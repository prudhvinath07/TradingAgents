from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create a custom config
config = DEFAULT_CONFIG.copy()

# LLM Configuration - Using Ollama Cloud with DeepSeek
# Options for llm_provider: "ollama", "google", "openai", "anthropic", "openrouter"
config["llm_provider"] = "ollama"
config["deep_think_llm"] = "deepseek-v3.2"  # Powerful reasoning model
config["quick_think_llm"] = (
    "deepseek-v3.2"  # Ollama Cloud models: deepseek-v3.2, gpt-oss:120b, qwen3-next:80b
)
config["backend_url"] = (
    "https://ollama.com/v1"  # Use http://localhost:11434/v1 for local Ollama
)

# LLM behavior settings (reduce hallucinations and loops)
config["llm_temperature"] = 0.3  # Lower = more deterministic
config["llm_max_tokens"] = 4096  # Prevent runaway generation

# Embedding Configuration - Using local MiniLM (default)
# Options for embedding_provider: "local", "openai", "google"
config["embedding_provider"] = "local"
config["embedding_model"] = "all-MiniLM-L6-v2"  # Fast, free, runs locally

# Debate settings
config["max_debate_rounds"] = 1

# Configure data vendors (default uses yfinance and alpha_vantage)
config["data_vendors"] = {
    "core_stock_apis": "yfinance",  # Options: yfinance, alpha_vantage, local
    "technical_indicators": "yfinance",  # Options: yfinance, alpha_vantage, local
    "fundamental_data": "alpha_vantage",  # Options: openai, alpha_vantage, local
    "news_data": "alpha_vantage",  # Options: openai, alpha_vantage, google, local
}

# Initialize with custom config
ta = TradingAgentsGraph(debug=True, config=config)

# forward propagate
_, decision = ta.propagate("NVDA", "2024-05-10")
print(decision)

# Memorize mistakes and reflect
# ta.reflect_and_remember(1000) # parameter is the position returns
