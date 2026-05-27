"""
XML Parser

Parses XML files including configuration files, Spring configs, Maven POMs, etc.
Uses Strategy Pattern for parsing and Adapter Pattern for ElementTree API.
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class XMLParser:
    """
    XML Parser using Strategy Pattern.
    
    Parses XML files and extracts:
    - Text content (flattened)
    - Hierarchical structure
    - Attributes
    - Namespaces
    - Metadata
    """
    
    def __init__(self):
        self.parser_name = "xml_parser"
    
    def parse(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Parse XML file.
        
        Args:
            file_path: Path to XML file
            
        Returns:
            Dictionary with content, metadata, and structure
        """
        
        file_path = Path(file_path)
        
        try:
            logger.info(f"[{self.parser_name}] Parsing XML: {file_path.name}")
            
            # Parse XML
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract content
            text_content = self._extract_text_content(root)
            
            # Extract structure
            structure = self._xml_to_dict(root)
            
            # Extract metadata
            metadata = self._extract_metadata(file_path, root)
            
            # Detect XML type
            xml_type = self._detect_xml_type(root, file_path)
            
            logger.info(
                f"[{self.parser_name}] Successfully parsed {file_path.name} "
                f"(type: {xml_type}, elements: {len(list(root.iter()))})"
            )
            
            return {
                "content": text_content,
                "metadata": metadata,
                "structure": structure,
                "xml_type": xml_type,
                "root_tag": root.tag,
                "namespaces": self._extract_namespaces(root)
            }
        
        except ET.ParseError as e:
            logger.error(f"[{self.parser_name}] XML parse error: {str(e)}")
            raise ValueError(f"Invalid XML file: {str(e)}")
        
        except Exception as e:
            logger.error(f"[{self.parser_name}] Error parsing XML: {str(e)}", exc_info=True)
            raise
    
    def _extract_text_content(self, element: ET.Element, depth: int = 0) -> str:
        """
        Extract all text content from XML tree (flattened).
        
        Args:
            element: XML element
            depth: Current depth (for indentation)
            
        Returns:
            Flattened text content
        """
        
        lines = []
        
        # Add element tag as section header
        tag = self._clean_tag(element.tag)
        indent = "  " * depth
        lines.append(f"{indent}{tag}:")
        
        # Add element text
        if element.text and element.text.strip():
            lines.append(f"{indent}  {element.text.strip()}")
        
        # Add attributes
        if element.attrib:
            for key, value in element.attrib.items():
                lines.append(f"{indent}  @{key}: {value}")
        
        # Process children
        for child in element:
            child_text = self._extract_text_content(child, depth + 1)
            if child_text:
                lines.append(child_text)
        
        # Add tail text
        if element.tail and element.tail.strip():
            lines.append(f"{indent}{element.tail.strip()}")
        
        return "\n".join(lines)
    
    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """
        Convert XML element to dictionary (preserves structure).
        
        Args:
            element: XML element
            
        Returns:
            Dictionary representation
        """
        
        result = {
            "tag": self._clean_tag(element.tag),
            "attributes": dict(element.attrib) if element.attrib else {},
            "text": element.text.strip() if element.text else None,
            "children": []
        }
        
        # Process children
        for child in element:
            result["children"].append(self._xml_to_dict(child))
        
        return result
    
    def _extract_metadata(self, file_path: Path, root: ET.Element) -> Dict[str, Any]:
        """
        Extract metadata from XML file.
        
        Args:
            file_path: Path to file
            root: Root XML element
            
        Returns:
            Metadata dictionary
        """
        
        stat = file_path.stat()
        
        return {
            "parser": "XMLParser",
            "file_name": file_path.name,
            "file_type": "xml",
            "file_size": stat.st_size,
            "created_date": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "root_tag": self._clean_tag(root.tag),
            "element_count": len(list(root.iter())),
            "has_namespaces": bool(self._extract_namespaces(root)),
            "encoding": "UTF-8"  # ElementTree default
        }
    
    def _detect_xml_type(self, root: ET.Element, file_path: Path) -> str:
        """
        Detect type of XML file.
        
        Args:
            root: Root XML element
            file_path: Path to file
            
        Returns:
            XML type string
        """
        
        root_tag = self._clean_tag(root.tag).lower()
        file_name = file_path.name.lower()
        
        # Maven POM
        if root_tag == "project" and "pom" in file_name:
            return "maven_pom"
        
        # Spring configuration
        if "beans" in root_tag or "spring" in root_tag:
            return "spring_config"
        
        # Web.xml
        if root_tag == "web-app":
            return "web_xml"
        
        # Hibernate config
        if "hibernate" in root_tag:
            return "hibernate_config"
        
        # Log4j config
        if "log4j" in root_tag or "configuration" in root_tag:
            return "log4j_config"
        
        # Application server config
        if any(x in root_tag for x in ["server", "application", "domain"]):
            return "server_config"
        
        # Generic config
        if "config" in file_name or "configuration" in root_tag:
            return "configuration"
        
        # Default
        return "generic_xml"
    
    def _extract_namespaces(self, root: ET.Element) -> Dict[str, str]:
        """
        Extract XML namespaces.
        
        Args:
            root: Root XML element
            
        Returns:
            Namespace dictionary
        """
        
        namespaces = {}
        
        # Get namespaces from root
        for prefix, uri in root.attrib.items():
            if prefix.startswith("{http://www.w3.org/2000/xmlns/}"):
                ns_prefix = prefix.split("}")[-1]
                namespaces[ns_prefix] = uri
        
        # Check for default namespace
        if root.tag.startswith("{"):
            default_ns = root.tag.split("}")[0][1:]
            namespaces["default"] = default_ns
        
        return namespaces
    
    def _clean_tag(self, tag: str) -> str:
        """
        Remove namespace from tag.
        
        Args:
            tag: XML tag with possible namespace
            
        Returns:
            Clean tag name
        """
        
        if "}" in tag:
            return tag.split("}")[-1]
        return tag


# Made with Bob