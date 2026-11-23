from pathlib import Path
import subprocess,json,os
d=Path('E:/soundcraft/compatibility-audit/g11-large-tempo');h='af4af80b626bab785de97ba895f76187b76da99d';gh='E:/soundcraft/tools/gh/bin/gh.exe';os.environ['GH_CONFIG_DIR']='E:/soundcraft/tools/gh-config'
def pr():return json.loads(subprocess.check_output([gh,'pr','view','1669','-R','storytold/soundcraft','--json','headRefOid,isDraft,body'],encoding='utf8'))
rec=pr();assert rec['headRefOid']==h and rec['isDraft']
b=rec['body'];old='- Should the proposed ramp and deck-change targets be accepted? The ±8% sweep peaked at 9.062 ms; the 130→80 section of a complete EDM song peaked at 70.104 ms.'
assert b.count(old)==1
table=(d/'pr-table.md').read_text(encoding='utf8').strip()
src=f'https://github.com/mtlcl410/soundcraft/blob/{h}/crates/ui-egui/src/app/clock_follow/tests/large_steps.rs'
new=f"""- Does this external tempo-follow response meet live performance needs? In the six abrupt changes below, the first offbeat deviated by at most one sample (0.021 ms), and every eighth from the second beat onward by at most three samples (0.0625 ms at 48 kHz). The continuous ±8% ramp still peaks at 9.062 ms; its proposed 4 ms target remains open. The 124.0→124.3→124.0 drift triggered fast correction zero times with 0, ±1 and ±2 ms timestamp jitter."""
b=b.replace(old,new)
sec=f"""### External Clock tempo steps ({h[:8]})

On the same 24-bar 80→130→80 BPM score, the first offbeat at the slowdown moved from **70.104 ms early to 0.000 ms**. The maximum absolute error across that final section fell to **0.167 ms**. All 192 hats, 48 kicks and 48 snares sounded with complete final bursts. The existing 12-bar hardware results below remain measurements of an earlier revision.

The sequencer releases events through the last received F8 plus one pulse. At a confirmed tempo change it joins the new pulse grid after committed audio. Sustained changes of at least 8% qualify; large, coherent steps of at least 30% can qualify in two intervals. The normal jitter filter and the running audio sample rate are preserved.

On Windows, the previous head `49a85d8e` failed both the online PCM matrix and the render-ahead test. The replacement for `chorus_tempo_step_keeps_the_next_backbeat_within_one_clock` checks every eighth, the unchanged boundary, onset count, per-sample waveform and final silence. The 128↔140 BPM controls passed at four sample rates (peak 0.042 ms). Coast relocked after 300 ms on F8 alone, with 65/65 hits and the last +2.458 ms. The eight-hour flutter peak stayed at 148 samples and all nine steady-tempo BPM/phase p95 pairs matched the baseline. Local library tests passed (102 mix, 228 playback, 412 UI), plus the explicit eight-hour profile and Clippy for those three crates. [PCM regression and reproduction code]({src})

<details>
<summary>Signed PCM onset deviations for the first eight beats</summary>

48 kHz, ideal input, at most 128 samples per render, with a 30 ms guard for grid edits. F8 at index 384 is a bar line; index 396 is halfway through a beat. Negative means early and positive means late. Counts include the lead-in. Tolerances are 10 ms for the first offbeat and 4 ms from the second beat. These values measure software rendering; loudspeaker and USB latency require a separate capture.

{table}

</details>

Avid documents transmitting Beat Clock, per-port playback offsets, and measuring the recorded response. SoundCraft's external-follow thresholds above are project acceptance criteria. [Pro Tools Reference Guide 2026.4, printed pp. 743–744](https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2026.4.pdf#page=845)

"""
# Before the historical hardware measurements, after their preceding paragraph.
key='**Three-section dance track.**';assert b.count(key)==1
b=b.replace(key,sec+'**Earlier three-section hardware run (6b82d9b).**')
# Preserve the rest of the description, including the existing questions and merge order.
payload=d/'pr-update.json';payload.write_text(json.dumps({'body':b},ensure_ascii=False),encoding='utf8')
subprocess.run([gh,'api','--method','PATCH','repos/storytold/soundcraft/pulls/1669','--input',str(payload),'--jq','.html_url'],check=True)
now=pr()
assert now['headRefOid']==h and now['isDraft'] and new in now['body'] and table in now['body'] and now['body'].count('<!-- g11-scenario-audit-20261122 -->')==1
(d/'pr-after.json').write_text(json.dumps(now,ensure_ascii=False),encoding='utf8')
p=d.parent/'g11-scenarios-20261122/REPORT.zh-TW.md';s=p.read_text(encoding='utf8');key='## A-3 修正後複驗'
addition=f"""## 第三項大幅變速複驗

[#1669 的修正 `{h[:8]}`](https://github.com/storytold/soundcraft/pull/1669/commits/{h}) 已保留為草稿。原曲第一個減速反拍從**早 70.104 ms 改為 0.000 ms**，該段最大絕對偏差 0.167 ms。六種變速各測小節線與拍中，第一個反拍最大 1 sample，第二拍起最大 3 samples。向前、向後連續推速和穩速結果與舊版相同；A-1 連續 ±8% 的 4 ms 提議仍未達成。以下歷史資料保留原提交結果。[逐音數字、舊版失敗及抗抖動對照](../g11-large-tempo/REPORT.zh-TW.md)

"""
assert key in s and '## 第三項大幅變速複驗' not in s
p.write_text(s.replace(key,addition+key).replace('降速後仍會晚 70.104 ms','當時降速後第一個反拍早 70.104 ms'),encoding='utf8')
p=d/'REPORT.zh-TW.md';s=p.read_text(encoding='utf8').replace('](clippy.log)','](published-clippy.log)').replace('PCM 起音同時滿足每個門檻','全表的首反拍最大絕對偏差為 1 個取樣（0.02083 ms），第二拍起為 3 個取樣（0.0625 ms）。表內毫秒值取到小數第 3 位。PCM 起音同時滿足每個門檻')
p.write_text(s,encoding='utf8')
print('Verified draft, commit, twelve matrix rows, Open questions and both local reports.')

