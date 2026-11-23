from pathlib import Path
import shutil,hashlib,sys,json,wave
root=Path(__file__).resolve().parent
label,song=sys.argv[1:3]
src=Path('H:/MTR')/song
assert src.is_dir() and src.parent==Path('H:/MTR')
dest=root/label/song
dest.mkdir(parents=True,exist_ok=True)
rows=[]
for no in ('01','02','11','12'):
 f,=src.glob('*_TR'+no+'.wav')
 out=dest/f.name
 if not out.exists():shutil.copyfile(f,out)
 digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 sh=digest(f);assert digest(out)==sh
 with wave.open(str(out),'rb') as w:
  rows.append(dict(name=f.name,channel=no,sha256=sh,bytes=out.stat().st_size,frames=w.getnframes(),rate=w.getframerate(),depth=w.getsampwidth()*8))
(root/(label+'-sd.json')).write_text(json.dumps(rows,indent=2))
print(rows)
