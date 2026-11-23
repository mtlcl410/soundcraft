### Digital loopback to the Model 12 MAIN return

The previous six exact starts averaged 19.47 ms from first Clock to digital loopback and 77.61 ms to MAIN USB. Matching the same crash at each tap accounts for the additional **58.14 ms**. The independent Windows capture callbacks timestamped the monitor copy 1.94 ms earlier than the digital witness. Monitor capture to ASIO output took 45.13 ms, and ASIO output callback to MAIN USB return took 14.95 ms. Inside the 45.13 ms monitor interval, the input and output callbacks containing the attack were 34.41 ms apart on average. Sample positions within those blocks account for the remaining 10.72 ms.

With the same eight-bar S-MU2000 project, executable, 120 BPM physical MIDI loop and 256-frame ASIO driver buffer, twelve new takes alternated monitor prefill settings. Each setting had four exact starts and two late starts. All times below are means from the four exact starts per setting.

| Interval | 40 ms monitor prefill | 20 ms monitor prefill |
|---|---:|---:|
| Monitor capture to ASIO output callback | 48.59 ms | 30.14 ms |
| ASIO output callback to MAIN USB return | 14.50 ms | 14.59 ms |
| Digital loopback to MAIN USB return | 61.15 ms | 43.04 ms |
| First incoming Clock to MAIN USB return | 83.15 ms | 62.49 ms |

Reducing the external monitor prefill saved **18.11 ms** between digital loopback and MAIN. As an independent check, writing the recorded crash straight to ASIO 9/10 and capturing MAIN USB 11/12 gave 14.38–15.61 ms across six repetitions (mean 14.67 ms). This last interval includes the driver, device and USB recording return. The measurement uses the driver's ADC timestamp and cannot distinguish their one-way contributions. SoundCraft had already rendered the signal at the digital tap. Its prior instrumented six takes averaged 6.05 ms to receive the playback command in the audio callback and another 4.62 ms to finish the first mix block. Those are separate runs and include scheduling.

The digital, monitor-input, ASIO-output and MAIN recordings each contained one crash in all eight 8.000 s takes and zero in all four 8.125 s takes. Later accompaniment matched on both digital and MAIN in all twelve (correlation above 0.99). Every take captured SPP, Continue, 144 clocks and Stop. The monitor logged zero short callbacks, overflow trims or ASIO status flags during the measured playback windows. Both the boundary-note and first-Clock dispatch regressions passed again. The product code and its default audio settings are unchanged in this measurement update.

![Measured MIDI Clock to audio taps and the effect of monitor prefill](IMAGE_URL)
