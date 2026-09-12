import logging
from pathlib import Path
from typing import List, Dict, Union
from pypdf import PdfReader

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

import io
from typing import List, Dict, Union, BinaryIO

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
    def extract_text(file_path_or_source: Union[str, Path, bytes, BinaryIO]) -> str:
        """
        Extracts raw text from a PDF file path, raw bytes, or file-like stream.
        Handles errors gracefully and returns an empty string for empty/corrupted files.
        """
        try:
            source_name = "stream"
            if isinstance(file_path_or_source, (str, Path)):
                path = Path(file_path_or_source)
                source_name = path.name
                if not path.exists():
                    logger.error(f"File not found: {path}")
                    return ""
                if not path.is_file():
                    logger.error(f"Path is not a file: {path}")
                    return ""
                reader = PdfReader(path)
            elif isinstance(file_path_or_source, (bytes, bytearray)):
                if not file_path_or_source:
                    return ""
                reader = PdfReader(io.BytesIO(file_path_or_source))
            elif hasattr(file_path_or_source, "read"):
                # Handle file-like objects (e.g. Streamlit UploadedFile)
                if hasattr(file_path_or_source, "seek"):
                    file_path_or_source.seek(0)
                if hasattr(file_path_or_source, "name"):
                    source_name = getattr(file_path_or_source, "name")
                reader = PdfReader(file_path_or_source)
            else:
                logger.error(f"Unsupported source type: {type(file_path_or_source)}")
                return ""

            text_parts = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                else:
                    logger.debug(f"No text extracted from page {i} of {source_name}")
                    
            raw_text = "\n".join(text_parts).strip()
            if not raw_text:
                logger.warning(f"No text could be extracted from PDF: {source_name}")
                return ""
                
            return raw_text
        except Exception as e:
            logger.error(f"Error reading PDF {source_name}: {str(e)}", exc_info=True)
            return ""
