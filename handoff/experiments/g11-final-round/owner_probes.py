"""Run original-head proofs without touching a PR branch."""
from pathlib import Path
import re, subprocess, sys

d=Path(__file__).resolve().parent
w=d/'red63'
cases={
    'crates/playback/src/mtc/tests.rs':['first_integer_sample_of_an_even_fractional_frame_emits_its_quarter_group'],
    'crates/playback/src/mtc_input.rs':['full_frame_locate_matches_fractional_rate_session_start'],
    'crates/engine/src/cmd/options.rs':['timecode_labels_for_session_start_and_durations_have_no_session_offset','timecode_retention_shifts_following_automation_and_refuses_underflow_atomically'],
    'crates/ui-egui/src/app/mtc.rs':['offset_edit_repositions_a_stopped_reader_without_another_packet','online_transition_gates_a_record_command_already_in_the_queue'],
}
def test_block(code,name):
    rx=rf'(?m)^( *)#\[test\]\n\1fn {name}\(\) \{{.*?^\1\}}\n'
    return re.search(rx,code,re.S|re.M)[0]
if __name__=='__main__':
    for path, names in cases.items():
        original=subprocess.check_output(['git','show',f'14030820:{path}'],cwd=w).decode()
        upper=subprocess.check_output(['git','show',f'c093aedb:{path}'],cwd=w).decode()
        start=original.index('#[test]')
        start=original.rfind('\n',0,start)+1
        (w/path).write_text(original[:start]+'\n'.join(test_block(upper,n) for n in names)+'\n'+original[start:],encoding='utf8')
