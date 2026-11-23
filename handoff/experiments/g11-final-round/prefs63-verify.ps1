$ErrorActionPreference='Stop'
$env:PYTHONUTF8='1'
$env:RUSTUP_HOME='E:/soundcraft/tools/rustup'
$env:CARGO_TARGET_DIR='E:/soundcraft/compatibility-audit/g11-verify-mtc-target'
$red=Get-Content -Raw ../evidence/f63-prefs-red.log
if ($red -notmatch 'mtc_bad_workstation_fields_recover_independently.*FAILED' -or $red -notmatch 'mtc_bad_project_fields_load_with_individual_resets.*FAILED') {throw 'No behavioral red'}
python ../prefs63green.py
if ($LASTEXITCODE) {exit $LASTEXITCODE}
python ../prefs63configgreen.py
if ($LASTEXITCODE) {exit $LASTEXITCODE}
& E:/soundcraft/tools/cargo/bin/rustfmt.exe --edition 2024 --config skip_children=true apps/soundcraft/src/config.rs crates/engine/src/lib.rs crates/engine/src/cmd/options.rs
if ($LASTEXITCODE) { exit $LASTEXITCODE }
& E:/soundcraft/compatibility-audit/g11-a10-recovery/run.cmd test -j 3 --locked -p soundcraft -p soundcraft-engine --lib --bins --no-fail-fast mtc_bad_ *> '../evidence/f63-prefs-green.log'
exit $LASTEXITCODE
