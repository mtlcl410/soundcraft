"""Record rate-mismatch and offset behavior while a real Model 12 song rolls."""
import json
import sys
import time
from pathlib import Path
from desktop_sync import cmd


def run(port, dest):
    with dest.open("x", encoding="utf-8", buffering=1) as log:
        start = time.perf_counter()

        def record(kind, data):
            print(json.dumps(dict(t=time.perf_counter()-start, kind=kind, data=data)), file=log)

        def setting(name, **params):
            result = cmd(port, name, **params)
            record(name, result)

        def observe():
            snapshot = cmd(port, "setup.midi_sync_status")
            record("diagnostics", snapshot)
            record("transport", cmd(port, "transport.status"))
            return snapshot["mtc_chase"]

        def sample(seconds):
            deadline = time.perf_counter()+seconds
            while time.perf_counter() < deadline:
                observe()
                time.sleep(.2)

        try:
            setting("setup.session", frame_rate="30", start_timecode="01:00:00:00",
                    external_offset_frames=0, freewheel="frames", freewheel_frames=8)
            setting("setup.mtc", input="UM-ONE", online=True)
            initial = observe().get("incoming_timecode")
            distinct = set()
            while len(distinct) < 5:
                if time.perf_counter()-start > 900:
                    raise TimeoutError("No advancing source for 15 minutes")
                label = observe().get("incoming_timecode")
                if label and label != initial:
                    distinct.add(label)
                time.sleep(.15)
            sample(4)
            setting("setup.session", external_offset_timecode="+01:00:00:00")
            sample(7)
            setting("setup.session", external_offset_frames=0)
            sample(2)
            setting("setup.session", start_timecode="00:00:00:00", frame_rate="29.97")
            sample(180)
            setting("setup.session", frame_rate="25")
            sample(30)
            setting("setup.session", frame_rate="30")
            sample(300)
        finally:
            setting("setup.mtc", online=False)
            record("final", cmd(port, "transport.status"))


if __name__ == "__main__":
    run(int(sys.argv[1]), Path(sys.argv[2]))
