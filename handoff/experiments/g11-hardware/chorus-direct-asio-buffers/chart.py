from pathlib import Path
import json,statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
d=Path(__file__).resolve().parent
rows=json.loads((d/'metrics.json').read_text())
fig,ax=plt.subplots(figsize=(9,4.7),layout='constrained')
ax.set_title('First MIDI Clock to the Model 12 MAIN return',loc='left',fontsize=17,pad=20)
groups=[256,128,64];out={}
for i,b in enumerate(groups):
 rr=[(k,r) for k,r in rows.items() if r['size']==b];v=[r['ms'] for k,r in rr if 'ms' in r];assert len(v)==8 and len(rr)==12
 assert all(r['crashes']==int(r['spp']==64) and r['later_corr']>.90 for k,r in rr)
 med=statistics.mean(v)
 for k,r in rr:
    if 'ms' not in r:continue
    x=i+(-.12 if k.startswith('repeat') else .12)+(ord(k[-1])-ord('b'))*.036
    ax.scatter(x,r['ms'],marker='D' if r['peak_residual_step']>16 else 'o',s=60,facecolors='none' if k.startswith('repeat') else '#176684',edgecolors='#9c4920' if r['peak_residual_step']>16 else '#176684',linewidths=1.7,zorder=3)
 ax.hlines(med,i-.27,i+.27,color='#151f28',lw=1.7);ax.text(i+.31,med,f'{med:.1f}',va='center',fontsize=10)
 out[b]=dict(mean=round(med,3),lo=min(v),hi=max(v),flags=sum(r['peak_residual_step']>16 for k,r in rr),big=sum(r['steps_over_32']>0 for k,r in rr),drops=sum(r['drop_windows'] for k,r in rr),clip=sum(r['clipped_frames'] for k,r in rr),gaps=sum(sum(r['serial_gaps']) for k,r in rr),min_later=min(r['later_corr'] for k,r in rr),maxstep=max(r['peak_residual_step'] for k,r in rr),maxmain=max(r['main_peak_counts'] for k,r in rr))
ax.set_xticks(range(3),['256 frames','128 frames','64 frames']);ax.set_xlim(-.45,2.6);ax.set_ylim(0,max(r['ms'] for r in rows.values() if 'ms' in r)+5);ax.set_ylabel('Clock to MAIN (ms)');ax.set_xlabel('Measured ASIO callback size at 44.1 kHz');ax.grid(axis='y',alpha=.23);ax.spines[['top','right']].set_visible(False)
legend=[Line2D([],[],color='#151f28',label='Mean'),Line2D([],[],ls='',marker='o',color='#176684',label='First run'),Line2D([],[],ls='',marker='o',mfc='none',color='#176684',label='Reopened stream'),Line2D([],[],ls='',marker='D',mfc='none',color='#9c4920',label='Waveform deviation¹')]
ax.legend(handles=legend,ncol=4,loc='upper center',frameon=False,fontsize=9)
fig.supxlabel('¹ MAIN differed from the aligned ASIO 9/10 signal (residual step >16 counts in 16-bit PCM).',fontsize=9,color='#444')
fig.savefig(d/'midi-clock-asio-buffer-sizes.png',dpi=155);(d/'summary.json').write_text(json.dumps(out,indent=2));print(out)

