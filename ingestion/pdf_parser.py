import io
import logging
from pathlib import Path
from typing import List, Union, BinaryIO

from pypdf import PdfReader

logger = logging.getLogger(__name__)


class PDFParser:
    """Utility for discovering and extracting text from PDF documents."""

    @staticmethod
    def discover_pdfs(directory: Union[str, Path]) -> List[Path]:
        """Return all PDF files in directory, sorted case-insensitively."""
        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            logger.warning(f"Directory {directory} does not exist or is not a directory.")
            return []

        # Deduplicate in case the OS glob is case-insensitive (Windows)
        pdfs = list({p.resolve() for p in dir_path.glob("*.pdf")} |
                    {p.resolve() for p in dir_path.glob("*.PDF")})
        pdfs.sort(key=lambda p: p.name.lower())
        logger.info(f"Discovered {len(pdfs)} PDF(s) in {directory}")
        return pdfs

    @staticmethod
    def extract_text(source: Union[str, Path, bytes, BinaryIO]) -> str:
        """
        Extract text from a PDF file path, raw bytes, or file-like stream.
        Returns an empty string for unreadable or empty PDFs rather than raising.
        """
        source_name = "stream"
        try:
            if isinstance(source, (str, Path)):
                path = Path(source)
                source_name = path.name
                if not path.exists() or not path.is_file():
                    logger.error(f"File not found or not a file: {path}")
                    return ""
                reader = PdfReader(path)
            elif isinstance(source, (bytes, bytearray)):
                if not source:
                    return ""
                reader = PdfReader(io.BytesIO(source))
            elif hasattr(source, "read"):
                if hasattr(source, "seek"):
                    source.seek(0)
                source_name = getattr(source, "name", "stream")
                reader = PdfReader(source)
            else:
                logger.error(f"Unsupported source type: {type(source)}")
                return ""

            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages.append(text)
                else:
                    logger.debug(f"No text on page {i} of {source_name}")

            raw = "\n".join(pages).strip()
            if not raw:
                logger.warning(f"No text extracted from: {source_name}")
            return raw

        except Exception as e:
            logger.error(f"Error reading PDF {source_name}: {e}", exc_info=True)
            return ""
