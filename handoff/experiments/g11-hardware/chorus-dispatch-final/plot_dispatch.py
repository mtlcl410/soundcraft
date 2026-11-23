from pathlib import Path
import json,statistics as stats
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.ticker import MultipleLocator
root=Path(__file__).resolve().parent.parent
def get(name): return json.loads((root/name/'final-acceptance.json').read_text())
before=get('chorus-dispatch-before')
after=get('chorus-dispatch-final')
clean=get('chorus-dispatch-release')
keys=list(before)
assert list(after)==list(clean)==keys
for group in (before,after,clean):
 for k,v in group.items():
  assert v['ticks']==144 and v['main_count']==v['digital_count']==int(v['spp']==64) and v['later_music_correlation']>.9
for k,v in after.items(): assert v['submitted_ms'] < v['input_to_ui_ms'],k
def dispatch(v):return v['input_to_ui_ms']+v['ui_to_start_ms']+v['prepare_session_ms']
def series(g,f,only=False):return [f(v) for v in g.values() if not only or v['spp']==64]
def stat(xs):return dict(min=min(xs),max=max(xs),mean=stats.mean(xs),median=stats.median(xs))
info=dict(before_dispatch=stat(series(before,dispatch)),after_dispatch=stat(series(after,lambda v:v['submitted_ms'])),
 before_wake=stat(series(before,lambda v:v['wake_return_ms'])), before_host=stat(series(before,lambda v:v['logic_entry_ms'])),
 before_frame_work=stat(series(before,lambda v:v['input_to_ui_ms']-v['logic_entry_ms'])),after_host=stat(series(after,lambda v:v['logic_entry_ms'])),
 before_audio=stat(series(before,lambda v:v['digital_ms'],True)),after_audio=stat(series(after,lambda v:v['digital_ms'],True)),
 release_audio=stat(series(clean,lambda v:v['digital_ms'],True)))
d=root/'chorus-dispatch-final'
(d/'comparison.json').write_text(json.dumps(info,indent=2))
palette=['#466989','#008377']
plt.rcParams.update({'font.size':11,'font.family':'DejaVu Sans','axes.spines.right':False,'axes.spines.top':False,'axes.labelcolor':'#23384b','text.color':'#182e42','axes.titleweight':'bold'})
fig,axes=plt.subplots(2,1,figsize=(9,6.6),layout=None)
fig.subplots_adjust(left=.26,right=.94,bottom=.18,top=.83,hspace=.76)
fig.suptitle('External MIDI Clock resume after a settled locate',x=.04,y=.974,ha='left',fontsize=19,fontweight='bold')
fig.text(.04,.907,'Eight-bar S-MU2000 session  |  120 BPM  |  Model 12 DIN OUT to UM-ONE',fontsize=11)
def plot(ax,sets,title):
 ax.set_title(title,loc='left',pad=12,fontsize=12)
 ax.set_axisbelow(True);ax.grid(axis='x',color='#d8e3ea',linewidth=.7)
 for row,(name,vals,co) in enumerate(sets):
  y=len(sets)-row
  ax.plot([min(vals),max(vals)],[y,y],color=co,lw=2)
  for j,v in enumerate(vals):
   off=(-.15+j*.3/(len(vals)-1))
   ax.scatter(v,y+off,s=28,color=co,zorder=3)
 ax.set_yticks(list(range(len(sets),0,-1)),[x[0] for x in sets]);ax.set_ylim(.48,len(sets)+.52);ax.set_xlim(-1,None)
 ax.set_xlabel('Milliseconds from first incoming Clock')
plot(axes[0],[('Previous dispatch',series(before,dispatch),palette[0]),('Prepared dispatch',series(after,lambda v:v['submitted_ms']),palette[1])],'A   Playback command, eight starts per build')
axes[0].scatter([31.188],[2],facecolor='white',edgecolor=palette[0],marker='D',zorder=5)
axes[0].annotate('Earlier 31.2 ms host wait',xy=(31.188,2),xytext=(23,1.27),fontsize=9,arrowprops={'arrowstyle':'-','color':palette[0]})
axes[0].set_xlim(-1,35);axes[0].xaxis.set_major_locator(MultipleLocator(5))
plot(axes[1],[('Previous',series(before,lambda v:v['digital_ms'],True),palette[0]),('Fixed',series(after,lambda v:v['digital_ms'],True),palette[1]),('Fixed, probes removed',series(clean,lambda v:v['digital_ms'],True),'#6a537c')],'B   Recorded crash at 8.000 s, six takes per build')
fig.text(.04,.062,'Each dot is one take. Timing probes bracket submission; audio onset uses the same recorded crash template.',fontsize=9)
fig.text(.04,.029,'All three runs: one crash per 8.000 s start, none at 8.125 s (two takes each), on both digital and MAIN returns.',fontsize=9)
fig.savefig(d/'midi-clock-resume-dispatch.png',dpi=165,facecolor='white')
print(json.dumps(info,indent=2))
