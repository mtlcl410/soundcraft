from pathlib import Path
import json
import statistics as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
here=Path(__file__).resolve().parent
s=json.loads((here/'stage-summary.json').read_text())
rows=json.loads((here/'per-take.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.right':False,'axes.spines.top':False,'axes.spines.left':False,'text.color':'#162d42','axes.labelcolor':'#162d42'})
fig,(a,b)=plt.subplots(2,1,figsize=(10.1,7.4),gridspec_kw={'height_ratios':[1,1.1]})
fig.subplots_adjust(left=.27,right=.95,top=.80,bottom=.18,hspace=.84)
fig.suptitle('Where the Model 12 MAIN return adds time',x=.04,y=.965,ha='left',fontsize=21,weight='bold')
fig.text(.04,.902,'S-MU2000 chorus at 8.000 s   /   same playback build   /   120 BPM',fontsize=12)
p=s['previous']; mean=lambda key:p[key]['mean']
positions=[mean('digital_ms'),mean('digital_ms')+mean('taps_ms'),mean('main_ms')-mean('output_to_main_ms'),mean('main_ms')]
labels=['Digital loopback','Monitor capture','ASIO output callback','MAIN USB return']
a.set_title('A   Original six takes, mean crash arrival after the first Clock',loc='left',size=12,weight='bold',pad=11)
for i,(pos,label) in enumerate(zip(positions,labels)):
    a.hlines(3-i,0,pos,color='#d0dfe5',lw=3)
    a.scatter(pos,3-i,s=60,color='#306783',zorder=3)
    a.text(pos+1.8,3-i,f'{pos:.1f}',va='center',fontsize=10,weight='bold')
a.set_yticks(range(3,-1,-1),labels);a.set_xlabel('Milliseconds from first Clock');a.set_xlim(0,90);a.set_ylim(-.55,3.55)
b.set_title('B   Same hardware, changing only the monitor prefill',loc='left',size=12,weight='bold',pad=12)
conditions=[('bridge_to_output_ms','Monitor capture → ASIO'),('output_to_main_ms','ASIO → MAIN'),('digital_to_main_ms','Digital loopback → MAIN')]
for i,(key,label) in enumerate(conditions):
    for q,y,co,mk in [(40,2-i+.12,'#456484','o'),(20,2-i-.12,'#008576','s')]:
        vals=[r[key] for n,r in rows.items() if n.startswith('queue'+str(q)) and r['spp']==64]
        b.scatter(vals,[y+(j-1.5)*.022 for j in range(4)],c=co,marker=mk,s=32,alpha=.86,label=f'{q} ms prefill' if i==0 else None)
        b.text(max(vals)+1.4,y,f'{st.mean(vals):.1f}',va='center',fontsize=9.5,color=co,weight='bold')
b.set_yticks([2,1,0],[label for _,label in conditions]);b.set_ylim(-.45,2.49)
b.set_xlim(0,max(r['digital_to_main_ms'] for r in rows.values() if r['spp']==64)+10);b.set_xlabel('Measured interval (ms)');b.legend(loc='upper center',bbox_to_anchor=(.47,-.27),frameon=False,ncol=2,fontsize=10)
for ax in (a,b):ax.set_axisbelow(True);ax.grid(axis='x',color='#dbe5eb',lw=.7);ax.tick_params(axis='y',length=0)
fig.text(.04,.060,'A: independent digital capture callbacks account for the signed offset between the first two rows.',fontsize=9.5)
fig.text(.04,.032,'B: four exact starts per setting; dots are takes, labels are means. MAIN includes the USB recording return.',fontsize=9.5)
fig.savefig(here/'midi-clock-main-return.png',dpi=160,facecolor='white')

