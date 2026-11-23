"""Apply the original 19-note registration to another hardware acceptance recording."""
import sys

from acquisition_analysis import measure
from register_chase_notes import audit_note, json, ref, root, sensitivity


def peaks(notes, fixed):
    rows = []
    for n in notes:
        for r in n["fixed" if fixed else "dense"]:
            p = r["best"] if fixed else r
            rows.append(dict(sec=n["sec"], ms=r["ms"], fft=p["fft"], period=p["period"], lag=p["lag"], r=p["r"]))
    return {key: max(rows, key=lambda r: abs(r[key])) for key in ("fft", "period")}


if __name__ == "__main__":
    base = sys.argv[1]
    measure(base)
    reference_notes = json.loads((root / (ref + "-acquisition.json")).read_text())["notes"]
    notes = [audit_note(base, n) for n in reference_notes]
    assert len(notes) == 19 and sum(len(n["dense"]) for n in notes) == 3344
    g4 = [n for n in notes if n["sec"] == 12]
    summary = dict(fixed=peaks(notes, True), dense=peaks(notes, False), g4=peaks(g4, False))
    print(json.dumps(summary, indent=1))
    result = dict(reference=ref, recording=base, controls=sensitivity(), notes=notes, summary=summary)
    (root / (base + "-registered.json")).write_text(json.dumps(result, separators=(",", ":"), allow_nan=False))
