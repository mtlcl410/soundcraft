from pathlib import Path
import json,sys
here=Path(__file__).resolve().parent
label='stop-ordinal-'+sys.argv[1]+'-two-hours'
f=here/label
v=json.loads((f/'stop-verdict.json').read_text())
old=json.loads((here/'reboot-0823-two-hours/result.json').read_text())
assert v['valid']['environment_valid'],v['valid']
origin,host,audio,begin,end,fc,done=v['native_stops'][-1]
asio=v['asio']
limits=asio['histogram']
within=limits['[200, 300)']
target=345600
strict='通過' if v['strict_exit']==0 else '未通過'
link='overnight-evidence/'+label
lines=[
f"本輪於 {v['completed']} 完成分析。環境檢查通過。來源／實體輸入／轉送後輸入依序為 {v['source']:,}／{v['physical_input']:,}／{v['captured_input']:,}。實體輸出 F8 為 {v['output']:,}，與輸入相差 {v['output']-v['captured_input']:+,}；前次為 {old['received_clock']:,}／{old['expected_clock']:,}。失鎖 {v['dropouts']} 次，輸出 FC 後另收 {v['sends_after_output_stop']} 個 F8。",
f"最後一次 F8 送出呼叫的起迄相對輸入 FC 為 {(begin-origin)/1e6:+.3f}、{(end-origin)/1e6:+.3f} ms。探針記錄了 {len(v['suppressions'])} 次超界攔截。",
f"ASIO 平均 {asio['mean_ms']:.3f} ms，p99 {asio['p99_ms']:.3f} ms，最大 {asio['max_ms']:.3f} ms；200–300 ms 區間 {within} 次。取樣位置及回呼序號不連續各 {asio['position_discontinuities']}／{asio['serial_discontinuities']} 次。",
f"原嚴格 H-10 驗收{strict}。實收 MTC quarter-frame {v['qf']:,}，外部計時原門檻 864,000；片段編號不連續 {v['qf_piece_discontinuities']} 次。此數分開列出。"
]
p=here.parent/'H10-時鐘速差與起停邊界.zh-TW.md'
assert 'stop-verdict.json)' not in p.read_text(encoding='utf-8-sig')
with p.open('a',encoding='utf-8') as out:
    out.write('\n'+'\n\n'.join(lines)+f' [本輪原始量測摘要]({link}/stop-verdict.json) · [回呼分布]({link}/asio-callback-histogram.json) · [嚴格計數測試](overnight-evidence/{label}-strict.log)\n')
print('\n'.join(lines))

