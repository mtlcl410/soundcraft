from pathlib import Path
import csv
d=Path(__file__).parent
with (d/'edge-fourth-f8.csv').open('w',newline='') as h:
 w=csv.writer(h);w.writerow(['case','source_before_bpm','input_four_interval_bpm','prior_192_f8_fit_bpm','apparent_change_pct','pass_threshold_with_rounding'])
 for line in (d/'stimulus.tsv').read_text().splitlines():
  name,b,cut,e,c,ts=line.split('\t')
  if not name.startswith('edge_'):continue
  t=list(map(int,ts.split(',')));i=int(cut)+4; vals=t[i-192:i];center=95.5
  slow=sum((j-center)*v for j,v in enumerate(vals))/sum((j-center)**2 for j in range(192));p=(t[i]-t[i-4])/4
  w.writerow([name,b,2.5e6/p,2.5e6/slow,abs(p-slow)/p*100,abs(p-slow)+.25>=p*.08])
