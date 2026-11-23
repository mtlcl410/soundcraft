"""Measure an impulse train at the native ASIO switch in a private test directory."""
from pathlib import Path
import json, os, sys, subprocess, struct
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"g11-hardware/capture-deps"))
import numpy as np
import wave

root = Path(__file__).resolve().parent
rate = 48000

def stimulus():
    times = [12000, 21849, 35937, 49634, 65341, 79212]
    data = np.zeros(96000, dtype='<i2')
    rng = np.random.default_rng(1662)
    for i in times:
        data[i:i+127] = rng.choice([-1024, 1024], 127)
    return data, times

def read_blocks(folder):
    meta_file, = folder.glob('epoch-*.json')
    meta = json.loads(meta_file.read_text())
    n = meta['buffer']
    dtype = np.dtype([('pos','<u8'),('system','<u8'),('qpc','<u8'),('serial','<u8'),('flags','<i4'),('n','<u4'),('pcm','<f4',(n,2))])
    path = meta_file.with_suffix('.bin')
    if path.stat().st_size % dtype.itemsize: raise ValueError('partial callback')
    a = np.fromfile(path, dtype=dtype)
    if len(a) < 2 or not np.all((a['flags'] & 2) != 0): raise ValueError('missing valid ASIO sample positions')
    if not np.all(a['n'] == n) or not np.all(np.diff(a['pos']) == n) or not np.all(np.diff(a['serial']) == 1):
        raise ValueError('missing or irregular callback sequence')
    return meta,a['pcm'].reshape(-1,2),a

def measure(folder):
    meta, pcm, blocks = read_blocks(folder)
    source, markers = stimulus()
    x, y = pcm.T
    idx = np.where(abs(x) > 0.00001)[0]
    starts = idx[np.r_[True, np.diff(idx)>3000]] if len(idx) else []
    if len(starts)!=len(markers): raise ValueError(f'unexpected transmitted marker count {len(starts)}')
    offsets=[]
    scores=[]
    for i in starts:
        ref=x[i:i+127].astype(float)
        samples=y[i:i+8192].astype(float)
        corr=np.correlate(samples,ref,mode='valid')
        peak=int(np.argmax(np.abs(corr)))
        target=samples[peak:peak+len(ref)]
        score=float(abs(corr[peak])/max(1e-12,np.linalg.norm(ref)*np.linalg.norm(target)))
        if not (score>.85 and max(abs(target))>1.e-5):raise ValueError(f'no unique matching return at output {i}, corr {score:.4f}, peak {max(abs(target))}')
        offsets.append(peak); scores.append(round(score,5))
    reported=meta['input_latency']+meta['output_latency']
    return dict(offsets=offsets,correlations=scores,reported_samples=reported,difference_samples=[v-reported for v in offsets],driver=meta)

if __name__=='__main__':
    folder=Path(os.environ['SOUNDCRAFT_ACCEPTANCE_RUN'])
    n, channel, runs=map(int,sys.argv[1:])
    data,_=stimulus()
    data.tofile(folder/'markers.raw')
    with wave.open(str(folder/'markers.wav'),'wb') as stream:
        stream.setparams((1,2,rate,0,'NONE',''));stream.writeframes(data.tobytes())
    for i in range(runs):
        dest=folder/f'take-{i+1:02d}';dest.mkdir()
        result=subprocess.run([str(root/'build/independent.exe'),str(rate),str(n),str(folder/'markers.raw')],env=os.environ|{'SC_ASIO_EVIDENCE':str(dest),'SC_ASIO_RETURN_INDEX':str(channel)},capture_output=True,timeout=20)
        (dest/'player.log').write_bytes(result.stdout+result.stderr)
        result.check_returncode()
        meta,_,blocks=read_blocks(dest)
        device=dict(device='Model Mixer ASIO', sample_rate=meta['sample_rate'],buffer_frames=int(blocks['n'][0]))
        if i==0:(folder/'device-start.json').write_text(json.dumps(device))
        (folder/'device-end.json').write_text(json.dumps(dict(device,buffer_frames=int(blocks['n'][-1]))))
        assert device['sample_rate']==rate and device['buffer_frames']==n
        summary=measure(dest)
        (dest/'summary.json').write_text(json.dumps(summary,indent=2))
        print(i+1,summary['offsets'],summary['reported_samples'],flush=True)
