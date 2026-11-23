"""Write the live or final report from the first eligible attempt for each case, including failures."""
import json
from pathlib import Path
from home_din_summary import inspect,root

def main():
    out=root/'runs/h4a-home-prep'
    buckets={}
    excluded=[]
    for folder in sorted((root/'runs').glob('home-*-din-*')):
        if not (folder/'environment-result.json').is_file():
            excluded.append((folder.name,'擷取未完成，缺少結束環境與有效量測。'))
            continue
        try:
            env=json.loads((folder/'environment-result.json').read_text())
        except (ValueError, UnicodeError):
            excluded.append((folder.name,'環境紀錄無法解碼，原檔保留。'))
            continue
        if not (folder/'result.json').is_file():
            excluded.append((folder.name,'、'.join(env['reasons'])))
            continue
        r=inspect(folder)
        if not r['environment_valid'] or not r['wire_equal']:
            reason='、'.join(env['reasons']) or json.dumps(r['packet_differences'],ensure_ascii=False)
            excluded.append((folder.name,reason+f"；回送極差 {r['current']['rx']['spread']} ms"))
            continue
        buckets.setdefault((r['rate'],r['direction']),r)
    rows=list(buckets.values())
    (out/'physical-matrix.json').write_text(json.dumps(dict(eligible=rows,excluded=excluded),indent=2))
    lines=['# 電腦產生 MTC 經實體 DIN 的候選版重測','',
           'Model 12 韌體 1.50 0103；程式 f13949d9（#1669 + #1663 起音候選 + #1634 I24），48 kHz／256。每組十次，回送極差門檻 3 ms，另核對二十次停止定位與完整 MIDI 封包。選用每組第一筆環境和封包均有效的紀錄。門檻未過的有效量測照樣列入。','',
           '| 格率 | 方向 | 舊回送極差 ms | 新回送極差 ms | 新輸出極差 ms | 新回送首音中位 ms（相對主機標籤） | 中位數相對舊版 ms | 判定 |','|---|---|---:|---:|---:|---:|---:|---|']
    for rate in ['24','25','29.97df','29.97nd','30']:
        for side in ['forward','reverse']:
            if (rate,side) not in buckets:continue
            r=buckets[rate,side]; a,b=r['prior']['rx'],r['current']['rx']
            lines.append(f"| {rate} | {('UM-ONE → Model 12' if side=='forward' else 'Model 12 → UM-ONE')} | {a['spread']:.3f} | {b['spread']:.3f} | {r['current']['tx']['spread']:.3f} | {b['median']:.3f} | {b['median']-a['median']:+.3f} | [{'通過' if r['passed'] else '未通過'}](runs/{r['path']}/result.json) |")
    lines += ['','## 全部嘗試','',f"目前有 {len(rows)}/10 組具有效環境及相符封包，其中 {sum(r['passed'] for r in rows)} 組通過全部原門檻。"]
    for name,reason in excluded:
        lines+=['',f'- [{name}](runs/{name}/)　{reason}']
    lines+=['','已完成組別的原始資料含原生 ASIO 時間戳、輸出與 USB 回送 PCM、收發 MIDI、起音辨識與完整環境。首音中位數是同樣樂譜上的偏差，不能當作按鍵到聲音的單向延遲；不同次實機測量包含輸出及回送路徑的自然變動。','',
            '[逐組回呼直方圖、封包及新舊數字](runs/h4a-home-prep/physical-matrix.json) · [離線診斷](起音與往返複查.zh-TW.md) · [異常封包、USB 回送與系統重開機](H4a-異常與重開機紀錄.zh-TW.md)']
    (root/'H4a-候選版實體DIN.zh-TW.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(len(rows),'eligible;',sum(r['passed'] for r in rows),'passed;',len(excluded),'excluded')
if __name__=='__main__':main()

