"""
Text Parser

Extracts content from plain text and markdown files.
"""

import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TextParser:
    """
    Plain text and markdown parser.
    
    Handles TXT, MD, and other text-based formats.
    """
    
    def parse(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Parse text file and extract content.
        
        Args:
            file_path: Path to text file
            
        Returns:
            Dictionary with extracted content and metadata
        """
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Text file not found: {file_path}")
        
        logger.info(f"Parsing text file: {file_path.name}")
        
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
            content = None
            encoding_used = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    encoding_used = encoding
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise ValueError(f"Could not decode file with any supported encoding")
            
            # Extract basic metadata
            lines = content.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            
            metadata = {
                "parser": "TextParser",
                "title": file_path.stem,
                "filename": file_path.name,
                "extension": file_path.suffix,
                "encoding": encoding_used,
                "line_count": len(lines),
                "non_empty_line_count": len(non_empty_lines),
                "format": "Text"
            }
            
            # For markdown files, try to extract title from first heading
            if file_path.suffix.lower() in ['.md', '.markdown']:
                for line in lines[:10]:  # Check first 10 lines
                    if line.startswith('# '):
                        metadata["title"] = line[2:].strip()
                        metadata["format"] = "Markdown"
                        break
            
            logger.info(f"Extracted {len(content)} characters from {len(lines)} lines")
            
            return {
                "content": content,
                "metadata": metadata,
                "lines": lines,
                "word_count": len(content.split()),
                "char_count": len(content)
            }
        
        except Exception as e:
            logger.error(f"Failed to parse text file {file_path}: {str(e)}")
            raise


# Made with Bob