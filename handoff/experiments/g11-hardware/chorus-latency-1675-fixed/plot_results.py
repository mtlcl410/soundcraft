from pathlib import Path
import json,sys
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
from assess import mono,matches
here=Path(__file__).resolve().parent
prev=here.parent/'chorus-latency-1674'
def data(p,f):return json.loads((p/f).read_text())
a,b=data(prev,'split.json'),data(here,'split.json')
plt.rcParams.update({'font.size':11,'axes.spines.right':False,'axes.spines.top':False,'font.family':'DejaVu Sans','figure.facecolor':'white','axes.titlelocation':'left','axes.labelcolor':'#344458'})
modes=['boundary-'+s for s in 'abcd']
def mean(d,k):return np.mean([d[m][k] for m in modes])
def style(ax):
 ax.grid(axis='x',color='#dce2e8',lw=.7);ax.set_axisbelow(True)
 for s in ['left','bottom']:ax.spines[s].set_color('#aab5c0')
fig,(p,q)=plt.subplots(2,1,figsize=(10.4,8.1),gridspec_kw={'height_ratios':[1,1.18]})
fig.subplots_adjust(left=.20,right=.96,top=.82,bottom=.20,hspace=.94)
fig.text(.04,.94,'External MIDI Clock resume latency',fontsize=22,weight='bold',color='#183148')
fig.text(.04,.89,'Same eight-bar session · 120 BPM · SPP 64 / Continue · four exact-position takes per build',fontsize=11)
cols=['#3b74a1','#bc590d','#238477','#75639a','#8092a5']
metrics=['input_to_ui_ms','prepare_session_ms','queue_to_callback_ms','callback_to_render_ms','render_to_digital_ms']
labels=['Input → host','Session preparation','Next callback','Mix first block','Render → loopback']
for y,d in [(1,a),(0,b)]:
 left=0.
 for k,col,l in zip(metrics,cols,labels):
  val=mean(d,k)
  p.barh(y,val,left=left,color=col,height=.48,label=l if y else None);left+=val
 p.text(left+.55,y,f'{mean(d,"digital_ms"):.1f} ms',va='center',fontsize=11,weight='bold')
p.set_xlim(0,max(mean(a,'digital_ms'),mean(b,'digital_ms'))+9);p.set_yticks([0,1],['Fixed','Before']);p.set_xlabel('Elapsed time from first Clock (ms)')
p.set_title('A   Average first-crash timing at digital loopback',fontweight='bold',pad=10)
p.legend(loc='upper left',bbox_to_anchor=(-.02,-.40),ncol=5,fontsize=8.6,frameon=False,handlelength=1.1,columnspacing=1.25);style(p)
q.set_title('B   Controlled changes to the monitor queue',fontweight='bold',pad=10)
control=data(here.parent/'chorus-latency-1675-final','split.json')
for y,ms in [(2,20),(1,40),(0,60)]:
 v={k:np.mean([control[f'queue{ms}-{s}'][k] for s in 'ab']) for k in ['bridge_to_output_ms','output_to_main_ms']};q.barh(y,v['bridge_to_output_ms'],height=.48,color='#3b74a1',label='Bridge capture → ASIO output callback' if y==2 else None)
 q.barh(y,v['output_to_main_ms'],left=v['bridge_to_output_ms'],height=.48,color='#238477',label='ASIO output callback → MAIN capture' if y==2 else None)
 end=v['bridge_to_output_ms']+v['output_to_main_ms'];q.text(end+.7,y,f'{end:.1f} ms',va='center',weight='bold')
q.set_yticks([0,1,2],['60 ms prefill','40 ms prefill','20 ms prefill']);q.set_xlabel('Elapsed time from bridge capture (ms)');q.set_xlim(0,max(v['bridge_to_output_ms']+v['output_to_main_ms'] for v in control.values() if 'bridge_to_output_ms' in v)+13);style(q)
h,l=q.get_legend_handles_labels();fig.legend(h,l,loc='center',bbox_to_anchor=(.54,.10),ncol=2,fontsize=9,frameon=False)
fig.text(.04,.042,'B shows means of two takes per prefill, tested in forward and reverse order with the same ASIO driver settings.',fontsize=9,color='#48596c')
fig.text(.04,.015,'Timing estimates use host callback timestamps. MAIN is the Model 12 USB stereo mix return; speakers were not measured.',fontsize=9,color='#48596c')
fig.savefig(here/'midi-clock-resume-latency.png',dpi=155);plt.close(fig)
fig,axes=plt.subplots(2,2,figsize=(10.4,6.6),sharex=True,gridspec_kw={'height_ratios':[1.1,1]})
fig.subplots_adjust(left=.105,right=.965,bottom=.18,top=.78,hspace=.55,wspace=.22)
fig.text(.045,.935,'Did the downbeat crash actually sound?',fontsize=22,weight='bold',color='#183148')
fig.text(.045,.875,'Two digital loopback takes, aligned to the first external Clock received after Continue.',fontsize=11)
maxamp=0; xlim=(-22,300)
for c,(mode,desc) in enumerate([('boundary-a','SPP 64  ·  8.000 s'),('later-a','SPP 65  ·  8.125 s')]):
 j=data(here,mode+'.json'); x=mono(here/(mode+'.wav'));a0=data(here,mode+'-analysis.json')
 t=next(t for t,n,m in j['midi'] if n.startswith('UM-ONE') and m[0]==248)
 blocks=j['blocks'];ends=np.cumsum([l[1] for l in blocks]);i=int(np.argmin([abs(l[0]-t) for l in blocks]));f0=ends[i]+(t-blocks[i][0])*48000
 r=np.arange(int(f0+xlim[0]*48),int(f0+xlim[1]*48),24);ts=(r-f0)/48
 peak=np.max(np.abs(x[r[:,None]+np.arange(24)]),axis=1)/32768
 maxamp=max(maxamp,peak.max())
 axes[0,c].fill_between(ts,0,peak,color='#3b74a1');axes[0,c].set_title(desc,fontweight='bold',fontsize=15)
 cr=mono(here/'Crash.wav')[200:2600];s=matches(x,cr)
 # Each candidate represents the onset, 200 samples before the matched fragment.
 score=np.max(s[r[:,None]+200+np.arange(24)],axis=1)
 axes[1,c].plot(ts,score,color='#238477',lw=1.3);axes[1,c].axhline(.9,color='#bc590d',ls='--',lw=1)
 axes[1,c].text(0.97,.91,('1 match' if a0['crash_count']==1 else f'{a0["crash_count"]} matches')+' in full take',ha='right',va='center',transform=axes[1,c].transAxes,fontsize=9,bbox={'facecolor':'white','edgecolor':'none','alpha':.92})
 for ax in axes[:,c]:
  ax.axvline(0,color='#57616d',lw=1,ls=':');ax.set_xlim(*xlim);style(ax)
 axes[1,c].set_ylim(-.1,1.09);axes[1,c].set_xlabel('Time from first Clock (ms)')
for ax in axes[0]:ax.set_ylim(0,1.12*maxamp)
axes[0,0].set_ylabel('Peak amplitude (FS)');axes[1,0].set_ylabel('Waveform correlation')
fig.text(.045,.075,'Top: recorded audio peaks in 0.5 ms bins. Bottom: waveform match to the same crash; dashed line marks the 0.90 threshold.',fontsize=9)
fig.text(.045,.043,'Counts span each full take through Stop and its recorded tail. The later accompaniment was present in both takes.',fontsize=9,color='#48596c')
fig.savefig(here/'midi-clock-resume-boundary.png',dpi=155);plt.close(fig)
