"""
Embeddings Module

Handles document chunking and embedding generation.
"""

from .chunker import DocumentChunker, chunk_text
from .embedder import EmbeddingGenerator, generate_embeddings

__all__ = [
    'DocumentChunker',
    'chunk_text',
    'EmbeddingGenerator',
    'generate_embeddings',
]

# Made with Bob