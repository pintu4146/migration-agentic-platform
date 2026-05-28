"""
Document Chunker

Smart text chunking with sentence boundary detection and overlap.
"""

import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class DocumentChunker:
    """
    Chunks documents into overlapping segments with sentence boundary detection.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 200,
        min_chunk_size: int = 50
    ):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target size for each chunk in characters
            overlap: Number of characters to overlap between chunks
            min_chunk_size: Minimum chunk size to avoid tiny fragments (default: 50)
        """
        
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
        
        # Sentence boundary patterns
        self.sentence_endings = re.compile(r'[.!?]\s+')
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk text into overlapping segments.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        
        if not text or len(text.strip()) == 0:
            return []
        
        metadata = metadata or {}
        chunks = []
        
        # Split into sentences first
        sentences = self._split_sentences(text)
        
        if not sentences:
            # Fallback to character-based chunking
            return self._chunk_by_characters(text, metadata)
        
        # Build chunks from sentences
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence exceeds chunk size
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'chunk_index': chunk_index,
                    'char_start': sum(len(c) + 1 for c in chunks) if chunks else 0,
                    'char_end': sum(len(c) + 1 for c in chunks) + len(chunk_text) if chunks else len(chunk_text),
                    'metadata': metadata.copy()
                })
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = chunk_text[-self.overlap:] if len(chunk_text) > self.overlap else chunk_text
                overlap_sentences = self._split_sentences(overlap_text)
                current_chunk = overlap_sentences
                current_length = sum(len(s) for s in current_chunk)
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append({
                    'text': chunk_text,
                    'chunk_index': chunk_index,
                    'char_start': sum(len(c['text']) + 1 for c in chunks) if chunks else 0,
                    'char_end': sum(len(c['text']) + 1 for c in chunks) + len(chunk_text) if chunks else len(chunk_text),
                    'metadata': metadata.copy()
                })
        
        logger.info(f"Chunked text into {len(chunks)} chunks (avg size: {sum(len(c['text']) for c in chunks) / len(chunks):.0f} chars)")
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        
        # Split on sentence boundaries
        sentences = self.sentence_endings.split(text)
        
        # Clean up
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _chunk_by_characters(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fallback chunking by character count.
        
        Args:
            text: Text to chunk
            metadata: Metadata to attach
            
        Returns:
            List of chunks
        """
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at word boundary
            if end < len(text):
                # Look for space within last 100 chars
                space_pos = text.rfind(' ', end - 100, end)
                if space_pos > start:
                    end = space_pos
            
            chunk_text = text[start:end].strip()
            
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append({
                    'text': chunk_text,
                    'chunk_index': chunk_index,
                    'char_start': start,
                    'char_end': end,
                    'metadata': metadata.copy()
                })
                chunk_index += 1
            
            # Move start with overlap
            start = end - self.overlap if end - self.overlap > start else end
        
        return chunks
    
    def chunk_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk a parsed document.
        
        Args:
            document: Parsed document with 'content' and 'metadata'
            
        Returns:
            List of chunks
        """
        
        content = document.get('content', '')
        metadata = document.get('metadata', {})
        
        # Add document-level metadata
        doc_metadata = {
            'source_file': metadata.get('file_name', 'unknown'),
            'source_type': metadata.get('file_type', 'unknown'),
            'page_count': metadata.get('page_count'),
            'author': metadata.get('author'),
            'created_date': metadata.get('created_date'),
            'project_id': metadata.get('project_id'),  # CRITICAL: Preserve project_id for filtering
        }
        
        return self.chunk_text(content, doc_metadata)


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
    metadata: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to chunk text.
    
    Args:
        text: Text to chunk
        chunk_size: Target chunk size
        overlap: Overlap between chunks
        metadata: Optional metadata
        
    Returns:
        List of chunks
    """
    
    chunker = DocumentChunker(chunk_size=chunk_size, overlap=overlap)
    return chunker.chunk_text(text, metadata)


# Made with Bob