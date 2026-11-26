"""Compare outputs/ with answer_key/ for the three keyed RFQs. Only this script reads answer_key/.

    python evaluation/evaluate.py [--outputs DIR]
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RFQS = ["rfq_01_email", "rfq_02_clearwater", "rfq_03_tricounty"]
THRESHOLD = 0.8
CUTOFFS = [round(0.5 + 0.05 * i, 2) for i in range(11)]


def load_lines(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    lines = data.get("lines", []) if isinstance(data, dict) else data
    return {l.get("line"): l for l in lines if isinstance(l, dict)}


def same_qty_unit(out, key):
    if out is None:
        return False
    q_out, q_key = out.get("quantity"), key.get("quantity")
    same_q = q_out == q_key or (q_out is not None and q_key is not None and float(q_out) == float(q_key))
    norm = lambda u: u.strip().lower() if isinstance(u, str) else None
    return same_q and norm(out.get("unit")) == norm(key.get("unit"))


def ratio(num, den):
    return round(num / den, 4) if den else None


def evaluate(outputs_dir):
    rows = []  # (rfq, key line, output line or None)
    for name in RFQS:
        key = load_lines(ROOT / "answer_key" / f"{name}.json")
        out = load_lines(Path(outputs_dir) / f"{name}.json")
        rows += [(name, k, out.get(n)) for n, k in sorted(key.items())]

    def predicted(o, cutoff):
        return o is not None and o.get("ridgeline_part_number") and (o.get("confidence") or 0) >= cutoff

    def correct(o, k):
        return o is not None and o.get("ridgeline_part_number") == k.get("expected_part_number")

    def at(cutoff):
        accepted = [(k, o) for _, k, o in rows if predicted(o, cutoff)]
        good = sum(correct(o, k) for k, o in accepted)
        have_expected = sum(1 for _, k, _ in rows if k.get("expected_part_number"))
        return {"cutoff": cutoff, "accepted": len(accepted), "correct": good,
                "precision": ratio(good, len(accepted)), "recall": ratio(good, have_expected),
                "left_for_review": len(rows) - len(accepted)}

    headline = at(THRESHOLD)
    per_rfq = {}
    for name in RFQS:
        mine = [(k, o) for n, k, o in rows if n == name]
        per_rfq[name] = {"lines": len(mine),
                         "extraction_correct": sum(same_qty_unit(o, k) for k, o in mine),
                         "match_correct": sum(correct(o, k) and (k.get("expected_part_number") is not None)
                                              for k, o in mine)}
    return {
        "threshold": THRESHOLD,
        "extraction_accuracy": ratio(sum(same_qty_unit(o, k) for _, k, o in rows), len(rows)),
        "match_precision": headline["precision"],
        "match_recall": headline["recall"],
        "additional_metrics": {
            "confidence_table": [at(c) for c in CUTOFFS],
            "per_rfq": per_rfq,
            "review_rate": ratio(headline["left_for_review"], len(rows)),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outputs", default=str(ROOT / "outputs"))
    results = evaluate(ap.parse_args().outputs)
    (ROOT / "evaluation" / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"threshold            {results['threshold']}")
    print(f"extraction_accuracy  {results['extraction_accuracy']}")
    print(f"match_precision      {results['match_precision']}")
    print(f"match_recall         {results['match_recall']}")
    print("\ncutoff  accepted  correct  precision  recall  left_for_review")
    for r in results["additional_metrics"]["confidence_table"]:
        print(f"{r['cutoff']:<7} {r['accepted']:<9} {r['correct']:<8} {str(r['precision']):<10} "
              f"{str(r['recall']):<7} {r['left_for_review']}")


if __name__ == "__main__":
    main()
