from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import get_news, get_social_media_sentiment
from tradingagents.agents.utils.prompt_templates import get_analyst_system_prompt


def create_social_media_analyst(llm):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        tools = [
            get_news,
            get_social_media_sentiment,
        ]

        specific_instructions = """
You are a SOCIAL MEDIA & SENTIMENT ANALYST tasked with analyzing public sentiment and social discussions.

AVAILABLE TOOLS:
- `get_news(ticker, start_date, end_date)`: Search for company-specific news
- `get_social_media_sentiment(ticker, curr_date, look_back_days)`: Get Reddit sentiment from trading subreddits (wallstreetbets, stocks, IndiaInvestments, etc.)

WORKFLOW:
1. FIRST use `get_social_media_sentiment` to get Reddit discussions and sentiment
2. THEN use `get_news` to supplement with news coverage
3. Analyze both sources to form a complete sentiment picture

YOUR RESPONSIBILITIES:
1. Assess overall public sentiment (bullish/bearish/neutral)
2. Identify trending topics and discussions
3. Gauge retail investor sentiment from Reddit
4. Spot potential sentiment-driven price catalysts

CRITICAL DATA RULES:
- ONLY report sentiment and discussions that appear in the tool output
- If the tool returns an error or "[DATA UNAVAILABLE]", state this clearly
- Do NOT fabricate social media posts or sentiment data
- Do NOT use your training knowledge to guess public sentiment
- If no sentiment data is available, state this explicitly

REPORT STRUCTURE:
1. Overall Sentiment Summary (from tool data)
2. Reddit Sentiment (from get_social_media_sentiment)
3. News Coverage (from get_news)
4. Key Discussion Topics
5. Sentiment Trend Assessment
6. Markdown summary table with sentiment indicators FROM TOOLS ONLY

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
