from common import *
t=d/'mtc'
log=(ev/'1663-10ed5411/soundcraft-ui-egui.log').read_text('utf8')
assert '389 passed; 1 failed' in log
labels=sorted(set(re.findall(r'(?m)^.*?\.rs: (".+")\s*$',log)))
assert len(labels)==10
dest=t/'crates/ui-egui/src/localization.rs'
s=dest.read_text('utf8')
needle='    #[test]\n    fn every_localized_source_string_has_a_catalog_entry()'
helper="""    // Feature keys fall back to English until the translation catalog is updated.
    fn permits_untranslated_sync_label(source: &str) -> bool {
        matches!(
            source,
            """+'\n                | '.join(labels)+"""
        ) && Language::PortugueseBrazil.text(source) == source
    }

"""
assert s.count(needle)==1
s=s.replace(needle,helper+needle.replace('every_localized_source_string_has_a_catalog_entry','localized_source_strings_have_catalog_entries_or_verified_fallbacks'))
needle='&& super::pt_br::translate(&source).is_none()'
assert s.count(needle)==1
dest.write_text(s.replace(needle,needle+'\n                                && !permits_untranslated_sync_label(&source)'),'utf-8')

