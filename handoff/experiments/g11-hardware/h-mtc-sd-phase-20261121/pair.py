from partition import *
from itertools import combinations
how=sys.argv[1]; folder=d/how; songs=[d/'sd'/v for v in sys.argv[2:]]
clock=wire(folder)
assert len(songs)>=len(clock)>0
pairs={}
for i in range(len(clock)):
 for j in range(i,i+len(songs)-len(clock)+1):
  r=analyze(folder,i,songs[j])
  conf=sum(abs(x['correlation']) for x in r['mic_markers'] if x['capture_origin_minus_wire_ms'] is not None)
  pairs[i,j]=(r,conf)
rank=sorted([(sum(pairs[i,j][1] for i,j in enumerate(ix)),ix) for ix in combinations(range(len(songs)),len(clock))],reverse=True)
print('mic alignment song indices, scores',rank)
if len(rank)>1 and rank[0][0]-rank[1][0]<0.5: raise SystemExit('ambiguous song pairing')
rows=[pairs[i,j][0] for i,j in enumerate(rank[0][1])]
for j,song in enumerate(songs):
 if j not in rank[0][1]:
  ch2=pcm(next(song.glob('*_TR02.wav')))
  i,cc=match(ch2[round(4.7*sr):round(5.45*sr)],ref)
  val=round((i/sr-.3)*1000,3)
  rows.append({'song':song.name,'sd_onset_ms':val if abs(cc)>.9 else None,'sd_match':round(cc,4),'first_qf_label_frames':None,'render_tap_minus_wire_ms':None,'mic_markers':[],'reason':'Audio endpoint invalidation; no simultaneous capture for this take.'})
rows.sort(key=lambda r:r['song'])
(folder/'partition.json').write_text(json.dumps(rows,indent=2))
print([(r['song'],r['sd_onset_ms'],r['render_tap_minus_wire_ms']) for r in rows])
