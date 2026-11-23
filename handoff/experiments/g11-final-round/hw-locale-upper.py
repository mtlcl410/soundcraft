from pathlib import Path
import subprocess
d=Path('.')
p='crates/ui-egui/src/localization.rs'
def resolve(w):
    orig=subprocess.check_output(['git','show','HEAD:'+p],cwd=w).decode().replace('\r\n','\n')
    b=(d/'beat'/p).read_text(encoding='utf8')
    name='    #[test]\n    fn beat_clock_uses_the_catalog_or_english'
    test=b[b.index(name):b.index('    #[test]\n    fn localized_source_strings_have_')]
    key='    #[test]\n    fn localized_source_strings_have_'
    assert orig.count(key)==1
    orig=orig.replace(key,test+key)
    begin='fn permits_untranslated_beat_clock_label'
    s=b[b.index('            source,\n',b.index(begin))+len('            source,\n'):b.index('\n        ) &&',b.index(begin))]
    mark='            source,\n'
    a=orig.index(mark,orig.index('fn permits_untranslated_sync_label'))+len(mark)
    orig=orig[:a]+s+'\n                | '+orig[a:].lstrip(' ')
    (w/p).write_text(orig,encoding='utf8')
resolve(d/'follow')

