import logging
from pathlib import Path
from typing import List, Dict, Union
from pypdf import PdfReader

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class PDFParser:
    """Utility class for discovering and parsing PDF documents."""

    @staticmethod
    def discover_pdfs(directory: Union[str, Path]) -> List[Path]:
        """Discovers all PDF files within the given directory."""
        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            logger.warning(f"Directory {directory} does not exist or is not a directory.")
            return []
        
        # Discover all PDF files (case-insensitive glob)
        pdfs = list(dir_path.glob("*.pdf")) + list(dir_path.glob("*.PDF"))
        # Remove duplicates if any (though on Windows glob might be case-insensitive already)
        unique_pdfs = list(set(pdfs))
        unique_pdfs.sort(key=lambda p: p.name.lower())
        logger.info(f"Discovered {len(unique_pdfs)} PDF(s) in {directory}")
        return unique_pdfs

    @staticmethod
    def extract_text(file_path: Union[str, Path]) -> str:
        """
        Extracts raw text from a PDF file.
        Handles errors gracefully and returns an empty string for empty/corrupted files.
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {path}")
            return ""
        
        if not path.is_file():
            logger.error(f"Path is not a file: {path}")
            return ""

        try:
            reader = PdfReader(path)
            text_parts = []
            
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                else:
                    logger.debug(f"No text extracted from page {i} of {path.name}")
                    
            raw_text = "\n".join(text_parts).strip()
            
            if not raw_text:
                logger.warning(f"No text could be extracted from PDF: {path.name}")
                return ""
                
            return raw_text
        except Exception as e:
            logger.error(f"Error reading PDF file {path.name}: {str(e)}", exc_info=True)
            return ""
