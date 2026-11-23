"""Refresh the three existing draft descriptions after their branches have been fast-forwarded."""
from pathlib import Path
import json
import os
import re
import subprocess
import sys

here = Path(__file__).resolve().parent
gh = "E:/soundcraft/tools/gh/bin/gh.exe"
env = dict(os.environ, GH_CONFIG_DIR="E:/soundcraft/tools/gh-config")


def api(endpoint):
    return json.loads(subprocess.check_output([gh, "api", endpoint], env=env))


def update(number, head, section):
    endpoint = f"repos/storytold/soundcraft/pulls/{number}"
    pr = api(endpoint)
    assert pr["draft"] and pr["head"]["sha"] == head
    body = pr["body"]
    start = "<!-- storage-output-timing -->"
    end = "<!-- end-storage-output-timing -->"
    if start in body:
        left, middle = body.split(start, 1)
        _, right = middle.split(end, 1)
        body = left.rstrip() + "\n\n" + right.lstrip()
    if number == 1663:
        body = body.replace("Native Windows verification on the published head `ee80920`", "Earlier native Windows verification on `ee80920`")
        body = body.replace("**Published head `ee80920`.**", "**Earlier hardware build `ee80920`.**")
        body = re.sub(r"^\*\*Reproduction and recovery\.\*\*[^\n]+", "**Original reproduction (`ee80920`).** Entering and leaving USB STORAGE invalidated the Windows shared-audio stream. The status bar displayed the unavailable Model 12 output and the Playback Engine reconnect instruction. The original recovery used a manual reopen. The automatic-recovery results and the tested revision are above. Take 0016 retained its SD audio only.", body, flags=re.M)
    if number == 1669:
        body = body.replace("Windows with prerequisite #1536 applied locally: 1,654", "Earlier Windows checks at `69eadb8`, with prerequisite #1536 applied locally: 1,654")
        body = body.replace("The latest code is 69eadb8.", "That review follow-up was published at 69eadb8.")
    body = start + "\n" + section.strip() + "\n" + end + "\n\n" + body.lstrip()
    assert api(endpoint)["body"] == pr["body"]
    if body != pr["body"]:
        subprocess.run([gh, "api", "-X", "PATCH", endpoint, "--input", "-"],
                       input=json.dumps({"body":body}).encode(), stdout=subprocess.DEVNULL, env=env, check=True)
    saved = api(endpoint)
    assert saved["body"] == body and saved["head"]["sha"] == head and saved["draft"]
    (here / f"published-{number}.json").write_text(json.dumps(dict(head=head,url=saved["html_url"],section=section),indent=2))
    print(number,head,saved["html_url"])


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        number, head = arg.split("=")
        section = (here / f"note-{number}.md").read_text(encoding="utf-8-sig")
        update(int(number),head,section)
