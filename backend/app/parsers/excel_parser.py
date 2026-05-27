"""
Excel Parser

Extracts data from Excel files (XLSX, XLS) using pandas and openpyxl.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logging.warning("pandas not installed. Excel parsing will not be available.")

logger = logging.getLogger(__name__)


class ExcelParser:
    """
    Excel document parser using pandas.
    
    Extracts data from Excel spreadsheets and converts to text format.
    """
    
    def __init__(self):
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for Excel parsing. Install with: pip install pandas openpyxl")
    
    def parse(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Parse Excel file and extract content.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            Dictionary with extracted content and metadata
        """
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")
        
        logger.info(f"Parsing Excel: {file_path.name}")
        
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            sheets_data = []
            full_text = []
            
            for sheet_name in sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Convert DataFrame to text
                sheet_text = f"Sheet: {sheet_name}\n"
                sheet_text += df.to_string(index=False)
                
                sheets_data.append({
                    "sheet_name": sheet_name,
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": df.columns.tolist(),
                    "text": sheet_text,
                    "data": df.to_dict('records')  # For structured access
                })
                
                full_text.append(sheet_text)
            
            content = "\n\n".join(full_text)
            
            metadata = {
                "parser": "ExcelParser",
                "title": file_path.stem,
                "sheet_count": len(sheet_names),
                "sheet_names": sheet_names,
                "format": "Excel"
            }
            
            logger.info(f"Extracted {len(content)} characters from {len(sheet_names)} sheets")
            
            return {
                "content": content,
                "metadata": metadata,
                "sheets": sheets_data,
                "word_count": len(content.split()),
                "char_count": len(content)
            }
        
        except Exception as e:
            logger.error(f"Failed to parse Excel {file_path}: {str(e)}")
            raise
    
    def extract_as_csv(self, file_path: str | Path, sheet_name: str | None = None) -> str:
        """
        Extract Excel data as CSV format.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Specific sheet to extract (None for first sheet)
            
        Returns:
            CSV formatted string
        """
        
        file_path = Path(file_path)
        
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            df = pd.read_excel(file_path)
        
        return df.to_csv(index=False)


# Made with Bob