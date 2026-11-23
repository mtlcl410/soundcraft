from pathlib import Path
p=Path("apps/soundcraft/src/config.rs")
s=p.read_text(encoding="utf8")
where='    reset_invalid(fields, "midi_sync", "midi_sync", Value::is_object, resets);'
assert where in s
s=s.replace(where,'''    reset_invalid(fields, "gen_mtc", "gen_mtc", Value::is_boolean, resets);
    for port in ["mtc_input_port", "mtc_output_port"] {
        reset_invalid(fields, port, port, |v| v.is_null() || v.as_str().is_some_and(valid_port), resets);
    }
'''+where,1)
p.write_text(s,encoding="utf8")
