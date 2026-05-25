# Parser Module Design Patterns

## Overview

The parser module uses several well-established design patterns to achieve flexibility, extensibility, and maintainability.

---

## 1. Strategy Pattern

**Purpose:** Define a family of algorithms (parsers), encapsulate each one, and make them interchangeable.

**Implementation:**
```python
# Base interface (implicit in Python)
class BaseParser:
    def parse(self, file_path: str) -> Dict[str, Any]:
        pass

# Concrete strategies
class PDFParser(BaseParser):
    def parse(self, file_path: str) -> Dict[str, Any]:
        # PDF-specific parsing logic
        pass

class XMLParser(BaseParser):
    def parse(self, file_path: str) -> Dict[str, Any]:
        # XML-specific parsing logic
        pass
```

**Benefits:**
- Each parser is independent and focused on one format
- Easy to add new parsers without modifying existing code
- Parsers can be swapped at runtime

---

## 2. Factory Pattern

**Purpose:** Create objects without specifying the exact class to create.

**Implementation:**
```python
class ParserFactory:
    PARSER_MAP = {
        '.pdf': PDFParser,
        '.xml': XMLParser,
        '.properties': PropertiesParser,
    }
    
    @classmethod
    def get_parser(cls, file_path: str):
        extension = Path(file_path).suffix.lower()
        parser_class = cls.PARSER_MAP.get(extension)
        return parser_class()
```

**Benefits:**
- Centralized parser creation logic
- Automatic parser selection based on file type
- Easy to extend with new parsers

---

## 3. Template Method Pattern

**Purpose:** Define the skeleton of an algorithm, letting subclasses override specific steps.

**Implementation:**
```python
class BaseParser:
    def parse(self, file_path: str) -> Dict[str, Any]:
        # Template method
        self._validate_file(file_path)
        content = self._extract_content(file_path)
        metadata = self._extract_metadata(file_path)
        return self._format_output(content, metadata)
    
    def _extract_content(self, file_path: str) -> str:
        # Must be implemented by subclasses
        raise NotImplementedError
    
    def _extract_metadata(self, file_path: str) -> Dict:
        # Default implementation, can be overridden
        return {"file_name": Path(file_path).name}
```

**Benefits:**
- Common parsing workflow is standardized
- Subclasses only implement format-specific logic
- Reduces code duplication

---

## 4. Adapter Pattern

**Purpose:** Convert the interface of a class into another interface clients expect.

**Implementation:**
```python
class XMLParser:
    def parse(self, file_path: str) -> Dict[str, Any]:
        # Adapt ElementTree API to our standard format
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Convert XML structure to our standard dict format
        return {
            "content": self._xml_to_text(root),
            "metadata": self._extract_xml_metadata(root),
            "structure": self._xml_to_dict(root)
        }
```

**Benefits:**
- External libraries (ElementTree, PyMuPDF) are wrapped
- Consistent output format across all parsers
- Easy to swap underlying libraries

---

## 5. Singleton Pattern (for Factory)

**Purpose:** Ensure a class has only one instance and provide global access.

**Implementation:**
```python
class ParserFactory:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**Note:** Not strictly necessary for our stateless factory, but useful if we add caching or configuration.

---

## 6. Chain of Responsibility Pattern (for Encoding Detection)

**Purpose:** Pass requests along a chain of handlers until one handles it.

**Implementation:**
```python
class TextParser:
    ENCODINGS = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
    
    def _read_with_fallback(self, file_path: str) -> str:
        for encoding in self.ENCODINGS:
            try:
                return open(file_path, encoding=encoding).read()
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode file")
```

**Benefits:**
- Graceful handling of encoding issues
- Automatic fallback to alternative encodings
- No need to know encoding in advance

---

## 7. Decorator Pattern (for Error Handling)

**Purpose:** Add behavior to objects dynamically.

**Implementation:**
```python
def safe_parse(parse_func):
    def wrapper(self, file_path: str) -> Dict[str, Any]:
        try:
            return parse_func(self, file_path)
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return {
                "content": "",
                "metadata": {"error": str(e)},
                "parse_status": "failed"
            }
    return wrapper

class PDFParser:
    @safe_parse
    def parse(self, file_path: str) -> Dict[str, Any]:
        # Parsing logic
        pass
```

**Benefits:**
- Consistent error handling across parsers
- Separation of concerns
- Easy to add logging, tracing, etc.

---

## 8. Builder Pattern (for Complex Output)

**Purpose:** Construct complex objects step by step.

**Implementation:**
```python
class ParsedDocumentBuilder:
    def __init__(self):
        self._doc = {}
    
    def set_content(self, content: str):
        self._doc['content'] = content
        return self
    
    def set_metadata(self, metadata: Dict):
        self._doc['metadata'] = metadata
        return self
    
    def add_structure(self, structure: Dict):
        self._doc['structure'] = structure
        return self
    
    def build(self) -> Dict[str, Any]:
        return self._doc

# Usage
doc = (ParsedDocumentBuilder()
    .set_content(content)
    .set_metadata(metadata)
    .add_structure(structure)
    .build())
```

**Benefits:**
- Fluent interface for building complex outputs
- Step-by-step construction
- Immutable final object

---

## Design Pattern Summary

| Pattern | Purpose | Location |
|---------|---------|----------|
| **Strategy** | Interchangeable parsing algorithms | All parser classes |
| **Factory** | Automatic parser selection | `ParserFactory` |
| **Template Method** | Common parsing workflow | Base parser structure |
| **Adapter** | Wrap external libraries | All parsers |
| **Chain of Responsibility** | Encoding fallback | `TextParser` |
| **Decorator** | Error handling | Parse methods |
| **Builder** | Complex output construction | Document builders |

---

## SOLID Principles Applied

### Single Responsibility Principle (SRP)
- Each parser handles only one file format
- Factory only handles parser creation
- Chunker only handles text chunking

### Open/Closed Principle (OCP)
- Open for extension: Add new parsers by creating new classes
- Closed for modification: Existing parsers don't change

### Liskov Substitution Principle (LSP)
- All parsers can be used interchangeably
- Same input/output contract

### Interface Segregation Principle (ISP)
- Parsers only implement `parse()` method
- No forced implementation of unused methods

### Dependency Inversion Principle (DIP)
- Factory depends on parser interface, not concrete classes
- High-level code depends on abstractions

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    ParserFactory                         │
│                   (Factory Pattern)                      │
│                                                          │
│  get_parser(file_path) → Returns appropriate parser     │
└─────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  PDFParser   │    │  XMLParser   │    │ PropsParser  │
│  (Strategy)  │    │  (Strategy)  │    │  (Strategy)  │
└──────────────┘    └──────────────┘    └──────────────┘
        ↓                   ↓                   ↓
┌──────────────────────────────────────────────────────┐
│              Common Output Format                     │
│  {                                                    │
│    "content": str,                                    │
│    "metadata": dict,                                  │
│    "structure": dict (optional)                       │
│  }                                                    │
└──────────────────────────────────────────────────────┘
```

---

## Made with Bob