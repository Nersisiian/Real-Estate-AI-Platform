import re
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal

from app.domain.repositories import PropertyRepository
from app.infrastructure.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class ToolAgent:
    def __init__(self, property_repo: PropertyRepository, llm_client: Optional[OpenAIClient] = None):
        self.property_repo = property_repo
        self.llm = llm_client
        self.tools = {
            "get_properties": self.get_properties,
            "calculate_mortgage": self.calculate_mortgage,
            "compare_properties": self.compare_properties,
        }

    async def determine_tools(self, state: Dict[str, Any]) -> List[str]:
        if self.llm:
            prompt = f"""Given the user query: "{state['messages'][-1]['content']}"
Which tools are needed? Options: calculate_mortgage, compare_properties, get_properties.
Return only tool names separated by commas."""
            response = await self.llm.chat_completion([{"role": "user", "content": prompt}], temperature=0)
            tools = [t.strip() for t in response.split(',') if t.strip() in self.tools]
            return tools
        last_msg = state["messages"][-1]["content"].lower()
        tools = []
        if any(w in last_msg for w in ["mortgage", "payment", "loan"]):
            tools.append("calculate_mortgage")
        if "compare" in last_msg:
            tools.append("compare_properties")
        if any(w in last_msg for w in ["show", "list", "find", "search"]):
            tools.append("get_properties")
        return tools

    async def execute(self, tool_name: str, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if tool_name not in self.tools:
            return None
        try:
            return await self.tools[tool_name](state)
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"tool": tool_name, "error": str(e)}

    async def get_properties(self, state: Dict[str, Any]) -> Dict[str, Any]:
        plan = state.get("plan", {})
        filters = plan.get("filters", {})
        properties = await self.property_repo.find_by_criteria(
            city=filters.get("city"),
            min_price=Decimal(str(filters["min_price"])) if filters.get("min_price") else None,
            max_price=Decimal(str(filters["max_price"])) if filters.get("max_price") else None,
            min_rooms=filters.get("min_rooms"),
            max_rooms=filters.get("max_rooms"),
            property_type=filters.get("property_type"),
            limit=10,
        )
        return {
            "tool": "get_properties",
            "result": {
                "count": len(properties),
                "properties": [
                    {
                        "id": str(p.id),
                        "title": p.title,
                        "price": float(p.price),
                        "location": f"{p.city}, {p.state}",
                        "rooms": p.rooms,
                        "area": p.area,
                    } for p in properties
                ]
            }
        }

    async def calculate_mortgage(self, state: Dict[str, Any]) -> Dict[str, Any]:
        last_msg = state["messages"][-1]["content"]
        numbers = re.findall(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', last_msg)
        numbers = [float(n.replace(',', '').replace('$', '')) for n in numbers]
        price = numbers[0] if numbers else 300000
        down_payment = numbers[1] if len(numbers) > 1 else price * 0.2
        rate = numbers[2] if len(numbers) > 2 else 6.5

        loan_amount = price - down_payment
        monthly_rate = rate / 100 / 12
        n_payments = 30 * 12
        if monthly_rate == 0:
            monthly_payment = loan_amount / n_payments
        else:
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)

        return {
            "tool": "calculate_mortgage",
            "result": {
                "price": price,
                "down_payment": down_payment,
                "loan_amount": loan_amount,
                "interest_rate": rate,
                "monthly_payment": round(monthly_payment, 2),
                "term_years": 30
            }
        }

    async def compare_properties(self, state: Dict[str, Any]) -> Dict[str, Any]:
        context = state.get("retrieved_context", [])
        if not context:
            return {"tool": "compare_properties", "result": {"error": "No properties available"}}
        comparison = []
        for item in context[:3]:
            comparison.append({
                "title": item.get("title"),
                "price": item.get("price"),
                "location": item.get("location"),
                "rooms": item.get("rooms"),
                "area": item.get("area"),
            })
        return {"tool": "compare_properties", "result": {"comparison": comparison}}