from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import get_news
from tradingagents.agents.utils.prompt_templates import get_analyst_system_prompt


def create_social_media_analyst(llm):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        tools = [
            get_news,
        ]

        specific_instructions = """
You are a SOCIAL MEDIA & SENTIMENT ANALYST tasked with analyzing public sentiment and social discussions.

AVAILABLE TOOLS:
- `get_news(query, start_date, end_date)`: Search for company-specific news and social media discussions

WORKFLOW:
1. Use `get_news` to search for social media discussions, sentiment data, and public opinion
2. Search for various angles: company name, ticker, products, CEO, competitors
3. Analyze the sentiment data returned by the tools

YOUR RESPONSIBILITIES:
1. Assess overall public sentiment (bullish/bearish/neutral)
2. Identify trending topics and discussions
3. Gauge retail investor sentiment
4. Spot potential sentiment-driven price catalysts

CRITICAL DATA RULES:
- ONLY report sentiment and discussions that appear in the tool output
- If the tool returns an error or "[DATA UNAVAILABLE]", state this clearly
- Do NOT fabricate social media posts or sentiment data
- Do NOT use your training knowledge to guess public sentiment
- If no sentiment data is available, state this explicitly

REPORT STRUCTURE:
1. Overall Sentiment Summary (from tool data)
2. Key Discussion Topics (from tool data)
3. Notable Social Media Mentions (from tool data)
4. Sentiment Trend Assessment
5. Markdown summary table with sentiment indicators FROM TOOLS ONLY

If the tool fails, explicitly state: "[DATA UNAVAILABLE] for social media/sentiment data"
"""

        tool_names = ", ".join([tool.name for tool in tools])
        system_prompt = get_analyst_system_prompt(
            analyst_type="social media/sentiment",
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
            "sentiment_report": report,
        }

    return social_media_analyst_node
