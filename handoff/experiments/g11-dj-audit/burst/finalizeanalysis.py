from pathlib import Path
p=Path(__file__).parent
f=p/'analyze.py';s=f.read_text(encoding='utf-8')
s=s.replace('hits=defaultdict(list); pulses=defaultdict(list)','hits=defaultdict(list); pulses=defaultdict(list); assigned=defaultdict(list)')
s=s.replace("['PULSE','HIT']","['PULSE','HIT','ASSIGN']")
s=s.replace('else: pulses[key].append(v)',"elif tag=='PULSE': pulses[key].append(v)\n    else: assigned[key].append(v)")
s=s.replace('assert len(hits)==12','assert len(hits)==16\nassert hits.keys()==assigned.keys()')
s=s.replace("for k,rows in hits.items():\n        for row in rows: w.writerow([*k,*row,round(int(row[3])/48,6)])","for k,rows in assigned.items():\n        for row in sorted(rows,key=lambda x:int(x[0])): w.writerow([*k,*row,round(int(row[3])/48,6) if row[3] else ''])")
s=s.replace('notes_outside_half_width','missing_expected_slots').replace("'extra','malformed'","'extra_attacks_or_unmatched','malformed'")
s=s.replace('at_sample','at_sample')
f.write_text(s,encoding='utf-8')
