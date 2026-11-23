from analysis_audio import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
fig,(a,b)=plt.subplots(2,1,figsize=(9.5,5.9),layout='constrained')
fig.suptitle('Where the Model 12 MAIN return diverged',fontsize=17,fontweight='bold')
ref='#075873';ret='#c36622'
key='repeat-128/exact-a';x,y,_=pair(key);on=read(d/'localize.json')[key]['out_onset_frame']
k=np.arange(on-120,on+580);t=(k-on)/44.1;a.plot(t,x[k,0],c=ref,lw=1.15,label='ASIO 9/10, scaled');a.plot(t,y[k,0],c=ret,lw=.95,label='MAIN 11/12')
a.axvspan((51136-on)/44.1,(51200-on)/44.1,color='black',alpha=.13,label='Flagged 64 samples');a.set_title('128 frames · first crash after opening the stream',loc='left');a.set_xlabel('Time relative to the rendered onset (ms)');a.legend(ncol=3,fontsize=8,loc='upper right')
key='repeat-64/late-b';x,y,_=pair(key);on=read(d/'localize.json')[key]['out_onset_frame']
i=on+int(np.argmax(np.max(abs(x[on:on+rate]-y[on:on+rate]),axis=1)));kk=np.arange(i-110,i+110);t=(kk-on)/44.1
b.plot(t,(y-x)[kk,0],color=ret,lw=1.05,label='Residual with one delay for the whole take');b.plot(t,y[kk,0]-x[kk-5,0],color=ref,lw=1.15,label='Residual allowing 5 samples here')
b.set_title('64 frames · 8.125 s start, before the timing shift',loc='left');b.set_xlabel('Time from the first accompaniment sound (ms)');b.legend(ncol=1,fontsize=8,loc='upper right')
for ax in (a,b):
 ax.set_ylabel('16-bit PCM counts (L)');ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.18);ax.set_axisbelow(True)
fig.savefig(d/'midi-clock-asio-waveform-detail.png',dpi=150)

