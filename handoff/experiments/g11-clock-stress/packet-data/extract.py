from pathlib import Path
import re,ast,csv,sys
folder=Path('E:/soundcraft/compatibility-audit/g11-clock-stress/packet-data')
file=folder/sys.argv[1]
s=file.read_text(encoding='utf-8-sig')
hits={k:ast.literal_eval(v) for k,v in re.findall(r'HITS (\S+) (\[.*\])',s)}
steps={k:ast.literal_eval(v) for k,v in re.findall(r'STEPS (\S+) (\[.*\])',s)}
def signed(x):return '+'+str(x) if x>=0 else str(x)
summary=[]
rows=[]
for label,miss,extra,damaged,loss,early,confirm in re.findall(r'CASE (\S+) missing=(\d+) extra=(\d+) damaged=(\d+) dropouts=(\d+) early_steps=(\d+) confirmations=(\d+)',s):
 if label not in hits or label not in steps:continue
 arr=hits[label];st=steps[label];ss=label.split('-')
 if label.startswith('A4'):
  tr=28800;before=after=120;mode='A4(group='+ss[-1]+')'
 else:before,after,tr=map(int,ss[:3]);mode=ss[3]
 times=[i/2*60/before if 12*i<=tr else tr/24*60/before+(i/2-tr/24)*60/after for i in range(len(arr))]
 for i,(ti,offs) in enumerate(zip(times,arr)):
  rows.append((label,i,12*i,round(ti*48000),';'.join(signed(x) for x in offs),';'.join(f'{x/48:+.4f}' for x in offs),int(not offs),max(0,len(offs)-1)))
 k=tr//12;half=arr[k+1] if k+1<len(arr) else []
 later=[x for bucket in arr[k+2:k+17] for x in bucket]
 post=[x for x in st if x[0]>tr]
 in_old=sum(i<=tr for i,n in st)
 additional=sum(i>tr for i,n in st)-int(bool(post))
 all2=sum(n==2 for i,n in st)
 summary.append((label,mode,before,after,tr,len(arr),miss,extra,damaged,loss,in_old,additional,all2,(';'.join(f'{x/48:+.4f}' for x in half) or '-'),f'{max(map(abs,later))/48:.4f}' if later else '-',post[0][0]-tr if post else '-',post[0][1] if post else '-',f'{max(abs(x) for a in arr for x in a)/48:.4f}'))
def save(name,header,data):
 with (folder/(file.stem+'-'+name+'.csv')).open('w',newline='',encoding='utf8') as f:
  w=csv.writer(f);w.writerow(header.split());w.writerows(data)
save('eighths','case eighth pulse expected_sample errors_samples errors_ms missed excess',rows)
save('summary','case delivery from_bpm to_bpm transition count missing excess damaged dropouts false_before extra_after two_interval first_offbeat_ms from_second_beat_peak_ms first_confirm_delay_pulses confirm_intervals whole_run_peak_ms',summary)
print('cases',len(summary),'onsets',len(rows))
for row in summary:
 print(row[0],row[6:14],row[14:])

