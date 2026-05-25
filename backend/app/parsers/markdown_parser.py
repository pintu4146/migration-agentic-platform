"""
Markdown Parser

Enhanced parser for Markdown files with structure extraction.
Uses Strategy Pattern for parsing.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class MarkdownParser:
    """
    Markdown Parser using Strategy Pattern.
    
    Parses Markdown files and extracts:
    - Text content
    - Heading structure
    - Code blocks
    - Links
    - Lists
    - Tables
    """
    
    def __init__(self):
        self.parser_name = "markdown_parser"
        
        # Regex patterns
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        self.code_block_pattern = re.compile(r'```(\w+)?\n(.*?)```', re.DOTALL)
        self.inline_code_pattern = re.compile(r'`([^`]+)`')
        self.link_pattern = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')
        self.image_pattern = re.compile(r'!\[([^\]]*)\]\(([^\)]+)\)')
        self.list_pattern = re.compile(r'^[\*\-\+]\s+(.+)$', re.MULTILINE)
        self.numbered_list_pattern = re.compile(r'^\d+\.\s+(.+)$', re.MULTILINE)
        self.table_pattern = re.compile(r'^\|(.+)\|$', re.MULTILINE)
    
    def parse(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Parse Markdown file.
        
        Args:
            file_path: Path to Markdown file
            
        Returns:
            Dictionary with content, metadata, and structure
        """
        
        file_path = Path(file_path)
        
        try:
            logger.info(f"[{self.parser_name}] Parsing Markdown: {file_path.name}")
            
            # Read file with encoding fallback
            content = self._read_file(file_path)
            
            # Extract structure
            headings = self._extract_headings(content)
            code_blocks = self._extract_code_blocks(content)
            links = self._extract_links(content)
            images = self._extract_images(content)
            
            # Extract metadata
            metadata = self._extract_metadata(file_path, content, headings)
            
            # Generate plain text (without markdown syntax)
            plain_text = self._to_plain_text(content)
            
            # Detect document type
            doc_type = self._detect_document_type(file_path, content, headings)
            
            logger.info(
                f"[{self.parser_name}] Successfully parsed {file_path.name} "
                f"(type: {doc_type}, headings: {len(headings)}, code blocks: {len(code_blocks)})"
            )
            
            return {
                "content": plain_text,
                "raw_markdown": content,
                "metadata": metadata,
                "structure": {
                    "headings": headings,
                    "code_blocks": code_blocks,
                    "links": links,
                    "images": images
                },
                "document_type": doc_type
            }
        
        except Exception as e:
            logger.error(f"[{self.parser_name}] Error parsing Markdown: {str(e)}", exc_info=True)
            raise
    
    def _read_file(self, file_path: Path) -> str:
        """
        Read file with encoding fallback.
        
        Args:
            file_path: Path to file
            
        Returns:
            File content
        """
        
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        raise ValueError(f"Could not decode file with any encoding: {encodings}")
    
    def _extract_headings(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract headings from Markdown.
        
        Args:
            content: Markdown content
            
        Returns:
            List of heading dictionaries
        """
        
        headings = []
        
        for match in self.heading_pattern.finditer(content):
            level = len(match.group(1))
            text = match.group(2).strip()
            
            headings.append({
                "level": level,
                "text": text,
                "position": match.start()
            })
        
        return headings
    
    def _extract_code_blocks(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract code blocks from Markdown.
        
        Args:
            content: Markdown content
            
        Returns:
            List of code block dictionaries
        """
        
        code_blocks = []
        
        for match in self.code_block_pattern.finditer(content):
            language = match.group(1) or "text"
            code = match.group(2).strip()
            
            code_blocks.append({
                "language": language,
                "code": code,
                "position": match.start()
            })
        
        return code_blocks
    
    def _extract_links(self, content: str) -> List[Dict[str, str]]:
        """
        Extract links from Markdown.
        
        Args:
            content: Markdown content
            
        Returns:
            List of link dictionaries
        """
        
        links = []
        
        for match in self.link_pattern.finditer(content):
            text = match.group(1)
            url = match.group(2)
            
            links.append({
                "text": text,
                "url": url
            })
        
        return links
    
    def _extract_images(self, content: str) -> List[Dict[str, str]]:
        """
        Extract images from Markdown.
        
        Args:
            content: Markdown content
            
        Returns:
            List of image dictionaries
        """
        
        images = []
        
        for match in self.image_pattern.finditer(content):
            alt_text = match.group(1)
            url = match.group(2)
            
            images.append({
                "alt_text": alt_text,
                "url": url
            })
        
        return images
    
    def _to_plain_text(self, content: str) -> str:
        """
        Convert Markdown to plain text.
        
        Args:
            content: Markdown content
            
        Returns:
            Plain text
        """
        
        # Remove code blocks
        text = self.code_block_pattern.sub('', content)
        
        # Remove inline code
        text = self.inline_code_pattern.sub(r'\1', text)
        
        # Remove images
        text = self.image_pattern.sub('', text)
        
        # Convert links to text
        text = self.link_pattern.sub(r'\1', text)
        
        # Remove heading markers
        text = self.heading_pattern.sub(r'\2', text)
        
        # Remove list markers
        text = self.list_pattern.sub(r'\1', text)
        text = self.numbered_list_pattern.sub(r'\1', text)
        
        # Remove bold/italic
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        
        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _extract_metadata(
        self,
        file_path: Path,
        content: str,
        headings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract metadata from Markdown file.
        
        Args:
            file_path: Path to file
            content: File content
            headings: Extracted headings
            
        Returns:
            Metadata dictionary
        """
        
        stat = file_path.stat()
        
        # Extract title (first H1 heading)
        title = None
        if headings and headings[0]['level'] == 1:
            title = headings[0]['text']
        
        # Count elements
        word_count = len(content.split())
        line_count = len(content.split('\n'))
        
        return {
            "file_name": file_path.name,
            "file_type": "markdown",
            "file_size": stat.st_size,
            "created_date": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "title": title,
            "word_count": word_count,
            "line_count": line_count,
            "heading_count": len(headings),
            "encoding": "UTF-8"
        }
    
    def _detect_document_type(
        self,
        file_path: Path,
        content: str,
        headings: List[Dict[str, Any]]
    ) -> str:
        """
        Detect type of Markdown document.
        
        Args:
            file_path: Path to file
            content: File content
            headings: Extracted headings
            
        Returns:
            Document type string
        """
        
        file_name = file_path.name.lower()
        content_lower = content.lower()
        
        # README
        if 'readme' in file_name:
            return "readme"
        
        # Documentation
        if any(x in file_name for x in ['doc', 'guide', 'manual']):
            return "documentation"
        
        # API documentation
        if 'api' in content_lower and any(x in content_lower for x in ['endpoint', 'request', 'response']):
            return "api_documentation"
        
        # Architecture document
        if any(x in content_lower for x in ['architecture', 'design', 'diagram']):
            return "architecture"
        
        # Changelog
        if 'changelog' in file_name or 'version' in content_lower:
            return "changelog"
        
        # Tutorial
        if any(x in content_lower for x in ['tutorial', 'getting started', 'quickstart']):
            return "tutorial"
        
        # Default
        return "general_markdown"


# Made with Bob