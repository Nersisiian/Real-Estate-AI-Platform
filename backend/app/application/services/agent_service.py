from typing import List, Dict, Any, Optional, AsyncGenerator
import logging

from app.infrastructure.agents.graph import MultiAgentGraph

logger = logging.getLogger(__name__)


class AgentService:
    def __init__(self, agent_graph: MultiAgentGraph):
        self.agent_graph = agent_graph

    async def process_message(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            return await self.agent_graph.invoke(messages, session_id)
        except Exception as e:
            logger.error(f"Agent processing error: {e}")
            return {
                "final_response": "I'm sorry, I encountered an error processing your request.",
                "error": str(e),
                "session_id": session_id,
                "retrieved_context": [],
                "tool_results": [],
            }

    async def stream_process(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            async for event in self.agent_graph.stream(messages, session_id):
                yield event
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {"error": str(e)}
