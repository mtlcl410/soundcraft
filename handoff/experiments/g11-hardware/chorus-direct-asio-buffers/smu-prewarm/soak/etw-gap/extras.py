exec(open('partition.py',encoding='utf-8-sig').read().split('details=[]')[0])
thread_info={}
for score,thread in scores[:3]:
 info=s['threadInfo'][str(thread)].split(' ',1);thread_info[thread]=(score,driver(int(info[0])),info[-1])
rec=read(case/'record.json');anchor=sum(rec['anchors'])//2
first=next(t+anchor for t,m in rec['events'] if m==[248]);last=next(t+anchor for t,m in rec['events'] if m==[252]);work=[]
for row in a[(a[:,1]>=first)&(a[:,1]<last)&(a[:,2]>b/44100*1e9)]:
 serial,t,d,*_=map(int,row);lo=t-d
 intervals=[(max(l,lo),min(r,t),c) for l,r,c in spans[tid] if l<t and r>lo]
 off=d-sum(r-l for l,r,c in intervals)
 interrupts=[(min(r,end)-max(l,start),c,name,k) for l,r,c,name,k in irqs for start,end,core in intervals if core==c and l<end and r>start]
 work.append(dict(serial=serial,elapsed_ms=d/1e6,offcpu_ms=off/1e6,foreign_elapsed_ms=(int(row[7])>>12)/1e6,same_cpu_irq_max_ms=max((v[0]/1e6 for v in interrupts),default=0)))
from collections import Counter
c=Counter()
for serial,lo,hi,delta in g['rows']:
 for l,r,core in spans[tid]:
    if l<hi and r>lo:c[core]+=1
print(thread_info,work[:3])
Path(f'extras-{b}.json').write_text(json.dumps(dict(thread_candidates=thread_info,overruns=work,cores=c,transport=[(i,rec['events'].count(i)) for i in []],midi_clocks=sum(1 for _,m in rec['events'] if m==[248]),actual_buffer=b,clock_duration_s=(last-first)/1e9,serial_gaps={name:gaps(load_wave(case/(name+'.bin'))['serial']) for name in ['in','out']}),indent=2))
