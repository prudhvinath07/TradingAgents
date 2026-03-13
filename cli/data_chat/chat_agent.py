"""Chat agent for conversational data exploration."""

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from cli.data_chat.data_accessor import AnalysisDataAccessor


class DataChatAgent:
    """LLM-powered conversational agent for analysis exploration."""

    def __init__(self, llm, data_accessor: AnalysisDataAccessor):
        """Initialize the chat agent.

        Args:
            llm: The LLM instance to use for chat
            data_accessor: The data accessor for analysis data
        """
        self.llm = llm
        self.data_accessor = data_accessor
        self.conversation_history: list = []
        self.system_prompt = self._create_system_prompt()

    def _create_system_prompt(self) -> str:
        """Create the system prompt with analysis data context."""
        ticker = self.data_accessor.ticker
        date = self.data_accessor.analysis_date
        data_context = self.data_accessor.get_all_data_for_context()

        return f"""You are a Financial Data Analyst assistant helping users explore their TradingAgents analysis results for {ticker} on {date}.

YOUR ROLE:
1. Answer questions about the analysis using ONLY the data provided below
2. Always cite your sources (e.g., "According to the Market Analyst Report...", "The Bull Researcher argued...")
3. Be precise with numbers, facts, and specific details from the reports
4. If asked about something not in the data, clearly state "This information is not available in the analysis"
5. Provide clear, concise answers that directly address the user's question

IMPORTANT RULES:
- Do NOT make up information or provide data not present in the analysis
- Do NOT provide investment advice beyond what's explicitly stated in the reports
- When discussing debates, present both sides fairly
- Use markdown formatting for clarity (headers, bullet points, etc.)

ANALYSIS DATA:
{data_context}

Answer the user's question based on this data. Be helpful and thorough."""

    def ask(self, question: str) -> str:
        """Process a user question and return an answer.

        Args:
            question: The user's question

        Returns:
            The AI's response
        """
        # Build messages list
        messages = [SystemMessage(content=self.system_prompt)]

        # Add conversation history
        for msg in self.conversation_history:
            messages.append(msg)

        # Add current question
        messages.append(HumanMessage(content=question))

        # Get response from LLM
        response = self.llm.invoke(messages)

        # Extract content from response
        if hasattr(response, "content"):
            answer = response.content
        else:
            answer = str(response)

        # Store in history
        self.conversation_history.append(HumanMessage(content=question))
        self.conversation_history.append(AIMessage(content=answer))

        return answer

    def get_summary(self) -> str:
        """Get a high-level summary of the entire analysis."""
        summary_prompt = """Please provide a concise summary of the entire analysis including:
1. Overall recommendation (buy/sell/hold and why)
2. Key bullish factors identified
3. Key bearish factors or risks identified
4. The final trading decision and rationale

Keep it to 3-4 paragraphs maximum."""

        return self.ask(summary_prompt)

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
