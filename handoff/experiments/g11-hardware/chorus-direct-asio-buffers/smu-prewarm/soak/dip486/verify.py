from original import *
import hashlib
from audio import analyse
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
boundary=read(here.parents[1]/'music-dip486-check64.json')
result={};perf=read(here/'splices.json')
for b in [64,128]:
    case=root.parent.parent/f'dip486-check{b}';ctl=read(case/'control.json')
    assert ctl['project_sha256']=='992c9ea2e252052261f326a03be545683f3bf9a59d1db5ab166a0acc1d5a7071'
    actual=read(case/'actual.json');assert actual['actual']=={'in':[b],'out':[b]}
    vals=[];raw=np.load(here/f'replay-{b}.npz')
    for key,v in boundary.items():
        if not key.startswith(case.name+'/'):continue
        j=read(case/(key.split('/')[-1]+'.json'))
        meta=dict(buf=b,anchors=[a[1] for a in j['anchors']],events=[[round(t*1e9),m] for t,m in j['events']])
        z=analyse(key,case,meta);hits=z['counts_8s_pattern']
        assert hits==[int(v['spp']==64)]*2 and v['later_corr']>.90 and v['serial_gaps']==[0,0] and not j['final']['playing']
        vals.append(dict(take=key,spp=v['spp'],crashes=hits,later_correlation=v['later_corr'],clocks=v['clocks'],gaps=v['serial_gaps'],dip_candidates=z['sliding_dips'],fixed_alignment_residual_step=v['peak_residual_step']))
    assert len(vals)==6
    for rr in perf[str(b)]:
        fit=rr['fit'];assert fit['flank_rms']<2
        if fit['length']:assert fit['quiet_rms']<2
    result[str(b)]=dict(takes=vals,raw_source_sha256=hashlib.sha256(raw['source'].tobytes()).hexdigest(),project=ctl,plugin=read(case/'loaded-plugin.json'))
assert result['64']['raw_source_sha256']==result['128']['raw_source_sha256']
(here/'verification.json').write_text(json.dumps(result,indent=2))
print('PASS 12 physical MIDI starts and matched ASIO/MAIN. Candidate count per size:',[sum(len(v['dip_candidates']) for v in r['takes']) for r in result.values()])

