from partition import *
proj=json.loads((old/'smu-model12-chase.scraft').read_text())
notes=proj['tracks'][0]['playlists'][0]['clips'][0]['content']['Midi']['sequence']['notes']
signals={tag:pcm(next((old/tag).glob('*/*_TR02.wav'))) for tag in ['take1','take2r','take3r']}
rows=[]
for n in notes:
 t=n['start']/1920
 if t<3:continue
 a=round((t+.02)*sr);template=signals['take1'][a:a+3600]
 if len(template)!=3600 or np.max(abs(template))<0.002:continue
 row={'song_s':t,'midi':n['pitch']}
 for tag in ['take2r','take3r']:
  lo=a-5760
  i,cc=match(signals[tag][lo:a+5760+len(template)],template)
  row[tag]=[round((lo+i-a)/48,3),round(cc,4)] if abs(cc)>=.96 else [None,round(cc,4)]
 rows.append(row)
(d/'note-alignment.json').write_text(json.dumps(rows,indent=2))
print(rows)
