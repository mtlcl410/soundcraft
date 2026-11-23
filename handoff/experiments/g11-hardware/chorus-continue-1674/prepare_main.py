from pathlib import Path
p=Path("chorus_monitor.py")
s=p.read_text().replace("import os, time, sys, threading, json","import os, time, sys, threading, json, wave")
s=s.replace("def render(out,n,t,flags):","""take=None
frames=[]
def save(name, chunks):
    if not chunks or not name:return
    with wave.open(str(here/(name+'-main.wav')),'wb') as w:
        w.setparams((2,2,44100,0,'NONE','')); w.writeframes(b''.join(c[1] for c in chunks))
    (here/(name+'-main-times.json')).write_text(json.dumps([c[0] for c in chunks]))
def render(inputs,out,n,t,flags):
    rx_time=time.perf_counter()+t.inputBufferAdcTime-t.currentTime
    if take:
        frames.append(([rx_time,n],(np.clip(inputs,-1.,.99996)*32768).astype('<i2').tobytes()))""")
s=s.replace("sd.OutputStream(device=target,extra_settings=sd.AsioSettings(channel_selectors=[8,9])","sd.Stream(device=(target,target),extra_settings=(sd.AsioSettings(channel_selectors=[10,11]),sd.AsioSettings(channel_selectors=[8,9]))")
s=s.replace("time.sleep(.5)","""time.sleep(.05)
            name=(here/'route-take.txt').read_text().strip() if (here/'route-take.txt').exists() else None
            if name!=take:
                prev=take; take=None
                old_frames=frames; frames=[]
                take=name
                save(prev,old_frames)""")
s=s.replace("time.monotonic()-begin<1:", "time.monotonic()-begin<.1:")
Path("main_return.py").write_text(s)
