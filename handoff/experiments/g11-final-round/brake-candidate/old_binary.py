from pathlib import Path
import os
root=Path('../brake-candidate')
rsp=(Path(os.environ['TEMP'])/'cargo-argfile.5WCpUi').read_text(encoding='utf-8').splitlines()
dirs=[('-L',rsp[i+1]) for i,a in enumerate(rsp) if a=='-L']
externs=dict(rsp[i+1].split('=',1) for i,a in enumerate(rsp) if a=='--extern')
args=['--edition=2024','--test',str(root/'red.rs'),'-C','opt-level=1','-o',str(root/'red.exe')]
for pair in dirs:args+=pair
for name in ['soundcraft_mix','soundcraft_time','soundcraft_model','soundcraft_midi','soundcraft_playback','craft_audio']:
 args+=['--extern',name+'='+externs[name].replace('.rmeta','.rlib')]
(root/'red.rsp').write_text('\n'.join(args),encoding='utf-8')
base=Path('crates/ui-egui/src/app')
code=(base/'clock_follow.rs').read_text(encoding='utf-8')
code='use soundcraft_playback::midi::MidiInputs;\n'+code[code.index('use soundcraft_playback::clock_follow'):code.index('#[derive(Default)]')]+code[code.index('fn update_grid('):code.index('#[cfg(test)]\nmod tests')]
for name in ['sampler_song','dj_render','dj_tempos','brake','packet_steps']:
 code+=f'\nmod {name} {{\n'+(base/'clock_follow/tests'/f'{name}.rs').read_text(encoding='utf-8')+'\n}'
(root/'red.rs').write_text(code,encoding='utf-8')
