"""H-4a DIN chase. Run once per frame rate and direction, 10 acquisitions per pair."""
import csv,json,os,sys,time,threading
from pathlib import Path
from manual_run import hw,desktop,cmd,live_midi,save
from wire_source import RATES, mtc, sleep_until
from analyse_chase import analyse

def test(f,rate,direction):
    tx_name,rx_name=('UM-ONE','Model 12 MIDI') if direction=='forward' else ('Model 12 MIDI','UM-ONE')
    label={'29.97nd':'29.97','29.97df':'29.97 Drop'}.get(rate,rate)
    num,den,_=RATES[rate]
    checks=[]
    with desktop(f,hw/'audio/manual-stimulus/chase-135s.wav') as port:
        save(f/'rate.json',cmd(port,'setup.session',frame_rate=label,start_timecode='00:00:00:00'))
        save(f/'online.json',cmd(port,'setup.mtc',input=rx_name,online=True,freewheel='frames',freewheel_frames=8))
        with live_midi(tx_name=tx_name,rx_name=rx_name) as (tx,rx,ports), (f/'tx.csv').open('x',newline='') as out:
            save(f/'ports.json',ports)
            raw=csv.writer(out);raw.writerow(['tag','due','send_qpc_ns','sent_qpc_ns','hex'])
            origin=time.perf_counter_ns()+500_000_000
            for due,msg,tag in mtc(rate,10):
                sleep_until(origin+due)
                stamp=time.perf_counter_ns();tx.send_message(list(msg))
                raw.writerow([tag,origin+due,stamp,time.perf_counter_ns(),bytes(msg).hex()])
                if msg[0]==240:
                    frame=int(tag.rsplit('-',1)[-1])
                    time.sleep(.35)
                    state=cmd(port,'transport.status')
                    diag=cmd(port,'setup.midi_sync_status')['mtc_chase']
                    checks.append(dict(tag=tag,expected_sample=round(frame*48000*den/num),actual=state,diagnostic=diag))
            time.sleep(.6)
            pulses=[]
            with (f/'wire.csv').open('x',newline='') as w:
                writer=csv.writer(w);writer.writerow(['qpc_ns','hex'])
                while not rx.empty():
                    stamp,msg,_=rx.get_nowait()
                    if msg[0]==254:continue
                    writer.writerow([stamp,bytes(msg).hex()])
                    if msg[0]==241:pulses.append(stamp)
            segments=[]
            for q in pulses:
                if not segments or q-segments[-1]['last']>600_000_000:
                    segments.append(dict(first=q,last=q,n=1))
                else:
                    segments[-1]['last']=q;segments[-1]['n']+=1
            save(f/'segments.json',segments)
            save(f/'locates.json',checks)
        cmd(port,'setup.mtc',online=False);cmd(port,'transport.stop')
    data=analyse(f,rate)
    values=[]
    for r in data:
        if not r['markers']:continue
        first=r['markers'][0]
        if min(first[c]['score'] for c in ('tx','rx'))>=.85:values.append(float(first['rx']['ms']))
    spread=round(max(values)-min(values),4) if len(values)==10 else None
    mismatch=[dict(tag=x['tag'],expected=x['expected_sample'],transport=x['actual']) for x in checks if x['expected_sample']!=x['actual']['position'] or x['actual']['playing']]
    missing=[(i,x['qfs']) for i,x in enumerate(data) if x['qfs']!=8*round(num/den*4)]
    save(f/'result.json',dict(rate=rate,direction=direction,onsets_ms=values,spread_ms=spread,locate_mismatches=mismatch,quarter_frame_mismatches=missing,
        criteria_met=len(data)==10 and len(checks)==20 and spread is not None and spread<=3 and not mismatch and not missing))
if __name__=='__main__':test(Path(os.environ['SOUNDCRAFT_ACCEPTANCE_RUN']),sys.argv[1],sys.argv[2])

