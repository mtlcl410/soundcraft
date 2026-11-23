## MTC verification after the Beat Clock fixes moved to #1662

Revision `{head}` includes the lower layer by a merge commit. Before the language catalog change, the merged tree was byte-for-byte identical to the earlier reviewed MTC revision. The queue, port identity, recovery and reconnect corrections are exercised in #1662 and inherited by MTC. The UI's English fallback is covered independently for the new MTC labels. The Model 12 hardware measurements are from the prior acceptance runs.

**Recovered document and offset warning (review item 12).** The regression `recovery_reports_the_document_name_and_the_external_offset_conflict` failed with the warning preservation reverted. For Take 12 the status contained only “Recovered ‘Take 12’. Save it to keep the changes.” and omitted the conflicting external-offset warning. The test on this revision verifies that the status includes both the document name and the offset conflict. Reproduce with `cargo test --locked -p soundcraft-ui-egui --lib recovery_reports_the_document_name_and_the_external_offset_conflict`.

All ten inline threads in the [formal review](https://github.com/storytold/soundcraft/pull/1663#pullrequestreview-6010501117) are resolved. The [finding-by-finding table](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7074865328) records the observed failures. The known Windows movie-relink test remains tracked in #1536.

