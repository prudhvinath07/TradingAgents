"""Shared prompt templates for data grounding and validation.

These templates are designed to prevent LLM hallucinations by enforcing
strict data grounding rules across all agents.
"""

# Critical data grounding instructions - added to ALL analyst prompts
DATA_GROUNDING_INSTRUCTIONS = """
=== CRITICAL DATA GROUNDING RULES ===
1. You MUST ONLY use data returned by the tools. Do NOT use your training knowledge for ANY financial figures.
2. If a tool fails or returns no data, explicitly state "[DATA UNAVAILABLE]" for that section. Do NOT fabricate data.
3. Every number you cite (revenue, price, P/E ratio, market cap, etc.) MUST come directly from the tool output.
4. Do NOT extrapolate, estimate, or fill in missing data with assumptions or your training knowledge.
5. If tool data seems to conflict with what you "know", ALWAYS use the tool data - your training data may be outdated.
6. Cite your source for critical numbers, e.g., "Revenue: $26B (from get_income_statement tool)"
7. If you cannot find specific data in tool outputs, say "Data not available in tool output" - never guess.
"""


def get_date_context(trade_date: str) -> str:
    """Generate date context instructions to prevent temporal confusion.

    Args:
        trade_date: The simulation/analysis date in YYYY-MM-DD format

    Returns:
        Formatted date context instructions
    """
    return f"""
=== IMPORTANT DATE CONTEXT ===
- ANALYSIS DATE: {trade_date}
- You are simulating a trading scenario on this SPECIFIC date.
- All data from tools represents the state AS OF {trade_date}.
- Do NOT reference or incorporate events that occurred AFTER {trade_date}.
- Do NOT use your training knowledge about what happened after {trade_date}.
- Pretend today IS {trade_date} - you have no knowledge of the future.
"""


# Output constraints to prevent generation loops
OUTPUT_CONSTRAINTS = """
=== OUTPUT CONSTRAINTS ===
1. Provide your analysis ONCE. Do not repeat sections or conclusions.
2. Maximum report length: 2000 words.
3. Structure: Analysis -> Key Insights -> Markdown Summary Table -> STOP
4. After the markdown table, your response is COMPLETE. Do not add additional content.
5. Do not repeat the same recommendation multiple times.
"""


# Data validation reminder for researchers/debaters
DATA_VALIDATION_REMINDER = """
=== DATA VALIDATION REMINDER ===
- Base ALL arguments on data from the provided reports.
- If a report shows a specific price (e.g., $90), use THAT price - not a different one.
- If a report shows specific revenue (e.g., $26B), use THAT figure - not a different one.
- If a report says "[DATA UNAVAILABLE]", acknowledge this gap explicitly.
- Reference specific data points: "According to the market report, the closing price was $X..."
- Do NOT introduce numbers or statistics that are not present in the provided reports.
"""


# Price grounding for trader
PRICE_GROUNDING_INSTRUCTIONS = """
=== PRICE GROUNDING RULES ===
Your price targets, stop-losses, and entry points MUST be based on the current price from the market research report.

CRITICAL: Extract the actual current price from the market_report before making recommendations.
- If the market report shows current price is $X, base ALL calculations on $X
- Stop-loss: Calculate relative to $X (e.g., 10% below = $X * 0.9)
- Price targets: Calculate relative to $X (e.g., 20% gain = $X * 1.2)
- Do NOT use prices from your training knowledge - they are likely outdated.

Example of CORRECT approach:
"Based on the market report showing current price of $89.50, I recommend:
 - Entry: $89.50 (current price)
 - Stop-loss: $80.55 (10% below current)
 - Target: $107.40 (20% above current)"

Example of INCORRECT approach (DO NOT DO THIS):
"Based on my knowledge, NVDA trades around $450, so I recommend..."
This is WRONG because you must use the price from the tool data, not training knowledge.
"""


# Reminder about handling missing data
MISSING_DATA_INSTRUCTIONS = """
=== HANDLING MISSING DATA ===
If any tool returns an error or "[DATA UNAVAILABLE]":
1. Explicitly acknowledge the missing data in your report
2. State: "Note: [specific data type] was unavailable from data sources"
3. Do NOT attempt to fill in the gap with your training knowledge
4. Adjust your confidence level accordingly
5. Make recommendations based only on available data
"""


def get_analyst_system_prompt(
    analyst_type: str,
    current_date: str,
    ticker: str,
    tool_names: str,
    specific_instructions: str,
) -> str:
    """Generate a complete system prompt for an analyst with all grounding instructions.

    Args:
        analyst_type: Type of analyst (e.g., "fundamentals", "market", "news")
        current_date: The trade/analysis date
        ticker: Stock ticker symbol
        tool_names: Comma-separated list of available tools
        specific_instructions: Role-specific instructions for this analyst

    Returns:
        Complete system prompt with grounding instructions
    """
    date_context = get_date_context(current_date)

    return f"""You are a helpful AI assistant, collaborating with other assistants.
Use the provided tools to progress towards answering the question.
If you are unable to fully answer, that's OK; another assistant with different tools will help where you left off.
Execute what you can to make progress.

You have access to the following tools: {tool_names}

{DATA_GROUNDING_INSTRUCTIONS}
{date_context}
{OUTPUT_CONSTRAINTS}
{MISSING_DATA_INSTRUCTIONS}

=== YOUR ROLE: {analyst_type.upper()} ANALYST ===
Company: {ticker}
Analysis Date: {current_date}

{specific_instructions}

Remember: ONLY use data from tools. State "[DATA UNAVAILABLE]" if data is missing. Never fabricate numbers.
"""
