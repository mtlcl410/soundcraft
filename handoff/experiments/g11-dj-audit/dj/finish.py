from pathlib import Path
import csv
p=Path(__file__).parent
def rows(f):
 with (p/f).open() as h:return list(csv.DictReader(h))
def write(f,rr):
 with (p/f).open('w',newline='') as h:
    w=csv.DictWriter(h,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
notes=rows('notes.csv');cases=rows('cases.csv')
diff=rows('differential/velocity-isolation.csv');name='brake_2b_silent_coast'
iso={r['note_id']:r for r in diff if r['case']==name}
assert len(iso)==4 and all(int(x['span_samples'])==96 for x in iso.values())
target=next(x for x in notes if x['case']==name and x['eighth']=='37')
for tag in ['37','38']:
 if tag=='38':
    entry=target.copy();entry['eighth']=tag;notes.insert(notes.index(target)+1,entry)
 else:entry=target
 entry.update(on_sample=iso[tag]['on_sample'],tail_samples=iso[tag]['span_samples'],template_match='overlap',status='post-source')
for x in cases:
 x['overlapped_unscored_attacks']='0'
 if x['case']==name:
    assert x['after_last_f8_extra']=='3' and x['damaged']=='1'
    x['after_last_f8_extra']='4';x['damaged']='0';x['overlapped_unscored_attacks']='2'
by_name={x['case']:x for x in cases}
for row in notes:
 c=by_name[row['case']]; rel=None if not row['on_sample'] else int(row['on_sample'])-int(c['terminal_sample'])
 row['onset_minus_last_scored_F8_ms']='' if rel is None else f'{rel/48:.6f}'
 row['onset_minus_FC_ms']='' if rel is None or c['ending']!='stop' else f'{rel/48-3:.6f}'
write('notes-isolated.csv',notes);write('cases-isolated.csv',cases)
