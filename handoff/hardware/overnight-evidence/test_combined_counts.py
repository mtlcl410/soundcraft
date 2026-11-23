"""Hardware acceptance on stored captures. Keep raw counts even if an SPP advanced the destination."""
import csv,json,os,unittest
from pathlib import Path
p=Path(os.environ.get('SC_SOAK_CAPTURE',Path(__file__).resolve().parent/'combined-isolated'))
class CombinedCounts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.status=json.loads((p/'result.json').read_text())
    def test_every_input_clock_reached_the_software_ingress(self):
        self.assertEqual(self.status['relayed_input'],self.status['expected_clock'])
    def test_output_count_includes_start_and_stop_boundaries(self):
        self.assertEqual(self.status['received_clock'],self.status['expected_clock'], self.status['controls'][:5])
    def test_mtc_quarter_frame_count_includes_start_and_stop_boundaries(self):
        self.assertEqual(self.status['received_qf'],self.status['expected_qf'])
    def test_no_qf_piece_discontinuity_within_the_run(self):
        self.assertEqual(self.status['discontinuous_qf_pieces'],0)
    def test_clock_follow_stayed_locked_after_acquisition(self):
        self.assertEqual(self.status['dropout_count'],0)
if __name__=='__main__':unittest.main()

