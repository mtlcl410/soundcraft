"""H-1/H-2, physical Beat Clock against independently generated and observed audio markers."""
import csv, json, math, os, sys, time, wave
from pathlib import Path
from manual_run import hw, desktop, cmd, live_midi, save
from m1 import np, read_blocks

def schedule(rate, duration, mapped):
    # Four quarters of 120, four at 90, eight ramp quarters, four at 120.
    bpms = [120]*4 + [90]*4 + [90+6*i for i in range(8)] + [120]*4 if mapped else [120]*int(2*duration)
    bounds = np.r_[0., np.cumsum(60/np.asarray(bpms, dtype=float))]
    ticks = [round((t+k*60/bpm/24)*rate) for t,bpm in zip(bounds,bpms) for k in range(24)]
    return bpms, [round(x*rate) for x in bounds], ticks

def acquire(folder, side, rate, n, duration, offset, mapped):
    out, inp = ('UM-ONE','Model 12 MIDI') if side=='forward' else ('Model 12 MIDI','UM-ONE')
    bpms, beats, ticks = schedule(rate,duration,mapped)
    marker=np.random.default_rng(1662).choice([-1024,1024],127).astype('<i2')
    wav=folder/'click.wav'
    with wave.open(str(wav),'wb') as w:
        w.setparams((1,2,rate,0,'NONE',''))
        for a,b in zip(beats,beats[1:]):
            w.writeframesraw(marker.tobytes()+bytes(2*(b-a-len(marker))))
    with desktop(folder,wav,n,rate) as port, live_midi(rx_name=inp) as (_,rx,ports):
        cfg=cmd(port,'setup.midi_beat_clock')
        save(folder/'clock-settings.json',cmd(port,'setup.midi_beat_clock',enabled=True,ports={out:dict(enabled=True,offset_samples=offset)},compensation=dict(cfg['compensation'],beat_clock=True)))
        for i,bpm in enumerate(bpms):
            if i==0 or bpms[i-1]!=bpm:cmd(port,'event.tempo',at=beats[i],bpm=bpm)
        if mapped:
            cmd(port,'event.meter',at=beats[4],numerator=7,denominator=8)
            cmd(port,'event.meter',at=beats[12],numerator=5,denominator=4)
        cmd(port,'options.loop_playback',value=False)
        cmd(port,'edit.select',start=0,end=beats[-1])
        time.sleep(.65)
        while not rx.empty():rx.get()
        cmd(port,'transport.play_selection')
        time.sleep(.4)
        save(folder/'running.json',dict(transport=cmd(port,'transport.status'),diagnostics=cmd(port,'setup.midi_sync_status')))
        time.sleep(max(0,beats[-1]/rate-.1))
        state=cmd(port,'transport.status')
        if state['playing']:cmd(port,'transport.stop')
        time.sleep(.3)
        cut=time.perf_counter_ns()
        cmd(port,'transport.locate',at=round(.875*rate))
        time.sleep(.65)
        data=[]
        while not rx.empty():
            stamp,msg,_=rx.get()
            if msg!=(254,):data.append((stamp,bytes(msg).hex()))
        with (folder/'wire.csv').open('x',newline='') as f:
            w=csv.writer(f);w.writerow(['qpc_ns','hex']);w.writerows(data)
        save(folder/'stop.json',dict(state=state,locate_before=cut,ports=ports,diagnostics=cmd(port,'setup.midi_sync_status')))
        cmd(port,'setup.midi_beat_clock',enabled=False)
    return analyse(folder,side,rate,n,beats,ticks,cut,data,offset)

def analyse(folder,side,rate,n,beats,ticks,cut,data,offset):
    tx=np.asarray([t for t,msg in data if msg=='f8' and t<cut],dtype=float)/1e6
    loc=[msg for t,msg in data if t>=cut]
    meta,pcm,blocks=read_blocks(folder/'driver')
    # Use individual marker transitions after verifying the coded waveform on both paths.
    starts=[]
    m=np.random.default_rng(1662).choice([-1.,1.],127)
    for ch in (0,1):
        matches=[]
        for base in range(0,len(pcm),rate*5):
            idx=np.flatnonzero(abs(pcm[base:base+rate*5,ch])>.001)+base
            if len(idx):matches.extend(idx[np.r_[True,np.diff(idx)>rate//30]].tolist())
        unique=[]
        for idx in matches:
            if unique and idx-unique[-1]<rate//30:continue
            s=pcm[idx:idx+127,ch].astype(float)
            if len(s)!=127 or abs(s@m)/(np.linalg.norm(s)*np.linalg.norm(m))<.85:continue
            unique.append(idx)
        starts.append(unique)
    result=dict(planned_ticks=len(ticks),received_ticks=len(tx),expected_markers=len(beats)-1,output_markers=len(starts[0]),input_markers=len(starts[1]),offset_samples=offset,stopped_messages=loc,exact_spp=loc==['f20700'])
    save(folder/'result.json',result)
    if len(starts[0])!=len(beats)-1 or len(starts[1])!=len(starts[0]) or not len(tx):return result
    sr=meta['sample_rate'];fq=meta['qpc_frequency']
    def at(idx):
        return blocks['qpc'][idx//n].astype(float)*1000/fq+(idx%n)*1000/sr
    tx_start=np.asarray(starts[0]);rx_start=np.asarray(starts[1])
    path=hw/f'runs/m2-{side}-c/data/m2-result.json'
    m2=json.loads(path.read_text())['path_delay']['median_ms']
    if rate==48000:
        ruler=sorted((hw/f'runs/m1-integration-{n}-formal-01').glob('take-*/summary.json'))
        m1=float(np.median([v for p in ruler for v in json.loads(p.read_text())['offsets']]))
    else:
        m1=float(np.median(rx_start-tx_start))  # Same-rate observed transfer. Do not substitute the 48 kHz ruler.
    result.update(m2_ms=m2,loop_reference_samples=m1,loop_reference='M1' if rate==48000 else 'same-take 44.1 kHz cross-check',loop_observed_samples=[int(min(rx_start-tx_start)),int(max(rx_start-tx_start))])
    indices=np.arange(min(len(ticks),len(tx)))
    expected_idx=tx_start[0]+np.array(ticks[:len(indices)])
    # Anchor to actual device time of the buffer that contains each pulse. QPC is callback entry.
    # Presentation is estimated using the driver's separate output latency, not the full loop latency.
    output_t=at(expected_idx)+meta['output_latency']*1000/sr
    err=tx[indices]-m2-output_t
    groups=np.arange(min(len(starts[0]),(len(tx)+23)//24))
    click=at(rx_start[groups])-m1*1000/sr+meta['output_latency']*1000/sr
    resid=tx[groups*24]-m2-click
    def summary(x):
        return dict(median_ms=float(np.median(x)),p99_abs_ms=float(np.percentile(abs(x),99,method='higher')),max_abs_ms=float(max(abs(x))))
    result.update(pulse_schedule=summary(err),click_residual=summary(resid),calibration_recommended_samples=-round(float(np.median(resid))*sr/1000),
                  exact_ticks=len(tx)==len(ticks),complete_sequence_alignment_verified=len(tx)==len(ticks) and np.max(np.abs(err-np.median(err)))<min(np.diff(ticks))*500/sr)
    for name,arr in [('pulse',err),('click',resid)]:
        np.savetxt(folder/f'{name}-error-ms.csv',arr,fmt='%.6f',header='signed_ms',comments='')
    save(folder/'result.json',result)
    return result

if __name__=='__main__':
    side,rate,n,seconds,offset,kind=sys.argv[1:]
    print(acquire(Path(os.environ['SOUNDCRAFT_ACCEPTANCE_RUN']),side,int(rate),int(n),int(seconds),int(offset),kind=='map'))

