"""
PDF Parser

Extracts text content from PDF files using PyMuPDF.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logging.warning("PyMuPDF not installed. PDF parsing will not be available.")

logger = logging.getLogger(__name__)


class PDFParser:
    """
    PDF document parser using PyMuPDF.
    
    Extracts text, metadata, and page information from PDF files.
    """
    
    def __init__(self):
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDF (fitz) is required for PDF parsing. Install with: pip install PyMuPDF")
    
    def parse(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Parse PDF file and extract content.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary with extracted content and metadata
        """
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        logger.info(f"Parsing PDF: {file_path.name}")
        
        try:
            doc = fitz.open(file_path)
            
            # Extract metadata
            metadata = {
                "title": doc.metadata.get("title", file_path.stem),
                "author": doc.metadata.get("author"),
                "subject": doc.metadata.get("subject"),
                "creator": doc.metadata.get("creator"),
                "producer": doc.metadata.get("producer"),
                "creation_date": doc.metadata.get("creationDate"),
                "modification_date": doc.metadata.get("modDate"),
                "page_count": doc.page_count,
                "format": "PDF"
            }
            
            # Extract text from all pages
            pages = []
            full_text = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                
                pages.append({
                    "page_number": page_num + 1,
                    "text": text,
                    "char_count": len(text)
                })
                
                full_text.append(text)
            
            doc.close()
            
            content = "\n\n".join(full_text)
            
            logger.info(f"Extracted {len(content)} characters from {doc.page_count} pages")
            
            return {
                "content": content,
                "metadata": metadata,
                "pages": pages,
                "word_count": len(content.split()),
                "char_count": len(content)
            }
        
        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {str(e)}")
            raise
    
    def extract_tables(self, file_path: str | Path) -> List[List[str]]:
        """
        Extract tables from PDF (basic implementation).
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of tables (each table is a list of rows)
        """
        
        # Note: This is a basic implementation
        # For better table extraction, consider using tabula-py or camelot
        
        file_path = Path(file_path)
        doc = fitz.open(file_path)
        
        tables = []
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            # Basic table detection using text blocks
            blocks = page.get_text("blocks")
            
            # Group blocks that might be table cells
            # This is a simplified approach
            table_blocks = [block for block in blocks if len(block[4].strip()) > 0]
            
            if table_blocks:
                tables.append(table_blocks)
        
        doc.close()
        
        return tables


# Made with Bob