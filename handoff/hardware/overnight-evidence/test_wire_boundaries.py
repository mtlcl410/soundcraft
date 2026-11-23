import unittest
from wire_boundaries import assign_nearest

class WireEdges(unittest.TestCase):
    def test_startup_skip_and_stop_extension_are_separate(self):
        r=assign_nearest(list(range(0,80,10)),[61,71,81],10)
        self.assertEqual((r['first_matched'],r['last_matched'],r['missing_inside_matched_span'],r['outside_after_last']),(6,7,0,1))
    def test_missing_and_repeated_interior_pulse_are_both_detected(self):
        r=assign_nearest([0,10,20,30],[0,10,11,30],10)
        self.assertEqual((r['missing_inside_matched_span'],r['repeated_nearest_input']),(1,1))
    def test_exact_halfway_tie_is_ambiguous(self):
        r=assign_nearest([0,10],[5],10)
        self.assertEqual((r['matched'],r['equidistant']),(0,1))
