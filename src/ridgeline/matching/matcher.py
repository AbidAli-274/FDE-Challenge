"""Map extracted lines to Ridgeline part numbers: exact PN, cross reference, description.

The LLM never picks a part number here and no prices are read.
"""
import csv
import re
from difflib import SequenceMatcher
from pathlib import Path

from ..schema import ExtractedLine, ExtractedRFQ, OutputLine

THRESHOLD = 0.8
CONF_EXACT = 1.0
CONF_XREF = 0.95
CONF_NOTE = 0.7          # cross reference row carries a note
CONF_DISCONTINUED = 0.7  # replaced by a successor part
DESC_FLOOR = 0.5         # below this, no description match
DESC_MARGIN = 0.05       # runner-up closer than this = ambiguous
DESC_AMBIGUOUS_PENALTY = 0.15

ROOT = Path(__file__).resolve().parents[3]


def _rows(name):
    with open(ROOT / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


PRODUCTS = {r["part_number"]: r for r in _rows("products.csv")}
XREF = {}
for _r in _rows("cross_reference.csv"):
    XREF.setdefault(re.sub(r"[\s\-]", "", _r["competitor_part_number"]).upper(), []).append(_r)


def _tokens(text):
    return {t[:-1] if len(t) > 3 and t.endswith("s") else t for t in re.findall(r"[a-z0-9]+", text.lower())}


def _resolve(pn):
    """Return (part number, extra flags, cap) following replaced_by for discontinued parts."""
    prod = PRODUCTS[pn]
    if prod["status"] == "discontinued" and prod["replaced_by"] in PRODUCTS:
        return prod["replaced_by"], ["discontinued_replaced"], CONF_DISCONTINUED
    return pn, [], None


def _describe(query):
    q = _tokens(query)
    if not q:
        return None, None
    scored = []
    for pn, prod in PRODUCTS.items():
        d = prod["description"].lower()
        coverage = len(q & _tokens(d)) / len(q)
        scored.append((0.8 * coverage + 0.2 * SequenceMatcher(None, query.lower(), d).ratio(), pn))
    scored.sort(reverse=True)
    best, pn = scored[0]
    if len(q) < 2:
        best = min(best, 0.6)
    if len(scored) > 1 and best - scored[1][0] < DESC_MARGIN:
        best -= DESC_AMBIGUOUS_PENALTY
    return (pn, round(best, 2)) if best >= DESC_FLOOR else (None, None)


def _match_line(n, line: ExtractedLine) -> OutputLine:
    flags = list(line.flags)
    note = None
    pn = method = conf = None

    if line.ridgeline_part_number:
        raw = line.ridgeline_part_number.strip().upper()
        if raw in PRODUCTS:
            pn, extra, cap = _resolve(raw)
            method, conf, flags = "ridgeline_part_number", cap or CONF_EXACT, flags + extra
        else:
            flags.append("unknown_part_number")

    if pn is None and line.competitor_part_number:
        rows = XREF.get(re.sub(r"[\s\-]", "", line.competitor_part_number).upper())
        if rows and len({r["ridgeline_part_number"] for r in rows}) > 1:
            flags.append("ambiguous_cross_reference")
            note = "cross reference maps to: " + ", ".join(r["ridgeline_part_number"] for r in rows)
        elif rows:
            pn, extra, cap = _resolve(rows[0]["ridgeline_part_number"])
            method, conf, flags = "cross_reference", cap or CONF_XREF, flags + extra
            if rows[0]["notes"]:
                conf = min(conf, CONF_NOTE)
                flags.append("xref_note")
                note = rows[0]["notes"]

    if pn is None and "ambiguous_cross_reference" not in flags:
        found, score = _describe(line.description or line.as_written)
        if found:
            pn, extra, cap = _resolve(found)
            method, conf, flags = "description", min(score, cap or 1.0), flags + extra

    return OutputLine(
        line=n, as_written=line.as_written, quantity=line.quantity, unit=line.unit,
        ridgeline_part_number=pn, match_method=method, confidence=conf,
        needs_review=conf is None or conf < THRESHOLD or bool(flags),
        flags=list(dict.fromkeys(flags)), note=note,
    )


def match(extracted: ExtractedRFQ) -> list[OutputLine]:
    return [_match_line(i, line) for i, line in enumerate(extracted.lines, 1)]
