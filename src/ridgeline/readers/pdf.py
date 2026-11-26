from pypdf import PdfReader


def read_pdf(path) -> str:
    """Layout mode keeps each table row on one line."""
    pages = [page.extract_text(extraction_mode="layout") for page in PdfReader(path).pages]
    return "\n\n".join(pages)
