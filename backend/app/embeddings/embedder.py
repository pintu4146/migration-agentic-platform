"""
Embedding Generator

Generates embeddings using Gemini or OpenAI models.
"""

import logging
from typing import List, Dict, Any, Optional
import asyncio

from app.config import settings
from app.providers.factory import get_provider

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generates embeddings for text chunks using configured LLM provider.
    """
    
    def __init__(self, provider_name: Optional[str] = None):
        """
        Initialize embedding generator.
        
        Args:
            provider_name: Provider to use ('gemini' or 'openai').
                          Defaults to settings.default_provider
        """
        
        self.provider_name = provider_name or settings.default_provider
        self.provider = None
        self._embedding_model = None
        self._genai_client = None
        self._actual_provider_name = None  # Track the actual provider being used
    
    async def _get_provider(self):
        """Get or create provider instance and detect actual provider."""
        if self.provider is None:
            # Get provider from factory (may return fallback if primary unavailable)
            from app.providers.factory import provider_factory
            
            # Check which provider is actually available
            if provider_factory.primary_provider and provider_factory.primary_status.value == "healthy":
                self.provider = provider_factory.primary_provider
                self._actual_provider_name = settings.primary_provider
                logger.info(f"Using primary provider for embeddings: {self._actual_provider_name}")
            elif provider_factory.fallback_provider and provider_factory.fallback_status.value == "healthy":
                self.provider = provider_factory.fallback_provider
                self._actual_provider_name = settings.fallback_provider
                logger.info(f"Using fallback provider for embeddings: {self._actual_provider_name}")
            else:
                raise RuntimeError("No healthy LLM provider available for embeddings")
        
        return self.provider
    
    def _get_actual_provider_name(self) -> str:
        """Get the actual provider name being used (after fallback logic)."""
        if self._actual_provider_name:
            return self._actual_provider_name
        return self.provider_name
    
    def _get_genai_client(self):
        """Get or create Google GenAI client for embeddings."""
        if self._genai_client is None and self.provider_name == 'gemini':
            try:
                from google import genai
            except ImportError:
                logger.error("google-genai package not installed. Install with: pip install google-genai")
                raise
            
            # Initialize client with API key from settings
            self._genai_client = genai.Client(api_key=settings.gemini_api_key)
        
        return self._genai_client
    
    def _get_embedding_model(self) -> str:
        """
        Get the embedding model name for the actual provider being used.
        
        Returns:
            Model name string
        """
        
        if self._embedding_model:
            return self._embedding_model
        
        # Use actual provider name (after fallback logic)
        actual_provider = self._get_actual_provider_name()
        
        if actual_provider == 'gemini':
            # Gemini embedding model from config
            self._embedding_model = settings.gemini_embedding_model
        elif actual_provider == 'openai':
            # OpenAI embedding model from config
            self._embedding_model = settings.openai_embedding_model
        else:
            raise ValueError(f"Unknown provider: {actual_provider}")
        
        return self._embedding_model
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        
        # Get provider first to determine actual provider being used
        await self._get_provider()
        actual_provider = self._get_actual_provider_name()
        model = self._get_embedding_model()
        
        try:
            if actual_provider == 'gemini':
                # Use new Google GenAI SDK for embeddings
                # DO NOT use provider.client - use separate genai client
                client = self._get_genai_client()
                
                logger.info(f"Generating Gemini embedding with model: {model}")
                result = client.models.embed_content(
                    model=model,
                    contents=text
                )
                
                # Extract embedding from response
                # result.embeddings is a list-like object
                logger.info(f"Gemini embedding result type: {type(result.embeddings)}")
                return list(result.embeddings)
            
            elif actual_provider == 'openai':
                # Use OpenAI embedding - need to get provider for OpenAI client
                provider = await self._get_provider()
                response = await provider.client.embeddings.create(
                    model=model,
                    input=text
                )
                
                return response.data[0].embedding
            
            else:
                raise ValueError(f"Embedding not supported for provider: {actual_provider}")
        
        except Exception as e:
            logger.error(f"Failed to generate embedding with {actual_provider}: {str(e)}", exc_info=True)
            raise
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 10
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            
        Returns:
            List of embedding vectors
        """
        
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Generate embeddings for batch
            batch_embeddings = await asyncio.gather(
                *[self.generate_embedding(text) for text in batch]
            )
            
            embeddings.extend(batch_embeddings)
            
            logger.info(f"Generated embeddings for batch {i // batch_size + 1} ({len(batch)} texts)")
        
        return embeddings
    
    async def embed_chunks(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for document chunks.
        
        Args:
            chunks: List of chunk dictionaries with 'text' field
            batch_size: Batch size for embedding generation
            
        Returns:
            Chunks with 'embedding' field added
        """
        
        if not chunks:
            return []
        
        # Extract texts
        texts = [chunk['text'] for chunk in chunks]
        
        # Generate embeddings
        embeddings = await self.generate_embeddings_batch(texts, batch_size)
        
        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding
            chunk['embedding_model'] = self._get_embedding_model()
            chunk['embedding_provider'] = self.provider_name
        
        logger.info(f"Embedded {len(chunks)} chunks using {self.provider_name}")
        
        return chunks
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Args:
            query: Query text
            
        Returns:
            Query embedding vector
        """
        
        # Get provider first to determine actual provider being used
        await self._get_provider()
        actual_provider = self._get_actual_provider_name()
        model = self._get_embedding_model()
        
        try:
            if actual_provider == 'gemini':
                # Use new Google GenAI SDK for query embeddings
                # DO NOT use provider.client - use separate genai client
                client = self._get_genai_client()
                
                logger.info(f"Generating Gemini query embedding with model: {model}")
                result = client.models.embed_content(
                    model=model,
                    contents=query
                )
                
                # Extract embedding from response
                logger.info(f"Gemini query embedding result type: {type(result.embeddings)}")
                return list(result.embeddings)
            
            elif actual_provider == 'openai':
                # Use OpenAI embedding - need to get provider for OpenAI client
                provider = await self._get_provider()
                response = await provider.client.embeddings.create(
                    model=model,
                    input=query
                )
                
                return response.data[0].embedding
            
            else:
                raise ValueError(f"Embedding not supported for provider: {actual_provider}")
        
        except Exception as e:
            logger.error(f"Failed to generate query embedding with {actual_provider}: {str(e)}", exc_info=True)
            raise


async def generate_embeddings(
    texts: List[str],
    provider_name: Optional[str] = None,
    batch_size: int = 10
) -> List[List[float]]:
    """
    Convenience function to generate embeddings.
    
    Args:
        texts: List of texts to embed
        provider_name: Provider to use
        batch_size: Batch size
        
    Returns:
        List of embedding vectors
    """
    
    generator = EmbeddingGenerator(provider_name)
    return await generator.generate_embeddings_batch(texts, batch_size)


# Made with Bob