"""Data Chat module for conversational exploration of analysis results."""

from cli.data_chat.data_accessor import AnalysisDataAccessor
from cli.data_chat.chat_agent import DataChatAgent
from cli.data_chat.chat_ui import DataChatUI


def start_chat_session(final_state: dict, ticker: str, analysis_date: str, llm, console):
    """Start an interactive chat session with the analysis data.

    Args:
        final_state: The final state dict from the analysis run
        ticker: The ticker symbol that was analyzed
        analysis_date: The date of the analysis
        llm: The LLM instance to use for chat (quick_thinking_llm)
        console: Rich console instance for output
    """
    data_accessor = AnalysisDataAccessor(final_state, ticker, analysis_date)
    chat_agent = DataChatAgent(llm, data_accessor)
    chat_ui = DataChatUI(console, chat_agent, ticker, analysis_date)
    chat_ui.run_chat_loop()
