import unittest
import numpy as np
from benchmarks.analyze_loopback import estimate_delay


class LoopbackAnalysisTests(unittest.TestCase):
    def test_known_delay_with_gain_and_noise(self):
        rng=np.random.default_rng(8); x=rng.normal(size=12000); delay=777
        y=np.r_[np.zeros(delay),x[:-delay]]*.4+rng.normal(0,.005,len(x))
        result=estimate_delay(x,y,16000,100)
        self.assertEqual(result['delay_samples'],delay)
        self.assertGreater(result['normalized_correlation'],.99)

    def test_silence_cannot_produce_latency_claim(self):
        with self.assertRaises(ValueError): estimate_delay(np.zeros(100),np.zeros(100),16000)

    def test_search_boundary_is_flagged(self):
        x=np.random.default_rng(1).normal(size=10000)
        y=np.r_[np.zeros(160),x[:-160]]
        self.assertTrue(estimate_delay(x,y,16000,10)['review_required'])


if __name__=='__main__': unittest.main()
