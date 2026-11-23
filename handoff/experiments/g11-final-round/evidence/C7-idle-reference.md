# C-7 strict idle reference

This is a matched repeat of the original software benchmark on the same 12-logical-CPU Windows workstation. It runs 150 simultaneous mono audio tracks at 48 kHz, with 0, 2, or 6 compressor inserts per track. The harness times 1,500 blocks of 128 samples under generated 25 fps MTC. Its 2.667 ms deadline covers rendering, PCM peak reading, MTC host service, and transport handling.

The executable SHA-256 is `44e4d95862b485d92c7ed577abfda34be1e91384d495ec159a1ea28ebb24ebf8`. Each accepted run was observed through a native Windows process snapshot. No compiler, Cargo task or other SoundCraft test process appeared in the eight-second pre-run and post-run windows or during the run. Each accepted run also showed no more than 12.5% total CPU in the preceding eight seconds.

| Inserts per track | Original misses | Current misses | Original p95 | Current p95 | Current median | Current max | MTC quarter frames | Acquired / losses | PCM peak |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| 0 | 175/1500 | 0/1500 | 270.1% | 20.5% | 13.0% | 54.8% | 454 | true / 0 | 0.053095993 |
| 2 | 274/1500 | 0/1500 | 252.7% | 21.6% | 17.4% | 88.7% | 456 | true / 0 | 0.053095993 |
| 6 | 51/1500 | 1/1500 | 74.5% | 33.6% | 27.6% | 143.5% | 443 | true / 0 | 0.053095993 |

Median, p95 and max are percentages of the block budget. Host CPU below is a percentage of the workstation. Background-process CPU is shown as a percentage of one logical core.

| Inserts | CPU 8 s before | CPU during | CPU 8 s after | Leading background processes before | Leading background processes after | Raw output |
|---:|---:|---:|---:|---|---|---|
| 0 | 7.9% | 18.6% | 10.6% | chatgpt.exe 15.4%, remoting_network.exe 8.0%, taskmgr.exe 8.0% | chatgpt.exe 49.0%, remoting_network.exe 10.0%, taskmgr.exe 7.2% | [c7-idle-native-0-0.log](c7-idle-native-0-0.log) |
| 2 | 5.6% | 14.5% | 4.4% | msedgewebview2.exe 18.8%, taskmgr.exe 7.0%, wmiprvse.exe 4.3% | taskmgr.exe 8.2%, dwm.exe 6.1%, remoting_desktop.exe 4.7% | [c7-idle-native-2-1.log](c7-idle-native-2-1.log) |
| 6 | 7.1% | 25.5% | 5.0% | taskmgr.exe 7.8%, memory compression 7.4%, remoting_desktop.exe 6.8% | taskmgr.exe 8.0%, svchost.exe 4.7%, wmiprvse.exe 4.7% | [c7-idle-native-6-2.log](c7-idle-native-6-2.log) |

At least one software block missed its deadline. Investigate mixer and host service timing separately from the G-11 transports.

[Final-round local acceptance report](../STATUS.zh-TW.md) · [Desktop-load control](C7-desktop-reference.md) · [Strict idle result](C7-idle-reference.md)

The external ASIO callback, physical MIDI cables and Model 12 main output lie outside this benchmark. A missed software deadline warrants a separate mixer/host timing investigation, including timing the render and host service individually. An audible dropout cannot be inferred from this result.

Run once with each of 0, 2 and 6 as `SCENARIO_C7_INSERTS`.

```text
load-bench.exe scenario_c7_chase --ignored --nocapture --test-threads=1
```

[Original simultaneous-build log](../../g11-scenarios-20261122/c7-final.log) · [Workload monitoring, including rejected runs](c7-idle-comparison.json)
