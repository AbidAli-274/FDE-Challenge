from openpyxl import load_workbook


def read_excel(path) -> str:
    """One line per row, cells joined by ' | '; empty rows skipped."""
    out = []
    for ws in load_workbook(path, data_only=True).worksheets:
        out.append(f"[sheet: {ws.title}]")
        for row in ws.iter_rows(values_only=True):
            cells = ["" if c is None else str(c).strip() for c in row]
            if any(cells):
                out.append(" | ".join(cells))
    return "\n".join(out)
