"""Replay the 192-point previous slope and four-source-pulse period at onset."""
import csv
import statistics
from pathlib import Path

base = Path(__file__).resolve().parent
with (base / 'threshold-at-fourth.csv').open('w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['case','previous_192_slope_us','candidate_period_us',
                     'apparent_pct','rounding_adjusted_pct'])
    for line in (base / 'dj/stimulus.tsv').read_text().splitlines():
        name, _, cut, _, _, raw = line.split('\t')
        if not name.startswith('edge_'):
            continue
        stamps = list(map(int, raw.split(',')))
        cut = int(cut)
        pulse = cut + 4
        old = statistics.linear_regression(range(pulse-192,pulse),
                                          stamps[pulse-192:pulse]).slope
        period = (stamps[pulse] - stamps[cut])/4
        apparent = abs(old-period)/period*100
        adjusted = (abs(old-period)+1/4)/period*100
        writer.writerow([name,old,period,apparent,adjusted])
