import csv,re,collections,hashlib,json,sys
from pathlib import Path
ev=Path(__file__).resolve().parent/'evidence'
def read(name):return (ev/name).read_text(encoding='utf8',errors='replace')
for side,files in {'old':['r2-onset-red.log','r4-phases-red.log','r2-long-red.log'],'new':['r2-actual-onset.log','r2-actual-phases.log','r2-actual-long.log']}.items():
 if not all((ev/f).exists() and 'test result:' in read(f) for f in files):continue
 docs=[read(f) for f in files]
 out=[]; cases=[]; notes=collections.defaultdict(list)
 for tag,text,src in [('ONSET','single to grouped',docs[0]),('PACKED','grouped slowdown',docs[1]),('DJ8','20 tracks',docs[2])]:
    for label,k,wire,hit,residual in re.findall(tag+r'_NOTE (.*?)eighth=(\d+) wire_samples=(\d+) measured_samples=(-?\d+) residual_samples=(-?\d+)',src):
      key=label.strip() or 'DJ8 grouped segment';k,wire,hit,residual=map(int,[k,wire,hit,residual])
      assert hit-wire==residual
      row=(text,key,k,wire,hit,residual,*[round(v/48,6) for v in (wire,hit,residual)])
      out.append(row);notes[text,key].append(row)
 qpat=r'ONSET (\S+) worst_late_samples=-?\d+ earliest_samples=-?\d+ missing=(\d+) extra=(\d+) damaged=(\d+) dropouts=(\d+)'
 det={('single to grouped',key):list(map(int,details)) for key,*details in re.findall(qpat,docs[0])}
 det.update({('grouped slowdown',key):list(map(int,details)) for key,*details in re.findall(r'CASE (\S+) missing=(\d+) extra=(\d+) damaged=(\d+) dropouts=(\d+)',docs[1])})
 det[('20 tracks','DJ8 grouped segment')]=[0]*4  # Verified by the complete PCM scan below.
 assert re.search(r'31264 scored eighths, 0 missing, 0 repeated, 0 unmatched, 0 changed waveforms, open tail false',docs[2])
 for (scope,case),series in notes.items():
    ws=[r[3] for r in series]; hits=[r[4] for r in series]; err=[r[5] for r in series]
    cases.append(dict(scope=scope,case=case,scored=len(series),wire_peak=max(ws),earliest_grid=min(hits),earliest_wire=min(err),max_late=max(0,max(err)),first_wire=ws[0],first_error=hits[0],first_residual=err[0],later_max_late=max(0,max(err[1:])),metrics=det[scope,case]))
 assert len(cases)==193,len(cases)
 with (ev/f'r2-{side}-per-eighth.csv').open('w',newline='',encoding='utf8') as f:
    cw=csv.writer(f);cw.writerow(['suite','case','eighth','wire_samples','error_samples','residual_samples','wire_ms','error_ms','residual_ms']);cw.writerows(out)
 (ev/f'r2-{side}-by-case.json').write_text(json.dumps(cases,indent=2),encoding='utf8')
 print(side)
 for suite in ['single to grouped','grouped slowdown','20 tracks']:
    v=[r for r in cases if r['scope']==suite]
    print(suite,len(v),'notes',sum(r['scored'] for r in v),'max wire',max(r['wire_peak'] for r in v),'earliest_grid',min(r['earliest_grid'] for r in v),'earliest_wire',min(r['earliest_wire'] for r in v),'max_late',max(r['max_late'] for r in v),'first_max_late',max(r['first_residual'] for r in v),'later',max(r['later_max_late'] for r in v),'counts',[sum(r['metrics'][i] for r in v) for i in range(4)])
    for bpm in [120,148]:
        u=[r for r in v if r['case'].startswith(str(bpm)+'-')]
        if u:print(bpm,min(r['earliest_grid'] for r in u),max(r['wire_peak'] for r in u),max(r['max_late'] for r in u))
 print('csv sha',hashlib.sha256((ev/f'r2-{side}-per-eighth.csv').read_bytes()).hexdigest())

