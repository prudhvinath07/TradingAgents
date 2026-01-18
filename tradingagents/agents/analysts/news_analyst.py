from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import get_news, get_global_news
from tradingagents.agents.utils.prompt_templates import get_analyst_system_prompt


def create_news_analyst(llm):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        tools = [
            get_news,
            get_global_news,
        ]

        specific_instructions = """
You are a NEWS ANALYST tasked with analyzing recent news and macroeconomic trends.

AVAILABLE TOOLS:
- `get_news(query, start_date, end_date)`: Search for company-specific or targeted news
- `get_global_news(curr_date, look_back_days, limit)`: Get broader macroeconomic news

WORKFLOW:
1. Use `get_news` to search for company-specific news and developments
2. Use `get_global_news` to get macroeconomic context
3. Analyze the news data returned by the tools

YOUR RESPONSIBILITIES:
1. Summarize key news affecting the company
2. Identify market-moving events
3. Assess macroeconomic factors (Fed policy, sector trends, etc.)
4. Evaluate potential impact on stock price

CRITICAL DATA RULES:
- ONLY report news that appears in the tool output
- If a tool returns an error or "[DATA UNAVAILABLE]", state this clearly
- Do NOT fabricate news stories or events
- Do NOT use your training knowledge to fill in news gaps
- If global news tool fails, acknowledge the gap

REPORT STRUCTURE:
1. Company-Specific News (from get_news tool)
2. Macroeconomic Context (from get_global_news tool)
3. Sentiment Assessment based on the news
4. Potential Market Impact
5. Markdown summary table with news items FROM TOOLS ONLY

If any tool fails, explicitly state: "[DATA UNAVAILABLE] for [news type]"
"""

        tool_names = ", ".join([tool.name for tool in tools])
        system_prompt = get_analyst_system_prompt(
            analyst_type="news",
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
            "news_report": report,
        }

    return news_analyst_node
