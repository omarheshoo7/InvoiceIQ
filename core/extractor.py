import io
import os

import fitz  # PyMuPDF
import pytesseract
from PIL import Image


def extract_text(file_bytes: bytes, filename: str) -> tuple[str, str]:
    """
    Main entry point. Returns (text, method).
    method is "pdf_native" for digital PDFs, "ocr" for scanned/images.
    """
    ext = os.path.splitext(filename.lower())[1]

    if ext == ".pdf":
        text = _extract_pdf_native(file_bytes)
        if len(text.strip()) > 50:
            return text, "pdf_native"
        # Not enough text — likely a scanned PDF, fall back to OCR
        return _ocr_pdf_pages(file_bytes), "ocr"

    if ext in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
        return _extract_image(file_bytes), "ocr"

    raise ValueError(f"Unsupported file type: '{ext}'. Use PDF, PNG, or JPG.")


def _extract_pdf_native(file_bytes: bytes) -> str:
    """Extract embedded text from a digital PDF using PyMuPDF."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages_text = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages_text)


def _ocr_pdf_pages(file_bytes: bytes) -> str:
    """Render each page of a scanned PDF as an image, then OCR it."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages_text = []
    for page in doc:
        # 2× zoom gives pytesseract much better accuracy
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        pages_text.append(pytesseract.image_to_string(img))
    doc.close()
    return "\n".join(pages_text)


def _extract_image(file_bytes: bytes) -> str:
    """OCR a plain image file."""
    img = Image.open(io.BytesIO(file_bytes))
    return pytesseract.image_to_string(img)
