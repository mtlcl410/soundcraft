import subprocess, sys, json, time
from pathlib import Path
from datetime import datetime
base = Path.cwd()
out = base/'evidence'/'1663-671b6672'/'coderabbit-increment.json'
while True:
    r = subprocess.run([sys.executable, str(base/'review_state.py')], capture_output=True, text=True)
    if r.returncode == 0 and out.exists():
        d = json.loads(out.read_text(encoding='utf8'))
        if d['reviews'] or d['inline']:
            print(datetime.now().isoformat(), 'review', len(d['reviews']), 'inline', len(d['inline']), flush=True)
            break
        busy = any('review in progress by coderabbit.ai' in v['body'] for v in d['conversation'])
        clean = any('No actionable comments' in v['body'] or 'No reviewable changes' in v['body'] for v in d['conversation'] if 'summarize by coderabbit' not in v['body'])
        if clean and not busy:
            print('no actionable comments review', flush=True); break
    elif r.returncode:
        print(f'poll ret={r.returncode}: {r.stderr[-600:]}', flush=True)
        if 'has not requested a review' in r.stderr:break
    time.sleep(45)
