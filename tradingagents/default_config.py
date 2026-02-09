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
    "llm_provider": "google",  # Options: openai, google, vertex, anthropic, ollama, openrouter
    "deep_think_llm": "gemini-3-pro-preview",  # Gemini 3 Pro (most advanced reasoning, 1M context)
    "quick_think_llm": "gemini-3-flash-preview",  # Gemini 3 Flash (fast and efficient)
    "backend_url": None,  # Not needed for Google/Vertex (uses ADC or GOOGLE_API_KEY env var)
    # Vertex AI settings (only needed if llm_provider is "vertex")
    "gcp_project_id": os.getenv(
        "GOOGLE_CLOUD_PROJECT"
    ),  # GCP Project ID (uses ADC default if None)
    "gcp_location": os.getenv(
        "GOOGLE_CLOUD_REGION", "global"
    ),  # GCP region for Vertex AI (use "global" for Gemini 3 preview models)
    # LLM behavior settings
    "llm_temperature": 0.3,  # Lower = more deterministic, reduces hallucinations
    "llm_max_tokens": 4096,  # Prevent runaway generation loops
    # Embedding settings
    "embedding_provider": "local",  # Options: local, openai, google, vertex
    "embedding_model": "all-MiniLM-L6-v2",  # Local: all-MiniLM-L6-v2, OpenAI: text-embedding-3-small, Google: text-embedding-004, Vertex: textembedding-gecko@003
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "yfinance",  # Options: yfinance, alpha_vantage, local
        "technical_indicators": "yfinance",  # Options: yfinance, alpha_vantage, local
        "fundamental_data": "yfinance",  # Options: yfinance, openai, alpha_vantage, local
        "news_data": "google",  # Options: google, openai, alpha_vantage, local
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Override specific tools if needed
        "get_global_news": "google",  # Options: google, reddit, openai, local
    },
}
