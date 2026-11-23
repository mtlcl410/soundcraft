from pathlib import Path
p=Path(__file__).resolve().parent/'analysis_audio.py'
s=p.read_text(encoding='utf-8-sig').replace("examples=[('128','repeat-128/exact-a'),('64','repeat-64/late-b')]","examples=[('64-cold','repeat-64/exact-a')]").replace('listening-key.json','listening-key-cold.json')
assert '64-cold' in s
exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
