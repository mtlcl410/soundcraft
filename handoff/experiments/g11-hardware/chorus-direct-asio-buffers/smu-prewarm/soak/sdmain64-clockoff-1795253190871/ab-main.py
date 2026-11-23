from pathlib import Path
import sys,json,secrets,wave,numpy as np
case=Path(sys.argv[1]).resolve();E={'__file__':str(case/'sd-landmarks.py')}
exec(compile((case/'sd-landmarks.py').read_text(encoding='utf-8-sig').split('res={}')[0],E['__file__'],'exec'),E)
wav=E['wav']; rate=44100
q=json.loads((case/'four-paths.json').read_bytes())
evs=json.loads((case/'transition-fit.json').read_bytes());i=max(range(len(evs)),key=lambda i:evs[i]['delta'])
e=evs[i];before=q['paths'][0]['offset_changes'][i]['before'];buf=E['buf']
x=np.column_stack([wav(c) for c in (3,4)])
event=e['usb_frame']+before['sd_minus_usb']+before['sd_analog_minus_internal']
pos=min(e['out_frame']//rate,539)
choices=[]
for bars in range(-34,35):
 if bars==0 or not 2<pos+bars*16<537:continue
 approx=event+16*bars*rate
 window=4096
 pre=event-6144
 post=event+2048
 shifts=[];scores=[]
 for o in (pre,post):
  r=x[o:o+window].mean(axis=1); lo=approx+(o-event)-4800; s=x[lo:lo+window+9600].mean(axis=1)
  sc=E['corr_scores'](s,r);k=int(sc.argmax());shifts.append(k-4800);scores.append(float(sc[k]))
 choices.append((min(scores),approx+shifts[0],scores,shifts))
score,ref,scores,shifts=max(choices)
assert score>.97,(score,scores,shifts)
lead=round(.75*rate);duration=round(1.6*rate);items=[x[a-lead:a-lead+duration].copy() for a in (event,ref)]
assert all(len(v)==duration for v in items)
levels=[np.sqrt(np.mean(v*v,dtype='f8')) for v in items]
for i,v in enumerate(items):
 v/=levels[i];v[:220]*=np.linspace(0,1,220)[:,None];v[-220:]*=np.linspace(1,0,220)[:,None]
g=.70/max(np.max(np.abs(v)) for v in items)
key=case/'blind-key.json'
bl=json.loads(key.read_bytes())['event_index'] if key.exists() else secrets.randbelow(2)
sig=np.vstack((items[bl],np.zeros((round(.85*rate),2)),items[1-bl]))*g
with wave.open(str(case/f'listen-main-{buf}-AB.wav'),'wb') as w:
 w.setparams((2,2,rate,0,'NONE','not compressed'));w.writeframes(np.round(32767*sig).astype('<i2').tobytes())
key.write_text(json.dumps(dict(event_index=bl,event_frame=event,comparison_frame=ref,correlations=scores,local_offsets=shifts,rms_before_normalization=levels,common_gain=float(g),excerpt_seconds=duration/rate,pause_seconds=.85,marker_in_excerpt=.75),indent=2))
print('validated A/B',buf,score)


