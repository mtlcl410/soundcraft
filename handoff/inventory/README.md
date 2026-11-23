# Worktree inventory

[Pre-handoff files, branches, local log and stash](BEFORE.json) · [Post-handoff status](AFTER.json) · [Locally recorded commits outside the original remote branches](LOCAL_ONLY_CANDIDATES.json) · [Recoverable G-11 snapshot IDs](G11_REFS.json)

| Git directory | Worktrees | Branches at inventory | Dirty before | Changed paths | Stashes |
|---|---:|---:|---:|---:|---:|
| E:/soundcraft/source/.git | 26 | 2 | 13 | 44 | 0 |
| E:/soundcraft/compatibility-audit/counter-overflow-20261118/pr641/.git | 1 | 1 | 1 | 1 | 0 |
| E:/soundcraft/compatibility-audit/dexed-vital-20261117-195606/dexed-source/.git | 1 | 0 | 0 | 0 | 0 |
| E:/soundcraft/compatibility-audit/dexed-vital-20261117-195606/vital-source/.git | 1 | 1 | 1 | 2 | 0 |
| E:/soundcraft/compatibility-audit/midi-track-routing/craft-libs/.git | 11 | 12 | 0 | 0 | 0 |
| E:/soundcraft/compatibility-audit/midi-track-routing/soundcraft/.git | 2 | 4 | 1 | 13 | 0 |
| E:/soundcraft/compatibility-audit/minilab-live-20261117-213002/checkout/.git | 1 | 3 | 1 | 22 | 0 |
| E:/soundcraft/compatibility-audit/minilab-live-20261117-213002/controller-channel-fix/.git | 1 | 1 | 0 | 0 | 0 |
| E:/soundcraft/compatibility-audit/minilab-live-20261117-213002/controller-fix/.git | 1 | 1 | 0 | 0 | 0 |
| E:/soundcraft/compatibility-audit/minilab-live-20261117-213002/hotplug-fix/.git | 1 | 1 | 0 | 0 | 0 |
| E:/soundcraft/compatibility-audit/minilab-live-20261117-213002/hotplug-validation/.git | 1 | 1 | 1 | 3 | 0 |
| E:/soundcraft/compatibility-audit/minilab-live-20261117-213002/monitor1601-validation/.git | 1 | 1 | 1 | 2 | 0 |
| E:/soundcraft/compatibility-audit/minilab-live-20261117-213002/pr1085/.git | 1 | 1 | 1 | 1 | 0 |
| E:/soundcraft/compatibility-audit/minilab-live-20261117-213002/pr493/.git | 1 | 1 | 1 | 1 | 0 |
| E:/soundcraft/compatibility-audit/minilab-live-20261117-213002/pr531/.git | 1 | 1 | 1 | 1 | 0 |
| E:/soundcraft/compatibility-audit/other-vst3-20261117-184658/probe-source/.git | 1 | 1 | 0 | 0 | 0 |
| E:/soundcraft/compatibility-audit/pr-verification-20261117-182245/checkout/.git | 1 | 1 | 0 | 0 | 0 |
| E:/soundcraft/compatibility-audit/smu-fixes-20261117-203648/checkout/.git | 1 | 2 | 0 | 0 | 0 |
| E:/soundcraft/compatibility-audit/smu-fixes-20261117-203648/combined-checkout/.git | 1 | 2 | 1 | 15 | 0 |
| E:/soundcraft/compatibility-audit/smu-fixes-20261117-203648/program-checkout/.git | 1 | 2 | 0 | 0 | 0 |
| E:/soundcraft/compatibility-audit/surge-pr1566/checkout/.git | 1 | 0 | 0 | 0 | 0 |
| E:/soundcraft/compatibility-audit/sysex-20261118/craft-libs/.git | 1 | 2 | 0 | 0 | 0 |
| E:/soundcraft/compatibility-audit/sysex-20261118/soundcraft/.git | 3 | 2 | 0 | 0 | 0 |
| E:/soundcraft/compatibility-audit/xg-sysex-playback/soundcraft/.git | 172 | 71 | 64 | 334 | 1 |
| E:/soundcraft/compatibility-audit/smu-arrangement/midnam-validation/upstream/.git | 2 | 2 | 1 | 8 | 0 |

Scope: project checkouts and their registered worktrees under E:/soundcraft. Package-manager dependency caches and the temporary bare verification repo are outside the project count. The primary branch-list sample includes the initially allocated WIP handoff ref. Other projects were inventoried only. Their original working contents, stash entries and branch tips were checked again after archiving.
