from pathlib import Path
p=Path('../edge-probe/make_pcm.py');s=p.read_text().replace('Path("../edge-probe/pcm.rs")','Path("../brake-candidate/integrated.rs")')
exec(compile(s,str(p),'exec'))
args=Path('../edge-probe/pcm.rsp').read_text().replace('..\\edge-probe\\pcm.', '..\\brake-candidate\\integrated.')
Path('../brake-candidate/integrated.rsp').write_text(args)
