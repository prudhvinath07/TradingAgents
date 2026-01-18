from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
)
from tradingagents.agents.utils.prompt_templates import get_analyst_system_prompt


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        ]

        specific_instructions = """
You are a FUNDAMENTALS ANALYST tasked with analyzing fundamental information about a company.

Your responsibilities:
1. Use the available tools to gather financial data:
   - `get_fundamentals`: Comprehensive company analysis
   - `get_balance_sheet`: Balance sheet data
   - `get_cashflow`: Cash flow statements
   - `get_income_statement`: Income statements

2. Write a comprehensive report including:
   - Company profile and basic financials
   - Financial health indicators (debt ratios, liquidity)
   - Revenue and earnings trends
   - Key financial metrics (P/E, P/B, margins)

3. CRITICAL DATA RULES:
   - ONLY report numbers that appear in the tool outputs
   - If a tool returns "[DATA UNAVAILABLE]", state this clearly
   - Cite the source tool for each key metric
   - Do NOT use your training knowledge for any financial figures

4. End with a Markdown table summarizing key metrics FROM THE TOOL DATA ONLY.

Provide detailed, actionable insights for traders based on the fundamental data.
"""

        tool_names = ", ".join([tool.name for tool in tools])
        system_prompt = get_analyst_system_prompt(
            analyst_type="fundamentals",
            current_date=current_date,
            ticker=ticker,
            tool_names=tool_names,
            specific_instructions=specific_instructions,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
