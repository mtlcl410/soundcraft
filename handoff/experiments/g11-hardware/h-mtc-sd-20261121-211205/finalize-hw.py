from pathlib import Path
import json,re,sys,subprocess
d=Path.cwd()
run=d.name
load=lambda name:json.loads((d/name).read_text(encoding="utf-8-sig"))
takes=["take1","take2r","take3r"]
audio=[load(t+"-audio.json") for t in takes]
mtc=[load(t+"-mtc.json") for t in takes]
assert [a["anchor"]["signed_offset_ms"] for a in audio]==[13.5,51.5,55.5]
assert all(m["rpc_errors"]==m["rate_mismatch_polls"]==m["session_record_true"]==0 for m in mtc)
assert mtc[-1]["largest_qf_gap_ms"]==1758.29
file=d.parent/"ROUND4-ACCEPTANCE.zh-TW.md"
raw=file.read_bytes()
old=raw.decode("utf-8").replace("\r\n","\n")
a=old.index("## #1663 的 H-MTC-SD")
b=old.index("## #1663 的本體連續播放",a)
plan=old[old.index("1. **先驗發碼",a):old.index("| Take |",a)].rstrip()
new="""## #1663 的 H-MTC-SD：本體錄 SD 並發送 MTC

**2026-11-21 實測完成。** Model 12 錄 SD 時會從 DIN 發送 MTC。SoundCraft 三輪都鎖定、播放伴奏並跟停。三輪的伴奏起音偏差極差為 **42.0 ms**，未達「跨次偏差固定」的驗收條件。

Model 12 韌體為 1.30 0088，歌曲為 48 kHz／24-bit，MIDI TIMECODE 開啟、MIDI CLOCK/SPP 關閉。背面 DIN OUT 經 Roland UM‑ONE 進入 SoundCraft。CH1 以 LIVE 錄麥克風，CH2 以 PC 錄 S‑MU2000 的 USB 回送，兩軌分開寫入同一首 SD 歌曲。SoundCraft 執行版為 #1663 的 `ee80920`，專案以 30 fps non-drop、零起始時碼和零外部偏移跟播，Online 開啟、Gen MTC 關閉、Freewheel 設 Frames 8。[執行檔與專案雜湊](DIR/control.json) · [設定讀回](DIR/reader-arm.json)

PLAN

| SD 歌曲 | 起錄位置 | 實錄時長 | DIN quarter-frame 筆數 | SoundCraft 跟停位置 | CH2 的 A4 起音 | 相對 5.000 秒 |
|---|---|---:|---:|---|---:|---:|
| [040208_0004](DIR/take1-sd.json) | 歌頭 | 69.552 s | 8,344 | 00:01:09:16 | 5.0135 s | +13.5 ms |
| [040208_0007](DIR/take2r-sd.json) | 00:00:02:00 | 65.680 s | 7,880 | 00:01:07:20 | 5.0515 s | +51.5 ms |
| [040208_0009](DIR/take3r-sd.json) | 歌頭，中途拔 DIN | 65.640 s | 7,662 | 00:01:05:19 | 5.0555 s | +55.5 ms |

三輪走帶輪詢的錄音旗標均為 false，查詢錯誤與幀率警告均為零。SD 原檔與本機副本已逐檔核對 SHA-256。0007 的起錄位置經 Reader 確認為 96,000 samples；其 WAV 含歌頭至第 2 秒的留白，全長 67.680 秒，表中起音均以歌曲時間計算。先前的 0005、0006 只有 MAIN 有資料，CH1、CH2 WAV 為空，故未納入起音統計。[歌頭走帶](DIR/take1-mtc.json) · [非零起點走帶](DIR/take2r-mtc.json) · [拔線走帶](DIR/take3r-mtc.json)

**起音與錄音品質。** CH2 三輪都辨識到 440.92 Hz 的 A4。以 1 ms RMS 視窗量得極差 42.0 ms，再以同一段 75 ms 鋼琴起音波形交叉比對，極差為 41.75 ms。兩種方法都顯示跨次起音會變動。目前量到的是整條回送路徑，無法單獨歸因於 MTC、音訊驅動或 Model 12。CH1 前兩輪麥克風峰值為 −38.42、−37.05 dBFS；第三輪檔案完整，但峰值僅 −89.08 dBFS，無法確認該輪口述清晰度。[第一輪音訊](DIR/take1-audio.json) · [第二輪音訊](DIR/take2r-audio.json) · [第三輪音訊](DIR/take3r-audio.json) · [波形交叉比對](DIR/anchor-crosscheck.json)

**拔線與重聽。** 0009 在第一筆 quarter-frame 後 10.9496 秒失去 DIN 訊號，12.7079 秒收到下一筆，空檔 1.758 秒。最後一筆有效碼後 268.19 ms 的輪詢仍在 8/8，335.05 ms 時已停在同一游標；接回後 310.76 ms 的輪詢已鎖定並播放。輪詢間隔中位數 67.17 ms。CH2 第 11 秒的音仍在，第 12 秒預期起音後的 350 ms 為靜音，第 13 秒已恢復。操作者重聽正常與拔線片段後回報「只聽到停頓，沒聽到額外異音」。這項聽感適用於本次錄音的接回處。[波形比較](DIR/take3r-gap-audio-comparison.json) · [正常片段](DIR/take1-relock-listen.wav) · [拔線片段](DIR/take3r-relock-listen.wav) · [#1663](https://github.com/storytold/soundcraft/pull/1663)

""".replace("DIR",run).replace("PLAN",plan)
assert all((file.parent/link).is_file() for link in re.findall(r"\]\(([^)]+)\)",new) if not link.startswith("https:"))
out=(old[:a]+new+old[b:]).encode("utf-8")
file.write_bytes(out.replace(b"\n",b"\r\n") if b"\r\n" in raw else out)
sys.path.insert(0,r"E:/soundcraft/tmp/1669-coderabbit-final")
from check import api,env,gh
ref="repos/storytold/soundcraft/pulls/1663"
p=api(ref)
body=p["body"]
start="<!-- H-MTC-SD-results -->"
end="<!-- end-H-MTC-SD-results -->"
before,rest=body.split(start)
_,after=rest.split(end)
before,n=re.subn(r"(?m)^- \[ \] \*\*H-MTC-SD\*\*[^\n]+This combination is pending\.", "- [ ] **H-MTC-SD tested; onset repeatability criterion unmet.** The Model 12 recorded to SD while sending MTC. See the three measured takes below.",before)
assert n==1
msg="""**Model 12 SD recording with MTC chase (November 21, build `ee80920`).** On firmware 1.30 0088, the Model 12 recorded CH1 (live mic) and CH2 (S‑MU2000 piano returned over USB) to a 48 kHz / 24-bit SD song. MIDI TIMECODE was on and MIDI CLOCK/SPP was off. The rear DIN output fed the SoundCraft reader via UM‑ONE at 30 fps non-drop, with zero session start and offset, Online enabled, Gen MTC off and Freewheel set to eight frames. All three takes locked, played the backing and followed stop. No transport poll showed SoundCraft recording, an RPC error or a frame-rate mismatch.

| SD take | Start | Recorded | DIN quarter frames | CH2 onset of the scheduled 5.000 s A4 |
|---|---|---:|---:|---:|
| 040208_0004 | Song start | 69.552 s | 8,344 | 5.0135 s (+13.5 ms) |
| 040208_0007 | 2.000 s | 65.680 s | 7,880 | 5.0515 s (+51.5 ms) |
| 040208_0009 | Song start, DIN interrupted during recording | 65.640 s | 7,662 | 5.0555 s (+55.5 ms) |

The onset offset varied by **42.0 ms** across takes using 1 ms RMS windows. Matching the same piano attack independently gave a 41.75 ms spread. The end-to-end measurement does not isolate the source. Both SD tracks were populated in all three takes. The third take’s microphone peaked at −89.08 dBFS, too quiet to verify speech.

During the 1.758 s DIN interruption, the reader reached 8/8 frames and stopped. The first locked-and-playing poll was 311 ms after timecode returned. The SD backing contains the note at 11 s, silence at the expected 12 s attack and the note at 13 s. On replay against the uninterrupted take, the listener heard the pause and no additional click, repeated note or skip on recovery."""
updated=before+start+"\n"+msg+"\n"+end+after
assert api(ref)["body"]==body
subprocess.run([gh,"api","-X","PATCH",ref,"--input","-"],env=env,input=json.dumps({"body":updated}).encode(),stdout=subprocess.DEVNULL,check=True)
v=api(ref)
assert v["body"]==updated and v["draft"]==p["draft"] and v["head"]["sha"]==p["head"]["sha"]
(d/"pr-hw-summary.md").write_text(msg+"\n",encoding="utf-8")
print("verified",v["html_url"],v["head"]["sha"],file)
