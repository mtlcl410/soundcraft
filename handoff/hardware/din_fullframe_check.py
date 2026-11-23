"""MIDI-only cross-check for full-frame byte differences; no SoundCraft, ASIO or SD access."""
from pathlib import Path
import csv,json,os,sys,time,contextlib
hw=Path(__file__).resolve().parent
sys.path.insert(0,str(hw/'midi'))
from midi_path import live_midi
from wire_source import sleep_until
from collections import Counter
def run(folder):
    # Reuse the four locate/stop positions from the failing 24 and 25 fps takes.
    full=[bytes.fromhex(h) for h in ['f07f7f010100000000f7','f07f7f010100000200f7','f07f7f010120000800f7','f07f7f010120000a00f7']]
    result=[]
    for direction,send,receive in [('forward','UM-ONE','Model 12 MIDI'),('reverse','Model 12 MIDI','UM-ONE')]:
      for clients in [1,2]:
        with contextlib.ExitStack() as leases:
            port,inbox,ports=leases.enter_context(live_midi(tx_name=send,rx_name=receive))
            second=None
            if clients==2:
                _,second,_=leases.enter_context(live_midi(rx_name=receive))
            time.sleep(.5)
            while not inbox.empty():
                _,msg,_=inbox.get_nowait()
                if msg[0]!=0xfe:raise RuntimeError(f'Input not idle on {receive}')
            if second is not None:
                while not second.empty():second.get_nowait()
            for profile in ('locates','quarter-frames-and-locates'):
                expected=[];transmitted=[]
                def write(msg,tag):
                    now=time.perf_counter_ns()
                    port.send_message(list(msg));expected.append(msg.hex());transmitted.append((now,tag,msg.hex()))
                count=200 if profile=='locates' else 120
                for i in range(count):
                    # The gap after each full-frame allows the ten bytes to clear the DIN wire.
                    write(full[i%4],f'locate-{i}')
                    time.sleep(.025)
                    if profile!='locates':
                        origin=time.perf_counter_ns()
                        for j in range(8):
                            sleep_until(origin+j*10_416_667)
                            write(bytes((0xf1,16*j)),f'qf-{i}-{j}')
                        time.sleep(.012)
                time.sleep(.18)
                actual=[]
                while not inbox.empty():
                    t,msg,_=inbox.get_nowait()
                    if msg[0]!=0xfe:actual.append((t,bytes(msg).hex()))
                other=[]
                if second is not None:
                    while not second.empty():
                        t,msg,_=second.get_nowait()
                        if msg[0]!=0xfe:other.append((t,bytes(msg).hex()))
                stem=folder/f'{direction}-{clients}-{profile}'
                if second is not None:
                    with (folder/(stem.name+'-observer2.csv')).open('x',newline='') as f:
                        w=csv.writer(f);w.writerow(['qpc_ns','hex']);w.writerows(other)
                for name,header,records in [('sent',['qpc_ns','tag','hex'],transmitted),('received',['qpc_ns','hex'],actual)]:
                    with (folder/(stem.name+'-'+name+'.csv')).open('x',newline='') as f:
                        w=csv.writer(f);w.writerow(header);w.writerows(records)
                full_tx=[h for h in expected if h.startswith('f0')]
                full_rx=[h for _,h in actual if h.startswith('f0')]
                unequal=[dict(index=i,sent=a,received=b) for i,(a,b) in enumerate(zip(full_tx,full_rx)) if a!=b] if len(full_tx)==len(full_rx) else None
                row=dict(clients=clients,observers_agree=([h for _,h in actual]==[h for _,h in other]) if second is not None else None,direction=direction,profile=profile,ports=ports,locates_sent=len(full_tx),locates_received=len(full_rx),
                         all_bytes_equal=expected==[h for _,h in actual],differences=unequal,
                         unexpected_full_shapes=dict(Counter(h for h in full_rx if h not in {msg.hex() for msg in full})))
                result.append(row);print(row,flush=True)
                (folder/'byte-comparison.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__':run(Path(os.environ['SOUNDCRAFT_ACCEPTANCE_RUN']))

