from pathlib import Path


def read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return "PDF extraction unavailable. Install pypdf from requirements.txt."

    reader = PdfReader(str(path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(f"[page {index}] {text}")
    return "\n".join(pages)

