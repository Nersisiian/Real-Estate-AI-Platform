from unittest.mock import AsyncMock, MagicMock

from app.infrastructure.agents.planner_agent import PlannerAgent
from app.infrastructure.agents.tool_agent import ToolAgent


async def test_planner_agent():
    mock_llm = AsyncMock()
    mock_llm.chat_completion.return_value = (
        '{"search_query": "test", "filters": {}, "tools": [], "reasoning": "test"}'
    )
    planner = PlannerAgent(mock_llm)
    plan = await planner.plan([{"role": "user", "content": "Find a house"}])
    assert plan["search_query"] == "test"


async def test_tool_agent_calculate_mortgage():
    agent = ToolAgent(property_repo=MagicMock())
    state = {
        "messages": [{"role": "user", "content": "Mortgage on 400000 with 20% down"}]
    }
    result = await agent.calculate_mortgage(state)
    assert result["tool"] == "calculate_mortgage"
    assert "monthly_payment" in result["result"]
