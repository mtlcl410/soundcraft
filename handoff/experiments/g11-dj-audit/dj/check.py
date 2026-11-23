"""Local acceptance assertions against the real PCM audit; preserves every failing case."""
import unittest,csv
from pathlib import Path
from collections import defaultdict
D=Path(__file__).parent
def read(p):
 with (D/p).open() as f:return list(csv.DictReader(f))
class Audit(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.cases=read('cases-isolated.csv');cls.notes=defaultdict(list)
  for r in read('notes-isolated.csv'):cls.notes[r['case']].append(r)
 def test_continuously_arriving_clock_never_declares_loss_during_brake(self):
  for c in self.cases:
   if c['case'].startswith('brake'):
    with self.subTest(case=c['case']):self.assertEqual(int(c['dropouts_before_terminal']),0)
 def test_every_scored_note_is_played_once_and_complete(self):
  for c in self.cases:
   with self.subTest(case=c['case']):self.assertEqual((int(c['missing']),int(c['duplicates']),int(c['damaged'])),(0,0,0))
 def test_threshold_confirmations(self):
  for c in self.cases:
   name=c['case']
   if name.startswith(('edge','wobble','nudge','stair')):
    expected=int(name.startswith('edge') and abs(float(name.split('_')[1].removesuffix('pct')))>=8)
    with self.subTest(case=name):self.assertEqual(int(c['steps']),expected)
 def test_first_offbeat_ten_ms_and_second_beat_four_ms_after_double_or_half(self):
  for c in self.cases:
   if not c['case'].startswith('ratio'):continue
   rows=[r for r in self.notes[c['case']] if r['error_ms'] and int(r['eighth'])*12-int(c['cut_pulse'])>0]
   with self.subTest(case=c['case']):self.assertLessEqual(abs(float(c['first_off_ms'])),10)
   with self.subTest(case=c['case'],later=True):self.assertLessEqual(max(abs(float(r['error_ms'])) for r in rows if int(r['eighth'])*12-int(c['cut_pulse'])>=24),4)
if __name__=='__main__':unittest.main(verbosity=2)
