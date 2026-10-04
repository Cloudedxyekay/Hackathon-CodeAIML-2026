from pathlib import Path


def read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return "PDF extraction unavailable. Install pypdf from requirements.txt."

    reader = PdfReader(str(path))
    pages = []
    empty_pages = False
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        empty_pages = empty_pages or not text.strip()
        pages.append(f"[page {index}] {text}")
    if empty_pages:
        from .read_image import read_image
        # OCR mixed/scanned documents as a whole so image-only pages are retained.
        return read_image(path)
    return "\n".join(pages)
