"""
Parser Factory

Automatically selects and creates the appropriate parser based on file type.
Uses Factory Pattern for parser creation.
"""

import logging
from pathlib import Path
from typing import Dict, Any

from .pdf_parser import PDFParser
from .docx_parser import DOCXParser
from .excel_parser import ExcelParser
from .text_parser import TextParser
from .xml_parser import XMLParser
from .properties_parser import PropertiesParser
from .markdown_parser import MarkdownParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """
    Factory for creating document parsers based on file extension.
    Implements Factory Pattern for automatic parser selection.
    """
    
    # Mapping of file extensions to parser classes
    PARSER_MAP = {
        # Documents
        '.pdf': PDFParser,
        '.docx': DOCXParser,
        '.doc': DOCXParser,
        
        # Spreadsheets
        '.xlsx': ExcelParser,
        '.xls': ExcelParser,
        
        # Configuration
        '.xml': XMLParser,
        '.properties': PropertiesParser,
        
        # Markdown
        '.md': MarkdownParser,
        '.markdown': MarkdownParser,
        
        # Plain text
        '.txt': TextParser,
        '.rst': TextParser,
        '.log': TextParser,
        '.yaml': TextParser,
        '.yml': TextParser,
        '.json': TextParser,
        '.sh': TextParser,
        '.bat': TextParser,
        '.sql': TextParser,
    }
    
    @classmethod
    def get_parser(cls, file_path: str | Path):
        """
        Get appropriate parser for file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Parser instance
            
        Raises:
            ValueError: If file type is not supported
        """
        
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        parser_class = cls.PARSER_MAP.get(extension)
        
        if parser_class is None:
            raise ValueError(
                f"Unsupported file type: {extension}. "
                f"Supported types: {', '.join(cls.PARSER_MAP.keys())}"
            )
        
        try:
            return parser_class()
        except ImportError as e:
            logger.error(f"Parser for {extension} not available: {str(e)}")
            raise
    
    @classmethod
    def parse_file(cls, file_path: str | Path) -> Dict[str, Any]:
        """
        Parse file using appropriate parser.
        
        Args:
            file_path: Path to file
            
        Returns:
            Parsed content dictionary
        """
        
        parser = cls.get_parser(file_path)
        return parser.parse(file_path)
    
    @classmethod
    def is_supported(cls, file_path: str | Path) -> bool:
        """
        Check if file type is supported.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if supported, False otherwise
        """
        
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        return extension in cls.PARSER_MAP


def get_parser(file_path: str | Path):
    """
    Convenience function to get parser.
    
    Args:
        file_path: Path to file
        
    Returns:
        Parser instance
    """
    return ParserFactory.get_parser(file_path)


def parse_file(file_path: str | Path) -> Dict[str, Any]:
    """
    Convenience function to parse file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Parsed content dictionary
    """
    return ParserFactory.parse_file(file_path)


# Made with Bob