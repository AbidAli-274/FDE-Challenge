from pathlib import Path

from .excel import read_excel
from .pdf import read_pdf
from .text import read_text

_READERS = {".txt": read_text, ".pdf": read_pdf, ".xlsx": read_excel}


def read_rfq(path) -> str:
    reader = _READERS.get(Path(path).suffix.lower())
    if reader is None:
        raise ValueError(f"no reader for {path}")
    return reader(path)
