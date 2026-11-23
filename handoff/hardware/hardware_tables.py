"""Tables from complete measurements only, preserving failed and missing evidence."""
from pathlib import Path
import json, statistics

def tables(root):
    def read(path):return json.loads(path.read_text('utf-8-sig'))
    runs=root/'runs'
    reference=[a for p in (runs/'m1-integration-256-formal-01').glob('take-*/summary.json') for a in read(p)['offsets']]
    if not reference:return ''
    loop=statistics.median(reference)/48
    lines=['','## H-4a　電腦產生 MTC，經實體 DIN 跟播','',
        '每格率、每方向各十次，從零和非零位置交替起播。起音取 USB 輸入 9 的編碼波形，時碼以另一介面實收的 quarter-frame 解碼。極差門檻為 3 ms。相對產生端的校正起音為回錄起音減去 M-1 的往返中位數，再加上該方向 M-2 的傳輸中位數；常數校正不會改變極差。','',
        '| 格率 | DIN 傳送端 → 接收端 | 有效起音／預期 | 定位錯誤／檢查 | QF 計數異常的段數 | 校正起音中位 ms | 極差 ms | 判定 |',
        '|---|---|---:|---:|---:|---:|---:|---|']
    for d in sorted(runs.glob('h4a-integration-*')):
        if not (d/'result.json').exists() or not (d/'environment-result.json').exists():continue
        s=read(d/'result.json');en=read(d/'environment-result.json')
        side=s['direction'];m2=read(runs/f'm2-{side}-c/data/m2-result.json')['path_delay']['median_ms']
        route='UM-ONE → Model 12' if side=='forward' else 'Model 12 → UM-ONE'
        state=('通過' if s['criteria_met'] else '未達門檻') if en['environment_valid'] else '環境無效'
        v=s['onsets_ms']; med=f'{statistics.median(v)-loop+m2:.3f}' if v else '—'
        spread=s['spread_ms'];show=f'{spread:.3f}' if spread is not None else '—'
        lines.append(f"| {s['rate']} | {route} | {len(v)}/10 | {len(s['locate_mismatches'])}/{len(read(d/'locates.json'))} | {len(s['quarter_frame_mismatches'])} | {med} | {show} | [{state}](runs/{d.name}/result.json) |")
    lines+=['','同一路徑上各次起音的散布包含 USB 傳輸、鎖定、ASIO 回呼與回送的不確定性。失去發送介面時的三種 Freewheel 行為另行驗收。']
    return '\n'.join(lines)+'\n'
