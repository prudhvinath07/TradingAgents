import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Callable


class FinancialSituationMemory:
    """Memory system for storing and retrieving financial situations and recommendations.

    Supports multiple embedding providers:
    - local: Uses sentence-transformers (all-MiniLM-L6-v2 by default)
    - openai: Uses OpenAI's embedding API
    - google: Uses Google's Generative AI embedding API
    - vertex: Uses Google Cloud Vertex AI embedding API
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        self.config = config
        self.embedding_provider = config.get("embedding_provider", "local")
        self.embedding_model_name = config.get("embedding_model", "all-MiniLM-L6-v2")

        # Initialize embedding model based on provider
        self._init_embedding_model()

        # ChromaDB setup
        self.chroma_client = chromadb.Client(Settings(allow_reset=True))
        self.situation_collection = self.chroma_client.create_collection(name=name)

    def _init_embedding_model(self) -> None:
        """Initialize the embedding model based on provider config."""
        if self.embedding_provider == "local":
            self._init_local_embeddings()
        elif self.embedding_provider == "openai":
            self._init_openai_embeddings()
        elif self.embedding_provider == "google":
            self._init_google_embeddings()
        elif self.embedding_provider == "vertex":
            self._init_vertex_embeddings()
        else:
            raise ValueError(
                f"Unsupported embedding provider: {self.embedding_provider}"
            )

    def _init_local_embeddings(self) -> None:
        """Initialize local sentence-transformers model."""
        from sentence_transformers import SentenceTransformer

        self._embedding_model = SentenceTransformer(self.embedding_model_name)
        self._get_embedding_func: Callable[[str], List[float]] = (
            self._get_embedding_local
        )

    def _init_openai_embeddings(self) -> None:
        """Initialize OpenAI embedding client."""
        from openai import OpenAI

        # Handle Ollama local backend
        backend_url = self.config.get("backend_url", "https://api.openai.com/v1")
        if backend_url == "http://localhost:11434/v1":
            self.embedding_model_name = "nomic-embed-text"
        elif self.embedding_model_name == "all-MiniLM-L6-v2":
            # Default to OpenAI model if local model name is still set
            self.embedding_model_name = "text-embedding-3-small"

        self._openai_client = OpenAI(base_url=backend_url)
        self._get_embedding_func = self._get_embedding_openai

    def _init_google_embeddings(self) -> None:
        """Initialize Google Generative AI embedding client."""
        from google import genai

        # Initialize client (uses GOOGLE_API_KEY env var by default)
        self._google_client = genai.Client()

        # Default to Google's embedding model if local model name is set
        if self.embedding_model_name == "all-MiniLM-L6-v2":
            self.embedding_model_name = "text-embedding-004"

        self._get_embedding_func = self._get_embedding_google

    def _init_vertex_embeddings(self) -> None:
        """Initialize Vertex AI embedding client."""
        from langchain_google_vertexai import VertexAIEmbeddings

        project = self.config.get("gcp_project_id")
        location = self.config.get("gcp_location", "us-central1")

        # Default to Vertex AI's embedding model if local model name is set
        if self.embedding_model_name == "all-MiniLM-L6-v2":
            self.embedding_model_name = "textembedding-gecko@003"

        self._vertex_embeddings = VertexAIEmbeddings(
            model_name=self.embedding_model_name,
            project=project,
            location=location,
        )
        self._get_embedding_func = self._get_embedding_vertex

    def _get_embedding_local(self, text: str) -> List[float]:
        """Get embedding using local SentenceTransformer model."""
        return self._embedding_model.encode(text).tolist()

    def _get_embedding_openai(self, text: str) -> List[float]:
        """Get embedding using OpenAI API."""
        response = self._openai_client.embeddings.create(
            model=self.embedding_model_name, input=text
        )
        return response.data[0].embedding

    def _get_embedding_google(self, text: str) -> List[float]:
        """Get embedding using Google Generative AI."""
        response = self._google_client.models.embed_content(
            model=self.embedding_model_name, contents=text
        )
        return list(response.embeddings[0].values)

    def _get_embedding_vertex(self, text: str) -> List[float]:
        """Get embedding using Vertex AI."""
        return self._vertex_embeddings.embed_query(text)

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using configured provider.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding vector
        """
        return self._get_embedding_func(text)

    def add_situations(self, situations_and_advice: List[tuple]) -> None:
        """Add financial situations and their corresponding advice.

        Args:
            situations_and_advice: List of tuples (situation, recommendation)
        """
        situations = []
        advice = []
        ids = []
        embeddings = []

        offset = self.situation_collection.count()

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situations.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))
            embeddings.append(self.get_embedding(situation))

        self.situation_collection.add(
            documents=situations,
            metadatas=[{"recommendation": rec} for rec in advice],
            embeddings=embeddings,
            ids=ids,
        )

    def get_memories(
        self, current_situation: str, n_matches: int = 1
    ) -> List[Dict[str, Any]]:
        """Find matching recommendations based on current situation.

        Args:
            current_situation: Description of the current financial situation
            n_matches: Number of similar situations to retrieve

        Returns:
            List of dictionaries with matched_situation, recommendation, and similarity_score
        """
        query_embedding = self.get_embedding(current_situation)

        results = self.situation_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_matches,
            include=["metadatas", "documents", "distances"],
        )

        matched_results = []
        for i in range(len(results["documents"][0])):
            matched_results.append(
                {
                    "matched_situation": results["documents"][0][i],
                    "recommendation": results["metadatas"][0][i]["recommendation"],
                    "similarity_score": 1 - results["distances"][0][i],
                }
            )

        return matched_results


if __name__ == "__main__":
    # Example usage with local embeddings (default)
    example_config = {
        "embedding_provider": "local",
        "embedding_model": "all-MiniLM-L6-v2",
    }

    matcher = FinancialSituationMemory("test_memory", example_config)

    # Example data
    example_data = [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities. Review fixed-income portfolio duration.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling pressure",
            "Reduce exposure to high-growth tech stocks. Look for value opportunities in established tech companies with strong cash flows.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions. Consider reducing allocation to emerging market debt.",
        ),
        (
            "Market showing signs of sector rotation with rising yields",
            "Rebalance portfolio to maintain target allocations. Consider increasing exposure to sectors benefiting from higher rates.",
        ),
    ]

    # Add the example situations and recommendations
    matcher.add_situations(example_data)

    # Example query
    current_situation = """
    Market showing increased volatility in tech sector, with institutional investors 
    reducing positions and rising interest rates affecting growth stock valuations
    """

    try:
        recommendations = matcher.get_memories(current_situation, n_matches=2)

        for i, rec in enumerate(recommendations, 1):
            print(f"\nMatch {i}:")
            print(f"Similarity Score: {rec['similarity_score']:.2f}")
            print(f"Matched Situation: {rec['matched_situation']}")
            print(f"Recommendation: {rec['recommendation']}")

    except Exception as e:
        print(f"Error during recommendation: {str(e)}")
