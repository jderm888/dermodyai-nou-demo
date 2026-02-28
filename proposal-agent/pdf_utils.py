"""PDF and text extraction utilities."""

import io
from typing import Optional


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    """Extract text from a PDF given raw bytes."""
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("pdfplumber is not installed. Run: pip install pdfplumber")

    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"[Page {i + 1}]\n{page_text}")

    full_text = "\n\n".join(text_parts)
    if not full_text.strip():
        raise ValueError("Could not extract any text from the PDF. It may be image-based.")
    return full_text


def truncate_rfp(text: str, max_chars: int = 200_000) -> tuple[str, bool]:
    """
    Truncate RFP text to avoid exceeding context limits.
    Returns (truncated_text, was_truncated).
    """
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "\n\n[... RFP TRUNCATED FOR CONTEXT LIMITS ...]", True
