from pathlib import Path
import json, os, sys, time, queue
from midi_path import live_midi, F8
root=Path(os.environ['SOUNDCRAFT_ACCEPTANCE_RUN'])
directions=[('UM-ONE','MIDIIN2 (Model 12 MIDI)'),('MIDIOUT2 (Model 12 MIDI)','UM-ONE'),
            ('UM-ONE','Model 12 MIDI'),('Model 12 MIDI','UM-ONE')]
out=[]
for txname,rxname in directions:
    entry=dict(tx=txname,rx=rxname,received=[])
    try:
        with live_midi(txname,rxname) as (tx,q,ports):
            entry['ports']=ports
            for j in range(4):
                t=time.perf_counter_ns();tx.send_message([0xf8])
                try:
                    stamp,msg,_=q.get(timeout=.15);entry['received'].append([list(msg),(stamp-t)/1e6])
                except queue.Empty: pass
                time.sleep(.04)
    except Exception as e:entry['exception']=str(e)
    out.append(entry)
(root/'routes.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
