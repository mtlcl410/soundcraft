"""Summarize observed transport and MTC state edges, retaining RPC timing bounds."""
import argparse
import json
from pathlib import Path


def summarize(path):
    transitions = []
    previous = None
    last_transport = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.endswith("\n"):
                continue
            row = json.loads(line)
            if "diagnostics" not in row:
                continue
            state = row["diagnostics"]["mtc_chase"]
            last_transport = row.get("transport", last_transport)
            key = (state["state"], state["freewheel_state"], state["locks"], state["losses"], last_transport.get("playing"))
            if key != previous:
                transitions.append(dict(elapsed_s=round(row["elapsed_s"], 3), reply_s=round(row["reply_s"], 3),
                                        state=state, last_transport=last_transport))
                previous = key
    return transitions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.file), ensure_ascii=False, indent=2))
