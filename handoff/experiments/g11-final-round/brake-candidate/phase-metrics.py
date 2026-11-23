from pathlib import Path
import re,ast,json
d=Path('../evidence');s=(d/'steady-final-short.log').read_text(encoding='utf8')
series={}
for m in re.finditer(r'(?m)^(nudge |ratio |threshold |build |wobble |one-percent tempo staircase)(.*?) signed eighth errors \(48 kHz samples\) (\[.*?\])',s,re.S):
 name=(m[1]+m[2]).strip().splitlines()[-1];arr=ast.literal_eval(''.join(m[3].splitlines()));group=name.split()[0]
 cut=384
 if group=='threshold':
  trial=int(re.search(r'trial (\d+)',name)[1]);cut+=trial
  group += ' below 8%' if abs(float(name.split()[1]))<8 else ' at or above 8%'
 elif group=='ratio':
  cut=int(re.search(r' at (\d+)',name)[1])
 elif group=='build':cut=384
 if group not in series:series[group]={'cases':0,'eighths':0,'min':0,'max':0,'worst_case':''}
 t=series[group];x=arr[(cut+11)//12:];t['cases']+=1;t['eighths']+=len(x)
 if max(map(abs,x))>max(abs(t['min']),abs(t['max'])):t['worst_case']=name
 t['min']=min(min(x),t['min']);t['max']=max(max(x),t['max'])
print(series)
(d/'phase-validated-short-metrics.json').write_text(json.dumps(series,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
