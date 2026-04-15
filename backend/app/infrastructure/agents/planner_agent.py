import json
import logging
from typing import List, Dict, Any

from app.infrastructure.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class PlannerAgent:
    def __init__(self, llm_client: OpenAIClient):
        self.llm = llm_client

    async def plan(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        system_prompt = """You are a planning agent for a real estate assistant. Analyze the conversation and create a structured plan.

Output must be valid JSON:
{
    "search_query": "optimized search string for vector retrieval",
    "filters": {
        "city": "string or null",
        "min_price": number or null,
        "max_price": number or null,
        "min_rooms": number or null,
        "max_rooms": number or null,
        "property_type": "string or null"
    },
    "tools": ["list of tools: calculate_mortgage, compare_properties, get_properties"],
    "reasoning": "brief explanation"
}

Available tools:
- calculate_mortgage: when user asks about monthly payments, loan amount, or interest
- compare_properties: when user wants to compare two or more properties
- get_properties: when user wants to see property listings matching filters
"""

        user_content = messages[-1]["content"]
        response = await self.llm.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
        )

        try:
            json_str = response.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            return json.loads(json_str.strip())
        except json.JSONDecodeError:
            logger.warning(f"Planner JSON parse failed: {response[:200]}")
            return {
                "search_query": user_content,
                "filters": {},
                "tools": [],
                "reasoning": "Fallback due to parsing error"
            }