from typing import TypedDict, List, Dict, Any, Optional, Annotated, AsyncGenerator
import operator
import logging
from uuid import UUID

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from app.infrastructure.agents.planner_agent import PlannerAgent
from app.infrastructure.agents.retrieval_agent import RetrievalAgent
from app.infrastructure.agents.tool_agent import ToolAgent
from app.infrastructure.agents.response_agent import ResponseAgent
from app.domain.repositories import PropertyRepository, UserSessionRepository
from app.infrastructure.vector_store.pgvector_store import PGVectorStore
from app.infrastructure.llm.openai_client import OpenAIClient
from app.infrastructure.llm.embeddings import EmbeddingGenerator
from app.infrastructure.cache.redis_cache import RedisCache

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: List[Dict[str, str]]
    session_id: Optional[str]
    user_id: Optional[str]
    plan: Optional[Dict[str, Any]]
    retrieved_context: Annotated[List[Dict[str, Any]], operator.add]
    tool_results: Annotated[List[Dict[str, Any]], operator.add]
    final_response: Optional[str]
    error: Optional[str]


class MultiAgentGraph:
    def __init__(
        self,
        openai_client: OpenAIClient,
        property_repo: PropertyRepository,
        vector_store: PGVectorStore,
        embedding_generator: EmbeddingGenerator,
        session_repo: Optional[UserSessionRepository] = None,
        cache: Optional[RedisCache] = None,
    ):
        self.openai_client = openai_client
        self.property_repo = property_repo
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator
        self.session_repo = session_repo
        self.cache = cache

        self.planner = PlannerAgent(openai_client)
        self.retrieval = RetrievalAgent(
            vector_store, embedding_generator, property_repo
        )
        self.tool_agent = ToolAgent(property_repo, openai_client)
        self.response_agent = ResponseAgent(openai_client)

        self.checkpointer = MemorySaver()
        self.store = InMemoryStore()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("planner", self._planner_node)
        workflow.add_node("retrieval", self._retrieval_node)
        workflow.add_node("tool_executor", self._tool_node)
        workflow.add_node("response_generator", self._response_node)

        workflow.set_entry_point("planner")

        workflow.add_edge("planner", "retrieval")
        workflow.add_conditional_edges(
            "retrieval",
            self._should_use_tools,
            {
                "tools": "tool_executor",
                "respond": "response_generator",
            },
        )
        workflow.add_edge("tool_executor", "response_generator")
        workflow.add_edge("response_generator", END)

        return workflow.compile(checkpointer=self.checkpointer, store=self.store)

    async def _planner_node(self, state: AgentState) -> Dict[str, Any]:
        try:
            plan = await self.planner.plan(state["messages"])
            return {"plan": plan}
        except Exception as e:
            logger.error(f"Planner error: {e}")
            return {"error": str(e), "plan": {}}

    async def _retrieval_node(self, state: AgentState) -> Dict[str, Any]:
        try:
            plan = state.get("plan", {})
            query = plan.get("search_query", state["messages"][-1]["content"])
            filters = plan.get("filters", {})
            context = await self.retrieval.retrieve(query, filters)
            return {"retrieved_context": context}
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return {"error": str(e), "retrieved_context": []}

    async def _tool_node(self, state: AgentState) -> Dict[str, Any]:
        try:
            plan = state.get("plan", {})
            tools_to_call = plan.get("tools", [])
            if not tools_to_call:
                tools_to_call = await self.tool_agent.determine_tools(state)

            tool_results = []
            for tool_name in tools_to_call:
                result = await self.tool_agent.execute(tool_name, state)
                if result:
                    tool_results.append(result)
            return {"tool_results": tool_results}
        except Exception as e:
            logger.error(f"Tool error: {e}")
            return {"error": str(e), "tool_results": []}

    async def _response_node(self, state: AgentState) -> Dict[str, Any]:
        try:
            response = await self.response_agent.generate(state)
            if self.session_repo and state.get("session_id"):
                session_id = UUID(state["session_id"])
                messages = state["messages"] + [
                    {"role": "assistant", "content": response}
                ]
                await self.session_repo.update_messages(session_id, messages)
            return {"final_response": response}
        except Exception as e:
            logger.error(f"Response error: {e}")
            return {
                "error": str(e),
                "final_response": "I'm sorry, I encountered an error.",
            }

    def _should_use_tools(self, state: AgentState) -> str:
        plan = state.get("plan", {})
        if plan.get("tools"):
            return "tools"
        last_msg = state["messages"][-1]["content"].lower()
        if any(
            word in last_msg for word in ["mortgage", "calculate", "compare", "payment"]
        ):
            return "tools"
        return "respond"

    async def invoke(
        self, messages: List[Dict[str, str]], session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        import uuid

        initial_state: AgentState = {
            "messages": messages,
            "session_id": session_id or str(uuid.uuid4()),
            "user_id": None,
            "plan": None,
            "retrieved_context": [],
            "tool_results": [],
            "final_response": None,
            "error": None,
        }

        if self.session_repo and session_id:
            existing_session = await self.session_repo.get(UUID(session_id))
            if existing_session:
                existing_messages = existing_session.messages
                if (
                    existing_messages
                    and messages[-1]["content"] == existing_messages[-1]["content"]
                ):
                    initial_state["messages"] = existing_messages
                else:
                    initial_state["messages"] = existing_messages + messages

        config = {"configurable": {"thread_id": initial_state["session_id"]}}
        final_state = await self.graph.ainvoke(initial_state, config)
        return final_state

    async def stream(
        self, messages: List[Dict[str, str]], session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        import uuid

        initial_state: AgentState = {
            "messages": messages,
            "session_id": session_id or str(uuid.uuid4()),
            "user_id": None,
            "plan": None,
            "retrieved_context": [],
            "tool_results": [],
            "final_response": None,
            "error": None,
        }
        config = {"configurable": {"thread_id": initial_state["session_id"]}}
        async for event in self.graph.astream(initial_state, config):
            yield event
