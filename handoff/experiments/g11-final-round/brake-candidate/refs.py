import re
from pathlib import Path
root=Path('../brake-candidate'); cmd=(root/'local_cmdline.txt').read_text(encoding='utf-8-sig')
args=['--edition=2024','--test',str(root/'pcm_probe.rs'),'-C','opt-level=1','-o',str(root/'pcm_probe.exe')]
for dep in re.findall(r'-L ([^ ]+)',cmd):
 args+=['-L',dep.strip()]
for name in ['soundcraft_mix','soundcraft_time','soundcraft_model','soundcraft_midi','craft_audio']:
 m=re.search(r'--extern '+name+'=([^ ]+)',cmd)
 if m: fn=m.group(1)
 else:
  dirs=[x.split('=',1)[1] for x in args if x.startswith('dependency=') and ('/'+ name.replace('_','-')+'/' in x.replace('\\','/'))]
  print(name,dirs)
  fn=str(next(Path(dirs[-1]).glob('lib'+name+'*.rlib')))
 args+=['--extern',name+'='+fn.replace('.rmeta','.rlib')]
(root/'pcm.rsp').write_text('\n'.join(args),encoding='utf-8')
