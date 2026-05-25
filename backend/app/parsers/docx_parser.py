"""
DOCX Parser

Extracts text content from Microsoft Word documents using python-docx.
"""

import logging
from pathlib import Path
from typing import Dict, Any

try:
    from docx import Document
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False
    logging.warning("python-docx not installed. DOCX parsing will not be available.")

logger = logging.getLogger(__name__)


class DOCXParser:
    """
    DOCX document parser using python-docx.
    
    Extracts text, tables, and metadata from Word documents.
    """
    
    def __init__(self):
        if not PYTHON_DOCX_AVAILABLE:
            raise ImportError("python-docx is required for DOCX parsing. Install with: pip install python-docx")
    
    def parse(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Parse DOCX file and extract content.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            Dictionary with extracted content and metadata
        """
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"DOCX file not found: {file_path}")
        
        logger.info(f"Parsing DOCX: {file_path.name}")
        
        try:
            doc = Document(file_path)
            
            # Extract core properties
            core_props = doc.core_properties
            metadata = {
                "title": core_props.title or file_path.stem,
                "author": core_props.author,
                "subject": core_props.subject,
                "keywords": core_props.keywords,
                "comments": core_props.comments,
                "created": core_props.created.isoformat() if core_props.created else None,
                "modified": core_props.modified.isoformat() if core_props.modified else None,
                "last_modified_by": core_props.last_modified_by,
                "revision": core_props.revision,
                "format": "DOCX"
            }
            
            # Extract paragraphs
            paragraphs = []
            full_text = []
            
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append({
                        "text": para.text,
                        "style": para.style.name if para.style else None
                    })
                    full_text.append(para.text)
            
            # Extract tables
            tables = []
            for table in doc.tables:
                table_data = []
                for row in table.rows:
                    row_data = [cell.text for cell in row.cells]
                    table_data.append(row_data)
                tables.append(table_data)
                
                # Add table content to full text
                for row in table_data:
                    full_text.append(" | ".join(row))
            
            content = "\n\n".join(full_text)
            
            logger.info(f"Extracted {len(content)} characters from {len(paragraphs)} paragraphs and {len(tables)} tables")
            
            return {
                "content": content,
                "metadata": metadata,
                "paragraphs": paragraphs,
                "tables": tables,
                "paragraph_count": len(paragraphs),
                "table_count": len(tables),
                "word_count": len(content.split()),
                "char_count": len(content)
            }
        
        except Exception as e:
            logger.error(f"Failed to parse DOCX {file_path}: {str(e)}")
            raise


# Made with Bob