"""Data accessor for unified access to all analysis data."""

from typing import Optional


class AnalysisDataAccessor:
    """Provides unified access to all analysis data for conversational queries."""

    # Report type mappings
    REPORT_TYPES = {
        "market": "market_report",
        "sentiment": "sentiment_report",
        "social": "sentiment_report",
        "news": "news_report",
        "fundamentals": "fundamentals_report",
        "investment_plan": "investment_plan",
        "trader_plan": "trader_investment_plan",
        "final_decision": "final_trade_decision",
    }

    def __init__(self, final_state: dict, ticker: str, analysis_date: str):
        """Initialize the data accessor.

        Args:
            final_state: The final state dict from the analysis run
            ticker: The ticker symbol that was analyzed
            analysis_date: The date of the analysis
        """
        self.final_state = final_state
        self.ticker = ticker
        self.analysis_date = analysis_date

    def get_report(self, report_type: str) -> Optional[str]:
        """Get a specific report by type.

        Args:
            report_type: One of 'market', 'sentiment', 'social', 'news',
                        'fundamentals', 'investment_plan', 'trader_plan', 'final_decision'

        Returns:
            The report content or None if not available
        """
        key = self.REPORT_TYPES.get(report_type.lower(), report_type)
        return self.final_state.get(key)

    def get_debate_history(self, debate_type: str) -> Optional[dict]:
        """Get debate history.

        Args:
            debate_type: Either 'investment' or 'risk'

        Returns:
            The debate state dict or None if not available
        """
        if debate_type.lower() == "investment":
            return self.final_state.get("investment_debate_state")
        elif debate_type.lower() == "risk":
            return self.final_state.get("risk_debate_state")
        return None

    def get_available_reports(self) -> list[str]:
        """Get list of available report types."""
        available = []
        report_names = {
            "market_report": "Market Analysis",
            "sentiment_report": "Social Sentiment",
            "news_report": "News Analysis",
            "fundamentals_report": "Fundamentals",
            "investment_plan": "Investment Plan",
            "trader_investment_plan": "Trader Plan",
            "final_trade_decision": "Final Decision",
        }
        for key, name in report_names.items():
            if self.final_state.get(key):
                available.append(name)
        return available

    def get_context_summary(self) -> str:
        """Get a summary of available data for display."""
        reports = self.get_available_reports()
        has_investment_debate = bool(self.final_state.get("investment_debate_state"))
        has_risk_debate = bool(self.final_state.get("risk_debate_state"))

        summary = f"Ticker: {self.ticker}\n"
        summary += f"Date: {self.analysis_date}\n\n"
        summary += "Available Reports:\n"
        for report in reports:
            summary += f"  - {report}\n"

        if has_investment_debate:
            summary += "\nDebates:\n  - Bull vs Bear Research Debate\n"
        if has_risk_debate:
            summary += "  - Risk Management Discussion\n"

        return summary

    def get_all_data_for_context(self) -> str:
        """Combine all data into a single context string for LLM."""
        context_parts = []

        context_parts.append(f"=== ANALYSIS FOR {self.ticker} ON {self.analysis_date} ===\n")

        # Add analyst reports
        if self.final_state.get("market_report"):
            context_parts.append("## MARKET ANALYST REPORT (Technical Analysis)")
            context_parts.append(self.final_state["market_report"])
            context_parts.append("")

        if self.final_state.get("sentiment_report"):
            context_parts.append("## SOCIAL MEDIA ANALYST REPORT (Sentiment)")
            context_parts.append(self.final_state["sentiment_report"])
            context_parts.append("")

        if self.final_state.get("news_report"):
            context_parts.append("## NEWS ANALYST REPORT")
            context_parts.append(self.final_state["news_report"])
            context_parts.append("")

        if self.final_state.get("fundamentals_report"):
            context_parts.append("## FUNDAMENTALS ANALYST REPORT")
            context_parts.append(self.final_state["fundamentals_report"])
            context_parts.append("")

        # Add investment debate
        investment_debate = self.final_state.get("investment_debate_state")
        if investment_debate:
            context_parts.append("## INVESTMENT RESEARCH DEBATE")
            if investment_debate.get("bull_history"):
                context_parts.append("### Bull Researcher Arguments:")
                context_parts.append(investment_debate["bull_history"])
            if investment_debate.get("bear_history"):
                context_parts.append("### Bear Researcher Arguments:")
                context_parts.append(investment_debate["bear_history"])
            if investment_debate.get("judge_decision"):
                context_parts.append("### Research Manager Decision:")
                context_parts.append(investment_debate["judge_decision"])
            context_parts.append("")

        # Add investment plan
        if self.final_state.get("investment_plan"):
            context_parts.append("## INVESTMENT PLAN")
            context_parts.append(self.final_state["investment_plan"])
            context_parts.append("")

        # Add trader plan
        if self.final_state.get("trader_investment_plan"):
            context_parts.append("## TRADER INVESTMENT PLAN")
            context_parts.append(self.final_state["trader_investment_plan"])
            context_parts.append("")

        # Add risk debate
        risk_debate = self.final_state.get("risk_debate_state")
        if risk_debate:
            context_parts.append("## RISK MANAGEMENT DISCUSSION")
            if risk_debate.get("risky_history"):
                context_parts.append("### Aggressive Risk Analyst:")
                context_parts.append(risk_debate["risky_history"])
            if risk_debate.get("safe_history"):
                context_parts.append("### Conservative Risk Analyst:")
                context_parts.append(risk_debate["safe_history"])
            if risk_debate.get("neutral_history"):
                context_parts.append("### Neutral Risk Analyst:")
                context_parts.append(risk_debate["neutral_history"])
            if risk_debate.get("judge_decision"):
                context_parts.append("### Portfolio Manager Decision:")
                context_parts.append(risk_debate["judge_decision"])
            context_parts.append("")

        # Add final decision
        if self.final_state.get("final_trade_decision"):
            context_parts.append("## FINAL TRADE DECISION")
            context_parts.append(self.final_state["final_trade_decision"])
            context_parts.append("")

        return "\n".join(context_parts)
