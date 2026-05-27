"""
Properties Parser

Parses Java properties files (.properties) and application.properties files.
Uses Strategy Pattern for parsing.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class PropertiesParser:
    """
    Properties Parser using Strategy Pattern.
    
    Parses Java properties files including:
    - application.properties
    - config.properties
    - Spring Boot configuration
    - Standard Java properties
    """
    
    def __init__(self):
        self.parser_name = "properties_parser"
        
        # Regex patterns
        self.comment_pattern = re.compile(r'^\s*[#!]')
        self.property_pattern = re.compile(r'^([^=:]+)[=:](.*)$')
        self.continuation_pattern = re.compile(r'\\$')
    
    def parse(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Parse properties file.
        
        Args:
            file_path: Path to properties file
            
        Returns:
            Dictionary with content, metadata, and properties
        """
        
        file_path = Path(file_path)
        
        try:
            logger.info(f"[{self.parser_name}] Parsing properties: {file_path.name}")
            
            # Read file with encoding fallback
            content = self._read_file(file_path)
            
            # Parse properties
            properties = self._parse_properties(content)
            
            # Extract metadata
            metadata = self._extract_metadata(file_path, properties)
            
            # Generate text content
            text_content = self._generate_text_content(properties)
            
            # Detect property type
            prop_type = self._detect_property_type(file_path, properties)
            
            # Group properties by prefix
            grouped = self._group_by_prefix(properties)
            
            logger.info(
                f"[{self.parser_name}] Successfully parsed {file_path.name} "
                f"(type: {prop_type}, properties: {len(properties)})"
            )
            
            return {
                "content": text_content,
                "metadata": metadata,
                "properties": properties,
                "grouped_properties": grouped,
                "property_type": prop_type,
                "property_count": len(properties)
            }
        
        except Exception as e:
            logger.error(f"[{self.parser_name}] Error parsing properties: {str(e)}", exc_info=True)
            raise
    
    def _read_file(self, file_path: Path) -> str:
        """
        Read file with encoding fallback.
        
        Args:
            file_path: Path to file
            
        Returns:
            File content
        """
        
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        raise ValueError(f"Could not decode file with any encoding: {encodings}")
    
    def _parse_properties(self, content: str) -> Dict[str, str]:
        """
        Parse properties from content.
        
        Args:
            content: File content
            
        Returns:
            Dictionary of properties
        """
        
        properties = {}
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and comments
            if not line or self.comment_pattern.match(line):
                i += 1
                continue
            
            # Handle line continuations
            full_line = line
            while self.continuation_pattern.search(full_line) and i + 1 < len(lines):
                i += 1
                full_line = full_line[:-1] + lines[i].strip()
            
            # Parse property
            match = self.property_pattern.match(full_line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                properties[key] = value
            
            i += 1
        
        return properties
    
    def _generate_text_content(self, properties: Dict[str, str]) -> str:
        """
        Generate readable text content from properties.
        
        Args:
            properties: Properties dictionary
            
        Returns:
            Formatted text content
        """
        
        lines = []
        
        # Group by prefix
        grouped = self._group_by_prefix(properties)
        
        for prefix, props in grouped.items():
            if prefix:
                lines.append(f"\n## {prefix.upper()} Configuration\n")
            else:
                lines.append("\n## General Properties\n")
            
            for key, value in props.items():
                lines.append(f"{key} = {value}")
        
        return "\n".join(lines)
    
    def _group_by_prefix(self, properties: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """
        Group properties by common prefix.
        
        Args:
            properties: Properties dictionary
            
        Returns:
            Grouped properties
        """
        
        grouped = {}
        
        for key, value in properties.items():
            # Extract prefix (first part before dot)
            if '.' in key:
                prefix = key.split('.')[0]
            else:
                prefix = ""
            
            if prefix not in grouped:
                grouped[prefix] = {}
            
            grouped[prefix][key] = value
        
        return grouped
    
    def _extract_metadata(self, file_path: Path, properties: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract metadata from properties file.
        
        Args:
            file_path: Path to file
            properties: Parsed properties
            
        Returns:
            Metadata dictionary
        """
        
        stat = file_path.stat()
        
        # Extract common Spring Boot properties
        spring_metadata = {}
        if 'spring.application.name' in properties:
            spring_metadata['application_name'] = properties['spring.application.name']
        if 'server.port' in properties:
            spring_metadata['server_port'] = properties['server.port']
        if 'spring.profiles.active' in properties:
            spring_metadata['active_profiles'] = properties['spring.profiles.active']
        
        return {
            "parser": "PropertiesParser",
            "file_name": file_path.name,
            "file_type": "properties",
            "file_size": stat.st_size,
            "created_date": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "property_count": len(properties),
            "spring_metadata": spring_metadata if spring_metadata else None,
            "encoding": "UTF-8"
        }
    
    def _detect_property_type(self, file_path: Path, properties: Dict[str, str]) -> str:
        """
        Detect type of properties file.
        
        Args:
            file_path: Path to file
            properties: Parsed properties
            
        Returns:
            Property type string
        """
        
        file_name = file_path.name.lower()
        
        # Check for Spring Boot
        spring_keys = ['spring.', 'server.', 'management.', 'logging.']
        if any(any(key.startswith(prefix) for prefix in spring_keys) for key in properties.keys()):
            if 'application' in file_name:
                return "spring_boot_application"
            return "spring_boot_config"
        
        # Check for database config
        db_keys = ['jdbc.', 'database.', 'datasource.', 'db.']
        if any(any(key.startswith(prefix) for prefix in db_keys) for key in properties.keys()):
            return "database_config"
        
        # Check for logging config
        if any(key.startswith('log') for key in properties.keys()):
            return "logging_config"
        
        # Check for application config
        if 'application' in file_name:
            return "application_config"
        
        # Default
        return "generic_properties"


# Made with Bob