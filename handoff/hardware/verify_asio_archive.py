"""Reanalyse the original hardware files without changing their reports or opening devices."""
import csv,json,sys
from pathlib import Path
from storage_idle_acceptance import hw,read_window,save
from storage_sdk_run import histogram
from m1 import measure
from analyse_chase import analyse
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
runs=hw/'runs'
out=runs/'asio-idle-archive-recheck';out.mkdir(exist_ok=True)
def messages(path):
    with path.open() as f:return list(csv.DictReader(f))
data={'cadence':{},'loopback':{},'mtc':{}}
for name in ['storage-main-i24-01','h3b-model12-01','storage-native-sdk-01','storage-native-reopen-01']:
    d=runs/name
    h=read(runs/'asio-environment-histogram.json') if name.startswith('h3b') else read(d/'histograms.json')
    rows={}
    for key,ref in h.items():
        if name.startswith('h3b'):ref=ref['roll']
        q=[int(r['qpc_ns']) for r in messages(d/key/'rx.csv') if r['hex'].startswith('f1')]
        assert len(q)==960,(name,key,len(q))
        if name.startswith('storage-native'):
            a=histogram(d,[q[0],q[-1]],read(d/'native.json')['qpc_hz']);median=a['median_ms']
        else:
            a=read_window(d,q[0],q[-1]);median=a['median']
        assert a['bins']==ref['bins'] and a['intervals']==ref['intervals'] and abs(median-ref['median_ms'])<1e-6,(name,key)
        rows[key]=dict(intervals=a['intervals'],median_ms=median,bins=a['bins'])
    data['cadence'][name]=rows
for name in ['m1-independent-128-a','m1-independent-256-a','m1-independent-512-c']+[f'm1-integration-{n}-formal-01' for n in (128,256,512)]:
    offsets=[]
    for d in sorted((runs/name).glob('take-*')):
        m=measure(d);ref=read(d/'summary.json')
        assert m['offsets']==ref['offsets'] and m['correlations']==ref['correlations'],d
        offsets.extend(m['offsets'])
    assert len(offsets)==120
    data['loopback'][name]=dict(markers=len(offsets),min_samples=min(offsets),max_samples=max(offsets),spread=max(offsets)-min(offsets))
class AnalysisDirectory:
    def __init__(self,d):self.d=d
    def __truediv__(self,name):
        return out/(self.d.name+'-markers.json') if name=='marker-phase.json' else self.d/name
for d in [*sorted(runs.glob('h4a-integration-*-01')),runs/'h4b-model12-02']:
    h4b=d.name.startswith('h4b')
    if not h4b:
        ref=read(d/'result.json')
        tx,rx=([r['hex'] for r in messages(d/file) if r['hex'].startswith(('f1','f0'))] for file in ['tx.csv','wire.csv'])
        assert tx==rx,d
        loc=read(d/'locates.json')
        assert len(loc)==20 and all(not r['actual']['playing'] and r['actual']['position']==r['expected_sample'] for r in loc),d
    raw=analyse(AnalysisDirectory(d),'30' if h4b else ref['rate'])
    assert raw==read(d/'marker-phase.json'),d
    onsets=[r['markers'][0]['rx']['ms'] for r in raw]
    spread=round(max(onsets)-min(onsets),4)
    if not h4b:assert onsets==ref['onsets_ms'] and spread==ref['spread_ms'],d
    data['mtc'][d.name]=dict(takes=len(raw),spread_ms=spread,locates=None if h4b else len(loc))
save(out/'result.json',data)
print('All archived comparisons matched.')
