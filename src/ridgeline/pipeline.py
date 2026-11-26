"""Run every RFQ in rfqs/ and write one JSON per RFQ to outputs/. Nothing is sent anywhere."""
import csv
import re
from difflib import SequenceMatcher
from pathlib import Path

from .extractor import extract
from .matching import match
from .matching.matcher import ROOT
from .readers import read_rfq
from .schema import OutputLine, OutputRFQ

STUB_NOTE = "Handwritten image RFQ: no image reader is implemented, so it needs a human to read it."


def _norm(name):
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def customer_id(company):
    """Exact or near-exact name match against customers.csv, else null."""
    if not company:
        return None
    with open(ROOT / "customers.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            a, b = _norm(company), _norm(row["name"])
            if a == b or a in b or b in a or SequenceMatcher(None, a, b).ratio() >= 0.85:
                return row["customer_id"]
    return None


def stub(rfq_id, flag, note) -> OutputRFQ:
    line = OutputLine(line=1, as_written="entire RFQ", needs_review=True, flags=[flag], note=note)
    return OutputRFQ(rfq_id=rfq_id, customer_id=None, lines=[line])


def process(path: Path) -> OutputRFQ:
    rfq_id = path.stem
    try:
        text = read_rfq(path)
    except ValueError:
        return stub(rfq_id, "stub", STUB_NOTE)
    try:
        extracted = extract(text)
    except Exception as e:  # report the type only: the message could echo credentials
        return OutputRFQ(rfq_id=rfq_id, customer_id=None, lines=[
            OutputLine(line=1, as_written="entire RFQ", needs_review=True,
                       flags=["extraction_failed"], note=f"extraction failed: {type(e).__name__}")])
    return OutputRFQ(rfq_id=rfq_id, customer_id=customer_id(extracted.company), lines=match(extracted))


def main():
    out = ROOT / "outputs"
    out.mkdir(exist_ok=True)
    for path in sorted((ROOT / "rfqs").iterdir()):
        result = process(path)
        (out / f"{path.stem}.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print(f"{path.stem}: {len(result.lines)} lines, {sum(l.needs_review for l in result.lines)} need review")


if __name__ == "__main__":
    main()
