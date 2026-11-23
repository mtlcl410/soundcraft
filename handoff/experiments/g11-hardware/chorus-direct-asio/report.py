import hashlib,json,statistics as st,re,shutil
from pathlib import Path
d=Path(__file__).resolve().parent
w=d.parent.parent/'g11-clock-follow'
def get(p):return json.loads(p.read_bytes())
old=get(d.parent/'chorus-main-return-split'/'per-take.json')
old={k:v for k,v in old.items() if k.startswith('queue20')}
new=get(d/'per-take.json');route=get(d/'route.json');ctl=get(d/'control.json')
assert ctl['project_sha256']==get(d.parent/'chorus-main-return-split'/'control.json')['project_sha256']
assert route['routing']['outputs'][0]['first_channel']==8 and route['audio']['device']['channels']==10
for g,key in [(old,'main_count'),(new,'crash_count')]:
 assert len(g)==6 and sum(v['spp']==64 for v in g.values())==4
 assert all(v[key]==int(v['spp']==64) for v in g.values())
a=[v['main_ms'] for v in old.values() if v['spp']==64];b=[v['first_clock_to_main_ms'] for v in new.values() if v['spp']==64]
assert all(abs(v['adc_adjustment_ms']+6.803)<.002 for v in new.values())
def part(vals):return f'{st.mean(vals):.2f} ms ({min(vals):.2f}–{max(vals):.2f})'
delta=st.mean(a)-st.mean(b); corr=min(v['later_correlation'] for v in new.values()); slots=', '.join(f'{x:.2f}' for x in b)
fig='midi-clock-direct-asio.png'
title='Direct hardware playback from the external Clock'
english=f"""### {title}

SoundCraft sent the same 48 kHz eight-bar S-MU2000 project directly through Model Mixer ASIO to physical outputs 9/10 (44.1 kHz, 256 frames). The local Windows build combined the Clock follower at `2b53c7e` with the Model 12 sample-format support in #1634 and hardware routing at #1635 (`7e922669`). These routing prerequisites apply to this hardware test. The original project was copied byte-for-byte and its stereo output was mapped to channels 9/10 in memory.

| First Clock at UM-ONE to crash onset on MAIN USB 11/12 | Mean (range), four 8.000 s starts |
|---|---:|
| Previous 20 ms monitor prefill | {part(a)} |
| Direct SoundCraft ASIO output | **{part(b)}** |

The direct takes measured {slots} ms. Direct playback averaged **{delta:.2f} ms faster** on this setup. Both runs used the same 120 BPM physical MIDI path (Model 12 DIN OUT to UM-ONE), four exact starts, two 8.125 s starts, the same waveform threshold (0.90), and the same driver input-time adjustment (6.80 ms). The previous run recorded through the external monitor process. The driver rejected a second independent ASIO client during direct playback, so a local input-only diagnostic copied MAIN 11/12 samples from SoundCraft’s native duplex stream to a background writer. The diagnostic did not forward audio or alter playback scheduling. Results describe the recorded MAIN return across separate runs.

Direct MAIN contained exactly one crash in **4/4** exact starts and zero in **2/2** late starts. Later accompaniment was present in all six (minimum correlation {corr:.3f}). Each take captured its specified Song Position, Continue, 144 Clock pulses and Stop. The input-block sequence was continuous in every take.

![Direct ASIO and 20 ms monitor route measured on the same chorus](IMAGE_URL)"""
zh=f"""### SoundCraft 直接從 Model 12 ASIO 9/10 播放

使用同一份 48 kHz 八小節 S-MU2000 伴奏的原檔副本，在記憶體將主立體聲路徑起始通道設為 8（實體 9/10）。使用 Model Mixer ASIO、44.1 kHz、每區塊 256 個取樣。實體 MIDI 迴路為 Model 12 USB MIDI → DIN OUT → UM-ONE；每次 120 BPM、SPP、Continue、144 個 Clock、Stop。執行檔為 #1669 的 `2b53c7e` 與含 #1634 的 #1635 `7e922669` 本機整合版，加上僅供量測的 MAIN 輸入樣本擷取。原專案 SHA-256 為 `{ctl['project_sha256']}`。[路由與實際開啟的裝置](chorus-direct-asio/route.json) · [執行檔與伴奏識別](chorus-direct-asio/control.json)

| UM-ONE 首個 Clock 到 Model 12 MAIN USB 銅鈸起音 | 平均與範圍，四次 8.000 秒起播 |
|---|---:|
| 上一輪外部監聽轉送，20 ms 預填 | {part(a)} |
| SoundCraft 直接 ASIO 9/10 | **{part(b)}** |

直接輸出的四次逐筆為 {slots} ms，平均比前輪縮短 **{delta:.2f} ms**。精確起播四次在 MAIN 各收到一次銅鈸；從 8.125 秒起播的兩次均沒有補播。六次都有後續伴奏（與前輪參考波形比對最低 {corr:.3f}），停止後還繼續擷取約 1.5 秒，整段一併計算起音數。

兩輪都以獨立 UM-ONE 接收第一個 Clock 的主機時間為零點，以 MAIN USB 11/12 相同銅鈸模板及 0.90 相關門檻判定起音，逐區塊校正驅動回報的 6.80 ms 輸入延遲。本輪驅動拒絕第二個程式同時開啟 ASIO 輸入，因此從 SoundCraft 自己的雙向串流擷取 MAIN，樣本交給背景執行緒存檔，整段區塊序號連續。輸出仍由產品原有 ASIO 路徑直接送到 9/10。比較值來自前後兩批錄音，包含 MIDI 接收觀測與音訊回呼取樣時機，未量喇叭的聲學延遲。

![直接 ASIO 與 20 毫秒監聽預填的逐次實測](chorus-direct-asio/{fig})

[本輪逐次結果](chorus-direct-asio/per-take.json) · [前輪數據](chorus-main-return-split/per-take.json) · [首音 WAV](chorus-direct-asio/exact-a.wav) · [晚起播 WAV](chorus-direct-asio/late-a.wav) · [實體接收與時間戳](chorus-direct-asio/exact-a.json) · [重算腳本](chorus-direct-asio/analyze.py) · [PR #1669](https://github.com/storytold/soundcraft/pull/1669)
"""
(d/'section.en.md').write_text(english,encoding='utf8');rep=d.parent/'ROUND4-ACCEPTANCE.zh-TW.md'
assert zh.splitlines()[0] not in rep.read_text(encoding='utf8')
for link in re.findall(r'\]\(([^)]+)\)',zh):
 if not link.startswith('https://'):assert (rep.parent/link).is_file(),link
with rep.open('ab') as file:file.write(('\n'+zh+'\n').encode('utf8'))
shutil.copyfile(d/fig,w/'docs/images'/fig)
attr=w/'ATTRIBUTION.md';s=attr.read_bytes();assert fig.encode() not in s
with attr.open('ab') as file:file.write(f'| `docs/images/{fig}` | SoundCraft contributors | original comparison of direct ASIO and monitored playback on the Model 12 MAIN return | MIT OR Apache-2.0 |'.encode()+ (b'\r\n' if s.endswith(b'\r\n') else b'\n'))
print(part(a),part(b),delta,corr)

