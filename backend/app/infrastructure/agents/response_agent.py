from typing import Dict, Any, List
import logging

from app.infrastructure.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class ResponseAgent:
    def __init__(self, llm_client: OpenAIClient):
        self.llm = llm_client

    async def generate(self, state: Dict[str, Any]) -> str:
        messages = state.get("messages", [])
        context = state.get("retrieved_context", [])
        tool_results = state.get("tool_results", [])

        system_prompt = self._build_system_prompt(context, tool_results)
        conversation = [{"role": "system", "content": system_prompt}] + messages

        try:
            response = await self.llm.chat_completion(conversation, temperature=0.3)
            return response
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            return "I'm having trouble formulating a response right now. Please try again."

    def _build_system_prompt(self, context: List[Dict], tool_results: List[Dict]) -> str:
        prompt = """You are a knowledgeable real estate assistant. Provide helpful, accurate responses based on the information given.

Guidelines:
- Be conversational but professional.
- If specific properties are mentioned, include key details.
- If mortgage calculation is provided, explain it clearly.
- If comparing properties, highlight differences.
- If information is insufficient, suggest what the user might clarify.

"""
        if context:
            prompt += "\n**Available Property Information:**\n"
            for item in context[:5]:
                prompt += f"- {item.get('title')}: ${item.get('price'):,.0f}, {item.get('rooms')} bed, {item.get('location')}. {item.get('content', '')[:150]}...\n"

        if tool_results:
            prompt += "\n**Tool Results:**\n"
            for tr in tool_results:
                if tr.get("tool") == "calculate_mortgage":
                    res = tr.get("result", {})
                    prompt += f"- Mortgage: Monthly payment ${res.get('monthly_payment')} for a ${res.get('price'):,.0f} home with {res.get('down_payment'):,.0f} down at {res.get('interest_rate')}% interest.\n"
                elif tr.get("tool") == "compare_properties":
                    comp = tr.get("result", {}).get("comparison", [])
                    if comp:
                        prompt += "- Comparison:\n"
                        for p in comp:
                            prompt += f"  * {p.get('title')}: ${p.get('price'):,.0f}, {p.get('rooms')} bed, {p.get('area')} sqft, {p.get('location')}\n"

        prompt += "\n**Instructions:** Answer the user's question using the above information. Be concise but thorough."
        return prompt