import unittest
from counter_holdout import compare

class ClockForecast(unittest.TestCase):
    def test_sign_count_and_disjoint_training(self):
        for ppm in [-40,0,40]:
            row=dict(wall_s=600,effective_hz=48000*(1+ppm*1e-6),f8_excess=0,qf_excess=0,device_excess_ms=0)
            test=dict(row,effective_hz=47000,f8_excess=9,qf_excess=12,device_excess_ms=7)
            ans=compare([row,test]);self.assertEqual(ans['held_out_seconds'],600)
            self.assertAlmostEqual(ans['clock_residual'],9-ppm*600e-6*48,7)
            self.assertAlmostEqual(ans['qf_residual'],12-ppm*600e-6*120,7)
            self.assertAlmostEqual(ans['device_excess_minus_prediction_ms'],7-ppm*.6,7)
    def test_one_window_cannot_be_used_to_predict_itself(self):
        with self.assertRaises(ValueError):compare([{}])
