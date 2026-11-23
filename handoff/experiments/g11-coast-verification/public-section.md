## Coast recovery when the external clock returns

In `COMMIT_SHA`, a rolling Coast transport relocks when returning F8 pulses establish a valid tempo. It estimates the nearest musical pulse from the previous clock and corrects the writable grid without restarting playback or seeking in an open take. A lone tick does not establish a new tempo. Stop on loss remains stopped until the source sends Start or Continue followed by Clock. F8 alone carries no absolute song position.

| Same 48 kHz rendered eighth-note backing, 120 → 128 BPM, source returns at 8.300 s | Before | After |
|---|---|---|
| Coast | 65/65 attacks; still Coasting; last attack +473.438 ms | Locked at 128.000 BPM; 65/65 distinct attacks, no transport restart; last attack +2.458 ms (118 samples) |
| Stop on loss | Stopped at sample 390,563; 33 attacks | Same stop sample and 33 attacks; F8 alone did not restart playback |

Ownership checked against upstream main `85623f28`: that revision has no external Beat Clock follow command or reader. Re-ran the original A-3 reproducer on the old and corrected code. The committed PCM regression counts the full rendered attacks, pairs each with its own grid position, and checks both loss policies. This is a software measurement using the production mixer and sampler.

The first hat after F8 returned was 200 samples early (4.167 ms); all subsequent attacks were within 185 samples (3.854 ms). Across both affected crates, 942 tests passed and five were ignored. Workspace format and all-targets Clippy passed. An additional Windows run with all warnings promoted to errors stops at the existing unused `mut` in `crates/engine/src/autosave.rs:481`; that file is byte-identical on main, the previous PR head, and this commit.
