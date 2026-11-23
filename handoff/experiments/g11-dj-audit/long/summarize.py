"""Summarize only PCM onset records acquired by the Rust audit."""
from pathlib import Path
import csv
from collections import defaultdict
from math import ceil

base = Path(__file__).parent
groups = defaultdict(list)
with (base / 'eighths.csv').open() as f:
    for row in csv.DictReader(f):
        groups[int(row['song']), row['phase']].append(row)

def stats(rows):
    measured = [float(r['delta_ms']) for r in rows if r['delta_ms']]
    absolute = sorted(map(abs, measured))
    missing = sum(not r['actual_sample'] for r in rows)
    repeats = len(rows) - len({r['eighth'] for r in rows})
    damaged = sum(r['waveform_exact']=='false' for r in rows)
    return [len(rows)-repeats, missing, repeats, damaged, min(measured),
            absolute[ceil(.95*len(absolute))-1], max(measured), measured[-1]]

def display(cells):
    return '| '+' | '.join(f'{v:.3f}' if isinstance(v,float) else str(v) for v in cells)+' |'

out = [
    '# 20 首連續混音的 PCM 驗收',
    '',
    '每首有 32 小節固定速度，相鄰歌曲之間附加 16 或 32 小節線性變速，交替共 19 段。速度介於 118 與 132 BPM。全程只送一次 Start，保持同一個 MIDI 跟隨器、速度圖、取樣器與混音引擎。測試以模擬時間前進，逐取樣讀取 48 kHz PCM；每個八分音符的聲音長度為 96 samples。測試為本機 ignored，沒有加入 PR。',
    '',
    '固定 128-sample 音訊區塊上限，網格編輯保護時間為 30 ms。在一個音符與下一個音符參考時間的中點分隔配對區間；每個區間零個起音計為漏音，超過一個計為重複。逐段比對每個起音的完整 96-sample 波形與第一下；尾音損壞也獨立計數。正值為晚，負值為早。',
    '',
    '| 首／段 | BPM（開始→結束） | 預期音數 | 漏音 | 重複 | 損壞 | 最早 ms | 絕對 p95 ms | 最晚 ms | 末音 ms |',
    '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|',
]
for (song, phase), rows in sorted(groups.items()):
    out.append(display([f'{song} '+('定速' if phase=='song' else '過渡'),
                        f"{float(rows[0]['bpm']):.2f} → {float(rows[-1]['bpm']):.2f}",
                        *stats(rows)]))
all_rows=[r for rows in groups.values() for r in rows]
out.append(display(['合計','118–132',*stats(all_rows)]))
out+=['','[逐八分音符的參考與實際 sample、帶正負號偏差和尾音](eighths.csv) · [執行紀錄與變速誤觸數](render.log) · [本機測試原始碼](../dj/repo/crates/ui-egui/src/app/clock_follow/tests/dj_long.rs)']
(base/'LONG.zh-TW.md').write_text('\n'.join(out)+'\n', encoding='utf-8')
print(out[-3])
