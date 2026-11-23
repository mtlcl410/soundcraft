from pathlib import Path
import json, statistics as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
d=Path(__file__).resolve().parent
before=json.loads((d.parent/'chorus-main-return-split'/'per-take.json').read_bytes());after=json.loads((d/'per-take.json').read_bytes())
old=[v['main_ms'] for k,v in before.items() if k.startswith('queue20') and v['spp']==64]
new=[v['first_clock_to_main_ms'] for v in after.values() if v['spp']==64]
assert len(old)==len(new)==4
fig,ax=plt.subplots(figsize=(8.7,4.4));fig.subplots_adjust(left=.28,right=.91,top=.71,bottom=.30)
fig.suptitle('First MIDI Clock to the recorded MAIN crash',x=.04,y=.96,ha='left',size=19,weight='bold',color='#183449')
fig.text(.04,.811,'S-MU2000   /   120 BPM   /   Model 12 outputs 9–10 and MAIN USB inputs 11–12',size=10.4)
for y,label,x,c in [(1,'20 ms monitor prefill',old,'#486984'),(0,'SoundCraft direct ASIO',new,'#007e70')]:
 ax.hlines(y,min(x),max(x),lw=2,color=c);ax.scatter(x,[y+.05*(i-1.5) for i in range(4)],s=43,color=c,zorder=3)
 ax.text(max(x)+1.7,y,f'{st.mean(x):.1f} ms',va='center',color=c,weight='bold')
ax.set_yticks([1,0],['20 ms monitor prefill','SoundCraft direct ASIO'])
ax.set_xlim(0,max(old+new)+13);ax.set_ylim(-.5,1.5);ax.set_xlabel('Milliseconds from the first Clock at UM-ONE');ax.tick_params(axis='y',length=0)
for key in ('top','left','right'):ax.spines[key].set_visible(False)
ax.grid(axis='x',color='#dce5ec');ax.set_axisbelow(True)
fig.text(.04,.116,'Each dot is a take, lines show ranges, and labels are means. The two routes were measured in separate runs.',size=9.2)
fig.text(.04,.057,'Per route: four exact 8.000 s starts each played one crash; two 8.125 s starts played none.',size=9.2)
fig.savefig(d/'midi-clock-direct-asio.png',dpi=170)

