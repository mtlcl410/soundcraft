from pathlib import Path
import sys,json
f=Path(__file__).resolve().parent;d=f.parent;sys.path.insert(0,str(d));p=d/'measure.py';s=p.read_text(encoding='utf-8-sig')
s=s.replace("d/'metrics.json'","d/'waveform-followup'/'retest.json'")
exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
rows=json.loads((f/'retest.json').read_bytes())
assert len(rows)==6*(len(sys.argv)-1)
assert all(r['crashes']==int(r['spp']==64) and r['clocks']==144 and r['later_corr']>.90 and r['serial_gaps']==[0,0] for r in rows.values())
print('PASS',len(rows))

