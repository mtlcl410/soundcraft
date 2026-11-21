"""Run the same issue #1674 note-on probe in a disposable, clean checkout."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(sys.argv[1]).resolve()
    fixture = Path(__file__).with_name("probe.rs").read_bytes()
    revision = subprocess.check_output(["git", "-C", root, "rev-parse", "HEAD"], text=True).strip()
    has_clock = {
        "85623f28f99a9a788123f0f6b48829f95f07962f": False,
        "2aa39ffc241a98a74bf7a2db52403c7f429d6b0e": True,
        "717f96953313c385ee2acf24a1b0aedeb7672585": True,
    }[revision]
    paths = ["crates/ui-egui/src/app.rs", "crates/playback/src/lib.rs", "crates/mix/src/lib.rs", "crates/mix/src/midi.rs"]
    if subprocess.check_output(["git", "-C", root, "status", "--porcelain", "--", *paths]):
        sys.exit("Run in a clean checkout; the probe temporarily instruments four source files.")
    app, playback, mix, midi = [root / path for path in paths]
    original = {p: p.read_bytes() for p in (app, playback, mix, midi)}
    modified = dict(original)
    for path, needle, insertion in [
        (playback, b"        match open_device(want, want_ch, cfg) {", b"""        if std::env::var_os("ISSUE_1674_SILENT").is_some() {
            let (tx, rx) = channel();
            let (gtx, grx) = channel();
            return Player::silent_clock_with(shared, tx, rx, Arc::clone(&session), new_side(grx), gtx);
        }
"""),
        (midi, b"                inst.plugin.note_on(", b"                crate::ISSUE_1674_ATTACKS.lock().unwrap().push(n.pitch);\n"),
    ]:
        assert original[path].count(needle) == 1, path
        modified[path] = original[path].replace(needle, insertion + needle)
    modified[app] += b"\n" + fixture + b"\n"
    modified[mix] += b"\npub static ISSUE_1674_ATTACKS: std::sync::Mutex<Vec<u8>> = std::sync::Mutex::new(Vec::new());\n"
    env = dict(os.environ, CARGO_TARGET_DIR=str(root / "target" / "issue-1674"), ISSUE_1674_SILENT="1", EXPECT_CLOCK=str(int(has_clock)))
    try:
        for path, data in modified.items():
            path.write_bytes(data)
        return subprocess.run(
            ["cargo", "test", "--locked", "-p", "soundcraft-ui-egui", "--lib", "issue_1674_compare_supported_starts", "--", "--nocapture"],
            cwd=root, env=env,
        ).returncode
    finally:
        for path, data in original.items():
            path.write_bytes(data)


if __name__ == "__main__":
    sys.exit(main())
