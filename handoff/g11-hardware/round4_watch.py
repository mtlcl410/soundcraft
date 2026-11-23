"""Record live SoundCraft diagnostics without opening a second MIDI input."""
import argparse
import json
from pathlib import Path
import time

from desktop_sync import cmd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", type=int)
    parser.add_argument("file", type=Path)
    parser.add_argument("--duration", type=float, default=180)
    args = parser.parse_args()
    start = time.perf_counter()
    last_transport = 0
    with args.file.open("x", encoding="utf-8", buffering=1) as log:
        while time.perf_counter() - start < args.duration:
            before = time.perf_counter()
            row = {"elapsed_s": before - start}
            try:
                row["diagnostics"] = cmd(args.port, "setup.midi_sync_status")
                if before - last_transport >= 0.15:
                    row["transport"] = cmd(args.port, "transport.status")
                    last_transport = before
            except (ValueError, OSError) as error:
                row["error"] = str(error)
            row["reply_s"] = time.perf_counter() - start
            print(json.dumps(row, ensure_ascii=False, separators=(",", ":")), file=log)
            time.sleep(0.015)


if __name__ == "__main__":
    main()
