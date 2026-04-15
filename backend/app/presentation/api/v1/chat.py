from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import json
import logging

from app.presentation.schemas.chat import ChatRequest, ChatResponse
from app.application.services.agent_service import AgentService
from app.core.dependencies import get_agent_service
from app.security.guardrails import InputGuardrail

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat")
async def chat(
    request: ChatRequest,
    agent_service: AgentService = Depends(get_agent_service),
):
    for msg in request.messages:
        if msg.role == "user":
            is_safe, reason = InputGuardrail.validate_input(msg.content)
            if not is_safe:
                raise HTTPException(status_code=400, detail=reason)

    if request.stream:
        return StreamingResponse(
            _stream_generator(request, agent_service), media_type="text/event-stream"
        )
    else:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        result = await agent_service.process_message(
            messages, str(request.session_id) if request.session_id else None
        )
        return ChatResponse(
            response=result["final_response"],
            session_id=result.get("session_id"),
            context_used=result.get("retrieved_context", []),
            tools_used=[t.get("tool") for t in result.get("tool_results", []) if t],
        )


async def _stream_generator(request: ChatRequest, agent_service: AgentService):
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    session_id = str(request.session_id) if request.session_id else None
    try:
        async for event in agent_service.stream_process(messages, session_id):
            for node_name, node_output in event.items():
                if (
                    node_name == "response_generator"
                    and "final_response" in node_output
                ):
                    yield f"data: {json.dumps({'content': node_output['final_response'], 'done': False})}\n\n"
                elif node_name == "planner" and "plan" in node_output:
                    yield f"data: {json.dumps({'step': 'planning', 'plan': node_output['plan']})}\n\n"
                elif node_name == "retrieval" and "retrieved_context" in node_output:
                    yield f"data: {json.dumps({'step': 'retrieval', 'count': len(node_output['retrieved_context'])})}\n\n"
                elif node_name == "tool_executor" and "tool_results" in node_output:
                    yield f"data: {json.dumps({'step': 'tools', 'results': node_output['tool_results']})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
