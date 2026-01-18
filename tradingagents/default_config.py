import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_dir": "/Users/yluo/Documents/Code/ScAI/FR1-data",
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": "google",  # Options: openai, google, anthropic, ollama, openrouter
    "deep_think_llm": "gemini-2.5-pro",  # Google Gemini Pro (state-of-the-art reasoning)
    "quick_think_llm": "gemini-2.5-flash",  # Google Gemini Flash (fast and efficient)
    "backend_url": None,  # Not needed for Google (uses GOOGLE_API_KEY env var)
    # LLM behavior settings
    "llm_temperature": 0.3,  # Lower = more deterministic, reduces hallucinations
    "llm_max_tokens": 4096,  # Prevent runaway generation loops
    # Embedding settings
    "embedding_provider": "local",  # Options: local, openai, google
    "embedding_model": "all-MiniLM-L6-v2",  # Local: all-MiniLM-L6-v2, OpenAI: text-embedding-3-small, Google: models/text-embedding-004
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "yfinance",  # Options: yfinance, alpha_vantage, local
        "technical_indicators": "yfinance",  # Options: yfinance, alpha_vantage, local
        "fundamental_data": "alpha_vantage",  # Options: openai, alpha_vantage, local
        "news_data": "alpha_vantage",  # Options: openai, alpha_vantage, google, local
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
        # Example: "get_news": "openai",               # Override category default
    },
}
