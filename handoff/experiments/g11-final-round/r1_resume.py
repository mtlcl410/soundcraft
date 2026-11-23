from pathlib import Path
import sys
d=Path(__file__).resolve().parent
sys.argv=[str(d/'verify.py'),'1662',str(d/'beat'),str(d.parent/'g11-review3-mtc-fix-target')]
src=(d/'verify.py').read_text(encoding='utf8')
s='rows=[]\nfor label,args in commands:'
assert src.count(s)==1
src=src.replace(s,'''rows=json.loads((results/'results.json').read_text(encoding='utf8'))
assert [r['check'] for r in rows] == ['soundcraft-playback','soundcraft-ui-egui'] and all(r['head']==head and r['code']==0 for r in rows)
for label,args in commands[2:]:''')
exec(compile(src,str(d/'verify.py'),'exec'),{'__file__':str(d/'verify.py'),'__name__':'__main__'})
