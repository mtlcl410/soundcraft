from pathlib import Path
s=Path(__file__).parent/'source/src'
def edit(name,a,b):
 p=s/name;t=p.read_text(encoding='utf8');assert a in t
 with p.open('w',encoding='utf8',newline='\n') as f:f.write(t.replace(a,b))
edit('mame/cpu/sh2_jit.cpp','bool sh2_device::jit_run()', '#include "../../vst3/warm_probe.h"\nbool sh2_device::jit_run()')
edit('mame/cpu/sh2_jit.cpp','code = m_jit->compile(*this, pc);','{cold::timer t(4);code = m_jit->compile(*this, pc);}')
edit('vst3/plugin.cpp','jit=%lld msgs=%zu','jit=%lld sh=%lld midi=%lld msgs=%zu')
edit('vst3/plugin.cpp','cold::totals[3],m_msgs.size()', 'cold::totals[3],cold::totals[4],cold::totals[5],m_msgs.size()')
edit('vst3/engine.cpp','if (port < 0 || port > mu2000::MIDI_PORTS)','cold::timer measure_midi(5);\n\tif (port < 0 || port > mu2000::MIDI_PORTS)')

