from pathlib import Path
import ast,re,subprocess,json
d=Path('E:/soundcraft/compatibility-audit/g11-large-tempo');w=d/'work'
def read(name): return (d/name).read_text(encoding='utf-8-sig')
def put(name,s): (d/name).write_text(s.strip()+'\n',encoding='utf8')
commit=subprocess.check_output(['git','-C',str(w),'rev-parse','HEAD'],text=True).strip()
def steps(file):
 return {(direction,int(pulse)):(int(count),ast.literal_eval(vals)) for direction,pulse,count,vals in re.findall(r'STEP ([\d>\-]+) pulse=(\d+) hits=(\d+) ms=(\[[^\]]+\])',read(file))}
green=steps('ui-published.log');red=steps('published-red.log')
assert len(green)==len(red)==12
def ms(i):return '0' if i==0 else f'{i:+.3f}'
table='| BPM | F8 | N | 變速點、+½、+1、+1½、…、+8 拍（ms） |\n|---|---:|---:|---|\n'
short='| BPM | 位置 | 舊首反拍 | 新首反拍 | 舊第二拍起最大絕對值 | 新第二拍起最大絕對值 |\n|---|---|---:|---:|---:|---:|\n'
for key,(n,li) in green.items():
 direction,i=key;old=red[key][1];assert len(li)==17
 table+=f"| {direction.replace('->','→')} | {i} | {n} | "+' · '.join(map(ms,li))+' |\n'
 short+=f"| {direction.replace('->','→')} | {('小節線' if i==384 else '拍中')} | {ms(old[1])} | {ms(li[1])} | {max(map(abs,old[2:])):.3f} | {max(map(abs,li[2:])):.3f} |\n"
def peak(lists):return max(abs(v) for l in lists for v in l)
a2=peak([ast.literal_eval(s) for s in re.findall(r'rendered_ms=(\[[^\]]+\])',read('scenario_a2_drop-after.log'))])
def steady(file):
 return re.findall(r'steady (\d+) (\d+) BPMp95=([\d.]+) phasep95_us=([\d.]+)',read(file))
st=steady('steady-before.log');assert len(st)==9 and st==steady('verified-mix-playback.log')
stab='| BPM | 輸入抖動 σ（µs） | BPM 誤差 p95 | 相位誤差 p95（µs） |\n|---:|---:|---:|---:|\n'+''.join(f'| {a} | {b} | {c} | {float(e):.0f} |\n' for a,b,c,e in st)
assert re.findall('A1 bars=.*',read('scenario_a1_pitch-before.log'))==re.findall('A1 bars=.*',read('scenario_a1_pitch-after.log'))
link=f'https://github.com/mtlcl410/soundcraft/blob/{commit}/crates/ui-egui/src/app/clock_follow/tests/large_steps.rs'
avid='https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2026.4.pdf#page=845'
full=f'''# #1669 外部 MIDI Clock 大幅變速驗收

Windows 本機。修正前 `49a85d8e`，修正後 `{commit[:8]}`。所有正值表示起音晚於 MIDI 參考，負值表示提早。48 kHz 的一個取樣為 0.02083 ms。使用理想 MIDI 時間戳及渲染 PCM，本輪沒有量測實體 MIDI 或喇叭延遲。

## 原曲重現與修正

沿用 24 小節 EDM 譜，每段八小節，80→130→80 BPM。兩版都是 192 下踩鈸、48 下大鼓、48 下小鼓。在最後一次減速處，變速點、第一個反拍、下一拍依序從 −1.750、**−70.104**、−15.125 ms 變成 **+0.167、0.000、0.000 ms**。最後一段的 64 下踩鈸最大絕對偏差 0.167 ms，最後一音 0.000 ms。三條獨立聲部的末音各有完整 96 個取樣，另驗證結尾一秒無額外起音。原曲探針先保存網格再渲染各聲部；下面的 CI 測試逐次餵入 F8 並立即渲染，尚未到達的 F8 無法改寫已留存的 PCM。[原曲舊版](edm-red.log) · [紅測判定](edm-red-verdict.log) · [原曲新版](scenario_edm_eighty-after.log) · [綠測判定](edm-green-verdict.log)

| 減速後 | 舊版 | 新版 |
|---|---|---|
| 速度確認 | 第 1～3 個間隔仍估 129.987、129.961、129.922 BPM，第 4 個才切 80 BPM（125 ms） | 第 2 個切到 80 BPM（62.5 ms） |
| 可修改網格的前沿 | 30 ms 保護區下，第 1～4 次比線上位置多 2.275、2.900、3.525、4.150 個 pulse | 第 2 次仍有 2.800 個 pulse，到第 6 次為 0.950。回呼另限制可送出的樂譜事件到最新 F8 加一個 pulse |
| 相位接回 | 以 0.35 拍修正，拍長增幅上限 25%。80 BPM 時一拍 750 ms，這代表修正斜率最多可把一拍拉長至 937.5 ms。第 4 次前沿約 4.15 × 31.25 − 30 ≈ 99.7 ms；0.35 拍可消化的差距約 65.6 ms | 在已渲染區之後加入一小段過渡速度，接到新時脈的未來 pulse，再恢復量到的速度。一般抖動沿用原相位濾波及 5% 拍長調整上限 |
| 快速模式 | 第 4～27 次有效，第 28 次關閉，當時前沿仍比線上位置多 1.200 個 pulse | 第 2～25 次有效，第 26 次關閉；第一個反拍已經對齊 |

一般變速採四個一致的間隔，依 BPM 變化達 8% 及噪聲門檻確認。至少 30% 的大幅變速可用兩個高度一致且明顯超過噪聲的間隔確認。已在裝置佇列的音訊維持原狀；限制作用於新的音符、控制器和節拍器。樂器持續以裝置取樣率發聲。壓力測試讓回呼預先跑 30 ms，刻意停送 F8，驗證起播點的音符、後續音符的釋放與完整波形；節拍器亦逐樣本比對延後發出的完整 click。[CI 測試原始碼]({link})

## 六種變速的 PCM

48 kHz，回呼每塊最多 128 samples，逐 F8 更新，網格修改留 30 ms 保護區。第 384 個 pulse 位於小節線，第 396 個位於拍中（第 0 個 pulse 是歌頭）。下表對照同一個 sampler 和可辨識的 96-sample 波形。起音數、逐音波形與最後一秒都檢查。透過前後界線計入 17 個量測點，每列 N 包含變速前的音。第一個變速後反拍要求 ≤10 ms，此後從第二拍起每音 ≤4 ms；變速界線沿用舊測的取樣位置不動。[舊版失敗](published-red.log) · [修正版](ui-published.log)

{short}
{table}
PCM 起音同時滿足每個門檻，個別聲音的樣本序列與該輪參照音完全相同。這項驗收涵蓋合成測試聲音，實體裝置延遲及其他音源的聽感仍應以獨立量測判讀。

## 其他情境與抗抖動

- A-1 連續推速。124 BPM 的 ±8% 緩變，輸入分別加 0、±1、±2 ms 抖動，最大偏差依次為上推 7.729、7.875、7.938 ms，下推 8.979、8.854、9.062 ms。六輪的變速快修誤觸皆為 0。124.0→124.3→124.0 的三輪是 3.104、3.062、3.792 ms，誤觸均為 0。九輪的數字與修正前相同。A-1 原提案的 4 ms 和包含起播估速在內的每次 BPM 變化 ≤0.1 仍未全數通過。[前](scenario_a1_pitch-before.log) · [後](scenario_a1_pitch-after.log)
- A-2 128↔140 BPM。兩種切點、44.1／48／96／192 kHz 共 16 種組合通過，逐音最大絕對偏差 {a2:.3f} ms。[前](scenario_a2_drop-before.log) · [後](scenario_a2_drop-after.log)
- A-3 缺鐘 300 ms 後只恢復 F8。線上逐塊渲染的 Coast 仍為 65/65 音，恢復後第一音 −200 samples、其後最大 185 samples、最後一音 +118 samples（+2.458 ms）。Stop on loss 僅有停前 33 音。[原測](returning_clock_without-before.log) · [修正後線上渲染](ui-published.log)
- 八小時 120 BPM ±0.2 模擬，1,382,400 個 pulse、230,400 次位置查詢、3,841 個 tempo events。前後峰值皆為 148 samples（3.083 ms），查詢 p99 均為 100 ns。這個 profile 每六個 pulse 更新一次網格；下表另測含時間戳量化的輸入估測器。[前](long-before.log) · [後](eight_hours_of_clock_flutter-after.log)
- 穩速測試在 1 ms USB 時間戳量化下比較第 240 個 pulse 起的 460 筆資料。九組 p95 的 BPM 和相位值前後完全一致。[前](steady-before.log) · [後](verified-mix-playback.log)

{stab}
## 重跑與參考

`cargo test -p soundcraft-ui-egui --lib large_steps -- --nocapture` 可重跑 12 組及領先渲染測試。`cargo test -p soundcraft-ui-egui --lib returning_clock_without -- --nocapture` 測 Coast。八小時模擬用 `cargo test -p soundcraft-ui-egui --lib eight_hours_of_clock_flutter -- --ignored --nocapture`。舊曲與 A-1／A-2 原始探針另存於 [本機情境測試](performance_scenarios.rs)。Windows 三個 library 測試合計 742 項通過（mix 102、playback 228、UI 412）；八小時另跑。三個變更 crate 的 Clippy（lib、tests、--no-deps、-D warnings）通過。依賴 engine 的既有 autosave.rs:481 警告照實保留。[播放與混音測試](verified-mix-playback.log) · [UI 測試](ui-published.log) · [Clippy](clippy.log)

Avid《Pro Tools Reference Guide》2026.4 印刷第 743–744 頁，涵蓋送出 MIDI Beat Clock、逐埠 offset 與以錄音量測固定延遲。這次外部跟隨採用的 10／4 ms 是 SoundCraft 的驗收目標。[Avid 手冊，第 743–744 頁]({avid})
'''
put('REPORT.zh-TW.md',full)
put('pr-table.md',table.replace('變速點、+½、+1、+1½、…、+8 拍（ms）','Signed ms at the transition, then every half beat through +8 beats').replace('| F8 | N |','| Pulse | Attacks |').replace(' · ', ', '))
print('rows',len(green),'A2 peak',a2)

