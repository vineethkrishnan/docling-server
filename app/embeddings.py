"""Embedding generation for document chunks."""

import os
from functools import lru_cache

import structlog
from sentence_transformers import SentenceTransformer

from models import DocumentChunk

logger = structlog.get_logger()

# Default embedding model
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingGenerator:
    """Generates vector embeddings for text using sentence-transformers."""

    def __init__(self, model_name: str | None = None):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Name of the sentence-transformers model to use.
                       Defaults to all-MiniLM-L6-v2 for good balance of
                       quality and speed.
        """
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL)
        self._model: SentenceTransformer | None = None
        logger.info("Embedding generator initialized", model=self.model_name)

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self._model is None:
            logger.info("Loading embedding model", model=self.model_name)
            self._model = SentenceTransformer(self.model_name)
            logger.info(
                "Embedding model loaded",
                model=self.model_name,
                embedding_dim=self._model.get_sentence_embedding_dimension(),
            )
        return self._model

    @property
    def embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        return self.model.get_sentence_embedding_dimension()

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text.strip():
            return [0.0] * self.embedding_dimension
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Filter empty texts but track positions
        valid_indices = []
        valid_texts = []
        for i, text in enumerate(texts):
            if text.strip():
                valid_indices.append(i)
                valid_texts.append(text)
        
        # Generate embeddings for valid texts
        if valid_texts:
            embeddings = self.model.encode(
                valid_texts,
                convert_to_numpy=True,
                show_progress_bar=len(valid_texts) > 10,
            )
            embeddings_list = embeddings.tolist()
        else:
            embeddings_list = []
        
        # Reconstruct full list with zeros for empty texts
        result = []
        valid_idx = 0
        zero_embedding = [0.0] * self.embedding_dimension
        
        for i in range(len(texts)):
            if i in valid_indices:
                result.append(embeddings_list[valid_idx])
                valid_idx += 1
            else:
                result.append(zero_embedding)
        
        return result

    def embed_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """
        Add embeddings to document chunks.
        
        Args:
            chunks: List of document chunks without embeddings
            
        Returns:
            List of document chunks with embeddings added
        """
        if not chunks:
            return chunks
        
        logger.info("Generating embeddings for chunks", num_chunks=len(chunks))
        
        # Extract texts
        texts = [chunk.content for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.generate_embeddings(texts)
        
        # Create new chunks with embeddings
        embedded_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            embedded_chunks.append(DocumentChunk(
                id=chunk.id,
                content=chunk.content,
                metadata=chunk.metadata,
                embedding=embedding,
            ))
        
        logger.info(
            "Embeddings generated",
            num_chunks=len(embedded_chunks),
            embedding_dim=self.embedding_dimension,
        )
        
        return embedded_chunks


# Global embedding generator instance (lazy loaded)
_generator: EmbeddingGenerator | None = None


def get_embedding_generator() -> EmbeddingGenerator:
    """Get the global embedding generator instance."""
    global _generator
    if _generator is None:
        _generator = EmbeddingGenerator()
    return _generator


def generate_embedding(text: str) -> list[float]:
    """Generate embedding for a single text."""
    return get_embedding_generator().generate_embedding(text)


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts."""
    return get_embedding_generator().generate_embeddings(texts)


def embed_chunks(chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    """Add embeddings to document chunks."""
    return get_embedding_generator().embed_chunks(chunks)
