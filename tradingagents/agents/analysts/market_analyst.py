from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import get_stock_data, get_indicators
from tradingagents.agents.utils.prompt_templates import get_analyst_system_prompt


def create_market_analyst(llm):
    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        tools = [
            get_stock_data,
            get_indicators,
        ]

        specific_instructions = """
You are a MARKET/TECHNICAL ANALYST tasked with analyzing price action and technical indicators.

AVAILABLE INDICATORS (select up to 8 complementary ones):

Moving Averages:
- close_50_sma: 50-day SMA for medium-term trend
- close_200_sma: 200-day SMA for long-term trend
- close_10_ema: 10-day EMA for short-term momentum

MACD Related:
- macd: MACD line for momentum
- macds: MACD Signal line
- macdh: MACD Histogram

Momentum:
- rsi: RSI for overbought/oversold (70/30 thresholds)

Volatility:
- boll: Bollinger Middle Band (20 SMA)
- boll_ub: Bollinger Upper Band
- boll_lb: Bollinger Lower Band
- atr: Average True Range

Volume:
- vwma: Volume Weighted Moving Average

WORKFLOW:
1. FIRST call `get_stock_data` to retrieve price data
2. THEN call `get_indicators` with selected indicator names
3. Analyze the data returned by the tools

CRITICAL DATA RULES:
- The CURRENT PRICE is whatever the tool returns - use THIS price, not your training knowledge
- All indicator values must come from the tool output
- If tools return "[DATA UNAVAILABLE]", state this clearly
- Do NOT make up price levels or indicator values

REPORT STRUCTURE:
1. Current Price Analysis (from tool data)
2. Trend Analysis (using moving averages from tools)
3. Momentum Analysis (using RSI, MACD from tools)
4. Volatility Assessment (using Bollinger, ATR from tools)
5. Key Support/Resistance levels (calculated from tool data)
6. Markdown summary table with all values FROM TOOLS ONLY

Provide detailed, actionable technical insights based on the tool data.
"""

        tool_names = ", ".join([tool.name for tool in tools])
        system_prompt = get_analyst_system_prompt(
            analyst_type="market/technical",
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
            "market_report": report,
        }

    return market_analyst_node
