"""Measure pitch after time translation only, comparing two hardware chase takes to local playback."""
from functools import lru_cache

from splice_diagnosis import waveform, ref, old, hzfft, autocorr_hz, window, cents, sensitivity
from acquisition_analysis import np, root, json, rate

fresh = "smu-phase-live-1795135619954155100"
standard_centers = (50, 75, 100, 125, 150)


def lag_at(x, y, ms):
    template = window(x, ms, 480)
    search = window(y, ms, 1920)
    squares = np.r_[0.0, np.cumsum(search ** 2)]
    energies = squares[480:] - squares[:-480]
    scores = np.correlate(search, template) / np.sqrt(np.maximum(energies, 1e-24) * max(template @ template, 1e-24))
    k = int(scores.argmax())
    return dict(t=ms, lag=k - 720, r=float(scores[k]))


def corr(a, b):
    return float((a @ b) / np.sqrt((a @ a) * (b @ b)))


def frequencies(y, hz):
    return np.array([hzfft(y, hz), autocorr_hz(y, hz)])


def first_pair(anchors):
    for i, a in enumerate(anchors):
        for b in anchors[i+1:]:
            if abs(a["t"] - b["t"]) >= 10 and min(a["r"], b["r"]) >= .995 and abs(a["lag"] - b["lag"]) <= 2:
                return a["lag"]
    return None


def frame(y, center, lag):
    i = 2400 + center * 48 + lag
    return y[i-1024:i+1024]


def audit_note(base, note):
    sec = note["score_seconds"]
    midi = note["expected_pitch"]
    hz = 440 * 2 ** ((midi - 69) / 12)
    x, n = waveform(base, sec)
    y, _ = waveform(ref, sec)
    assert n["expected_pitch"] == midi
    anchor = lru_cache(None)(lambda t: lag_at(x, y, t))
    fixed, dense = [], []
    for dt in range(25, 201):
        z = frame(x, dt, 0)
        fp = frequencies(z, hz)
        ends = [[anchor(dt + direction*d) for d in (27, 32, 37, 42)] for direction in (-1, 1)]
        pairs = [first_pair(side) for side in ends]
        # Each candidate is from a disjoint template. The centre waveform identifies
        # the local phase branch, without consulting either pitch estimator.
        lags = {v for v in pairs if v is not None} | {side[0]["lag"] for side in ends}
        middle = anchor(dt)
        lag = min(sorted(lags), key=lambda v: abs(v - middle["lag"]))
        def profile(v):
            matched = frame(y, dt, v)
            fft, period = cents(fp, frequencies(matched, hz))
            return dict(lag=v, fft=float(fft), period=float(period), r=corr(z, matched))
        p = profile(lag)
        dense.append(dict(ms=dt, **p, middle_lag=middle["lag"], middle_r=middle["r"],
                          stable_pair=lag in pairs, pairs=pairs))
        if dt in standard_centers:
            fixed.append(dict(ms=dt, best=p, ends=ends, pairs=pairs, middle=middle,
                              alternatives=[profile(v) for v in sorted(lags) if v != lag],
                              raw=cents(fp, frequencies(frame(y, dt, 0), hz)).tolist()))
    return dict(sec=sec, midi=midi, fixed=fixed, dense=dense)


if __name__ == "__main__":
    notes = json.loads((root / (ref + "-acquisition.json")).read_text())["notes"]
    assert [n["score_seconds"] for n in notes] == [5, 5.5, *range(6, 23)]
    result = dict(reference=ref, rate_hz=rate, window_samples=2048, sensitivity=sensitivity(), takes={})
    for base in (old, fresh):
        result["takes"][base] = [audit_note(base, n) for n in notes]
    (root / "mtc-19-note-registration.json").write_text(json.dumps(result, separators=(",", ":"), allow_nan=False))

