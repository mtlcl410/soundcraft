from pathlib import Path
import os, re, subprocess, sys

d = Path(__file__).resolve().parent
c = d / "brake-candidate"
w = d / "follow"
src = (c / "new-guard-green.rs").read_text(encoding="utf8")
grid = (w / "crates/ui-egui/src/app/clock_follow.rs").read_text(encoding="utf8")
extra = (w / "crates/ui-egui/src/app/clock_follow/tests/ramp_response.rs").read_text(encoding="utf8")
drift = grid[grid.index("    #[test]\n    fn two_hours_of_gradual"):grid.index("    #[test]\n    #[ignore",grid.index("    fn two_hours_of_gradual"))]
src += "\nmod ramps {"+extra+"\n}\n"+drift.rsplit("\n    }",1)[0]+"\n}\n"
variant=sys.argv[1]
if variant != "base":
    threshold = sys.argv[2]
    src=src.replace("phase.abs() > 0.0012",f"phase.abs() > {threshold}")
    src=src.replace("self.phase_pulses_left > 0","self.phase_pulses_left > 0 && !self.steady.is_tempo_ramp()")
    src=src.replace("let precise = !s.packed_delivery","let precise = !s.tempo_ramp && !s.packed_delivery")
if len(sys.argv)>3:
    exec(Path(sys.argv[3]).read_text(encoding="utf8"))
prefix="guard-root-"+variant
(c/(prefix+".rs")).write_text(src,encoding="utf8")
opts=(c/"new-guard-green.rsp").read_text(encoding="utf8").replace("new-guard-green",prefix)
(c/(prefix+".rsp")).write_text(opts,encoding="utf8")
with (d/"evidence"/(prefix+"-build.log")).open("wb") as out:
    rc=subprocess.run(["E:/soundcraft/tools/rustup/toolchains/stable-x86_64-pc-windows-msvc/bin/rustc.exe","@../brake-candidate/"+prefix+".rsp"],cwd=w,stdout=out,stderr=subprocess.STDOUT).returncode
if rc:
    print((d/"evidence"/(prefix+"-build.log")).read_text(errors="replace")[:2200]);sys.exit(rc)
with (d/"evidence"/(prefix+".log")).open("wb") as out:
    rc=subprocess.run([str(c/(prefix+".exe")),"ramps::","two_hours_of_gradual","dj_tempos::","--nocapture","--test-threads=2"],stdout=out,stderr=subprocess.STDOUT).returncode
print(prefix,rc,flush=True)
