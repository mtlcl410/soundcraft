"""Reconstruct two transitions from unmodified excerpts of the local reference recording."""
from register_chase_notes import np, root, json, rate, frame, corr, waveform, ref, fresh, frequencies, cents


def reconstruct(sec, center, left, right, transition_range, middle_lags=()):
    x, _ = waveform(fresh, sec)
    y, _ = waveform(ref, sec)
    hz = 440 * 2**(((65 if sec == 6 else 67)-69)/12)
    # Fit the waveform itself using alternate samples; do not use any pitch estimate in fitting.
    ix = 2400 + center*48 + np.arange(-1024, 1024)
    times = (ix-2400)/48
    actual = x[ix]
    def source(lag):
        return y[ix + lag]
    def fade(start):
        return np.clip((times - start)/10, 0, 1)
    baseline = source(right)
    def stats(v):
        predicted = frequencies(v, hz)
        delta = cents(predicted, frequencies(baseline, hz))
        a, b = actual[1::2], v[1::2]
        return dict(fft_vs_post=float(delta[0]), period_vs_post=float(delta[1]),
                    correlation=corr(a, b), relative_rms=float(np.linalg.norm(a-b)/np.linalg.norm(a)))
    models = {"fixed_pre": stats(source(left)), "fixed_post": stats(baseline), "recording": stats(actual)}
    def fit(allow_mid):
        best_loss = float("inf")
        for start in np.arange(*transition_range, .25):
            w = fade(start)
            for lag in (middle_lags if allow_mid else (right,)):
                joined = (1-w)*source(left) + w*source(lag)
                for distance in ((10,20) if allow_mid else (0,)):
                    v = joined if distance == 0 else joined + fade(start+distance)*(baseline-source(lag))
                    residual = (actual-v)[::2]
                    loss = residual @ residual
                    if loss < best_loss:
                        best_loss = loss
                        best = dict(start_ms=float(start), midlag=lag, second_after_ms=distance, **stats(v))
        return best
    models["one_join"] = fit(False)
    if middle_lags:
        models["two_joins"] = fit(True)
    return dict(sec=sec, center=center, pre=left, post=right, models=models)


if __name__ == "__main__":
    results = [reconstruct(12,154,127,499,(132,155),range(490,500)), reconstruct(6,25,-1,273,(10,26))]
    print(json.dumps(results,indent=1))
    (root / "mtc-19-note-splices.json").write_text(json.dumps(results,indent=2,allow_nan=False))
