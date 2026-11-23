from pathlib import Path
import os,sys
a=Path(__file__).resolve().parent; d=a.parent
sys.path.insert(0,str(d))
os.environ.setdefault("SC_ACCEPTANCE_BUILD",str(d/'audio/build/f13949d9-build.json'))
src=(d/'soak_relay.py').read_text()
src=src.replace("tx_name='UM-ONE',rx_name='Model 12 MIDI'","tx_name='Model 12 MIDI',rx_name='UM-ONE'").replace("live_midi(rx_name='UM-ONE')","live_midi(rx_name='Model 12 MIDI')").replace("ports={'Model 12 MIDI':","ports={'UM-ONE':").replace("port='Model 12 MIDI',offset_samples","port='UM-ONE',offset_samples")
exec(compile(src,str(d/'soak_relay.py'),'exec'))

