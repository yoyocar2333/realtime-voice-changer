import unittest
import numpy as np
from benchmarks.benchmark_f0 import yin_difference, yin_f0, synth, summarize, SR


class BenchmarkTests(unittest.TestCase):
    def test_difference_matches_direct_sum(self):
        x=np.random.default_rng(9).normal(size=200)
        d=yin_difference(x,30)
        expected=[sum((x[:170]-x[k:k+170])**2) for k in range(31)]
        np.testing.assert_allclose(d,expected,atol=1e-10)

    def test_yin_recovers_known_period(self):
        for f0 in (80,110,160,220,280):
            x,_=synth('tone_'+str(f0),0.1,2)
            estimate,voiced=yin_f0(x[1000:1000+1764])
            self.assertTrue(voiced)
            self.assertLess(abs(1200*np.log2(estimate/f0)),5)

    def test_silence_is_unvoiced(self):
        self.assertFalse(yin_f0(np.zeros(1764))[1])

    def test_missed_frames_are_counted_in_error_rate(self):
        base=dict(method='ACF',window_ms=40,snr_db=0,kind='steady',true_voiced=True,compute_s=.001)
        rows=[dict(base,pred_voiced=True,error_cents=5),dict(base,pred_voiced=False,error_cents=0)]
        s=summarize(rows)[0]
        self.assertEqual(s['median_abs_cents'],5)
        self.assertEqual(s['error_over_50c_or_miss'],.5)
        self.assertEqual(s['voiced_miss_rate'],.5)


if __name__=='__main__': unittest.main()
