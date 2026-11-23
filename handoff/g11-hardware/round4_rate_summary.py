"""Summarize real recorder observations between completed session-setting changes."""
import json
import statistics
import sys
from pathlib import Path


def summarize(source):
    stages = []
    stage = None
    with source.open(encoding="utf8") as stream:
        for line in stream:
            if not line.endswith("\n"):
                continue
            row = json.loads(line)
            if row["kind"] == "setup.session":
                stage = {"session": row["data"], "start": row["t"], "observations": [], "transport": []}
                stages.append(stage)
            elif stage and row["kind"] == "diagnostics":
                stage["observations"].append((row["t"], row["data"]["mtc_chase"]))
            elif stage and row["kind"] == "transport":
                stage["transport"].append(row["data"])
    out = []
    for stage in stages:
        observations = stage["observations"]
        if not observations:
            continue
        warnings = [(t, s["rate_mismatch"]) for t, s in observations if s["rate_mismatch"]]
        ppm = [w["speed_deviation_ppm"] for _, w in warnings if w.get("speed_deviation_ppm") is not None]
        first, last = observations[0][1], observations[-1][1]
        playing = [t["position"] for t in stage["transport"] if t["playing"]]
        out.append(dict(rate=stage["session"]["frame_rate"], start=stage["session"]["start_timecode"],
                        offset=stage["session"]["external_offset_timecode"], samples=len(observations),
                        observed_s=round(observations[-1][0]-observations[0][0], 2),
                        incoming_first=first["incoming_timecode"], incoming_last=last["incoming_timecode"],
                        states=sorted(set(s["state"] for _, s in observations)),
                        playing_samples=([playing[0],playing[-1]] if playing else []),
                        warning_count=len(warnings), first_warning_s=round(warnings[0][0]-stage["start"], 3) if warnings else None,
                        median_warning_ppm=statistics.median(ppm) if ppm else None,
                        hard_relocates_delta=last["hard_relocates"]-first["hard_relocates"],
                        losses_delta=last["losses"]-first["losses"]))
    return out


if __name__ == "__main__":
    print(json.dumps(summarize(Path(sys.argv[1])), indent=2))
