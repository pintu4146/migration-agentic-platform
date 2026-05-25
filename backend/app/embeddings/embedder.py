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
    
    async def _get_provider(self):
        """Get or create provider instance."""
        if self.provider is None:
            self.provider = await get_provider(self.provider_name)
        return self.provider
    
    def _get_embedding_model(self) -> str:
        """
        Get the embedding model name for the provider.
        
        Returns:
            Model name string
        """
        
        if self._embedding_model:
            return self._embedding_model
        
        if self.provider_name == 'gemini':
            # Gemini embedding model
            self._embedding_model = 'models/embedding-001'
        elif self.provider_name == 'openai':
            # OpenAI embedding model
            self._embedding_model = 'text-embedding-3-small'
        else:
            raise ValueError(f"Unknown provider: {self.provider_name}")
        
        return self._embedding_model
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        
        provider = await self._get_provider()
        model = self._get_embedding_model()
        
        try:
            if self.provider_name == 'gemini':
                # Use Gemini embedding
                import google.generativeai as genai
                
                result = genai.embed_content(
                    model=model,
                    content=text,
                    task_type="retrieval_document"
                )
                
                return result['embedding']
            
            elif self.provider_name == 'openai':
                # Use OpenAI embedding
                response = await provider.client.embeddings.create(
                    model=model,
                    input=text
                )
                
                return response.data[0].embedding
            
            else:
                raise ValueError(f"Embedding not supported for provider: {self.provider_name}")
        
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
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
        
        provider = await self._get_provider()
        model = self._get_embedding_model()
        
        try:
            if self.provider_name == 'gemini':
                # Use Gemini embedding with query task type
                import google.generativeai as genai
                
                result = genai.embed_content(
                    model=model,
                    content=query,
                    task_type="retrieval_query"
                )
                
                return result['embedding']
            
            elif self.provider_name == 'openai':
                # Use OpenAI embedding
                response = await provider.client.embeddings.create(
                    model=model,
                    input=query
                )
                
                return response.data[0].embedding
            
            else:
                raise ValueError(f"Embedding not supported for provider: {self.provider_name}")
        
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {str(e)}")
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