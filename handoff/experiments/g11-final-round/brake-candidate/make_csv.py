from pathlib import Path
import re, csv,sys,ast
path=Path(sys.argv[1])
with Path(sys.argv[2]).open('w',encoding='utf-8',newline='') as out:
 w=csv.writer(out);w.writerow(['brake_pulses','curve','input_jitter_us','end','eighth','error_ms','onsets','timecode_state_transitions','damaged_waveforms','unmatched_attacks','open_tail'])
 for line in path.read_text(encoding='utf-8').splitlines():
  match=re.search(r'brake (\d+) exponential=(true|false) jitter=(\d+) (.*?): eighth errors (\[.*?\]); state transitions .*?(\[.*?\]); earliest vs wire ([-\d.]+) samples, damage (\d+), extras (\d+), open tail (true|false)',line)
  if not match: continue
  length,exp,jitter,ending,attacks,trans,e,damaged,extra,tail=match.groups()
  for i,row in enumerate(ast.literal_eval(attacks)):
   w.writerow([length, 'exponential' if exp=='true' else 'linear',jitter,ending,i,'|'.join(f'{v/48:+.5f}' for v in row),len(row),trans,damaged,extra,tail])
