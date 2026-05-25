"""
Document Parsers Module

Provides parsers for various document formats using Strategy Pattern.
Each parser implements the same interface for consistent usage.
"""

from .pdf_parser import PDFParser
from .docx_parser import DOCXParser
from .excel_parser import ExcelParser
from .text_parser import TextParser
from .xml_parser import XMLParser
from .properties_parser import PropertiesParser
from .markdown_parser import MarkdownParser
from .parser_factory import ParserFactory, get_parser, parse_file

__all__ = [
    "PDFParser",
    "DOCXParser",
    "ExcelParser",
    "TextParser",
    "XMLParser",
    "PropertiesParser",
    "MarkdownParser",
    "ParserFactory",
    "get_parser",
    "parse_file",
]

# Made with Bob
