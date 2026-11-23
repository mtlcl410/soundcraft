# R-1 — Beat Clock output, independent lower-layer verification

The four repairs and their regression tests were moved to #1662. The MTC-only output fixture remains in #1663. The MTC merge preserves each fix once.

The lower base was 7ff81296df6d36a565c4636d75da682d52bc5423. Its [test-only changes](../r1-1662-red/lower-head-with-probes.patch) adapt test signatures to the earlier implementation. The production transport and recovery logic on the red worktree is the original code.

For item 19, the implementation was already correct on the lower base. To prove the strengthened assertion distinguishes destinations, the negative control swaps the two queued route indices. The distinguishable F1/F8 packets make the mutant fail.

| CodeRabbit item | Regression | On pre-fix base or mutation | On 56169122 |
|---:|---|---|---|
| 5 | `callback_panic_latched_after_service_check_prevents_handoff` | Failed as expected | Passed |
| 6 | `review_unavailable_generation_never_encodes_another_sessions_tempo` | Failed as expected | Passed |
| 7 | `review_superseded_pass_discards_locates_both_before_and_at_their_deadline` | Failed as expected | Passed |
| 8 | `review_failed_transport_stop_is_retried_before_new_pass_start` | Failed as expected | Passed |
| 9 | `applied_selection_retargets_a_failed_open_including_equal_names_on_other_hosts` | Failed as expected | Passed |
| 14 | `review_delay_uses_rate_of_the_audible_callback_after_an_edit` | Failed as expected | Passed |
| 15 | `review_unnameable_output_with_the_same_id_never_opens_its_named_sibling` | Failed as expected | Passed |
| 17 | `review_launch_at_a_rounded_pulse_boundary_does_not_send_two_clocks` | Failed as expected | Passed |
| 18 | `review_stopped_range_warning_persists_until_the_next_locate` | Failed as expected | Passed |
| 19 | `a_missed_timing_gap_invalidates_only_the_compensated_route_queue` | Wrong route rejected (mutation) | Passed |
| 20 | `review_a_stall_beyond_the_repayment_beat_relocates_to_the_current_position` | Failed as expected | Passed |
| 22 | `manual_retry_and_apply_clear_only_the_matching_idle_warning` | Failed as expected | Passed |
| 23 | `exhausted_recovery_can_reopen_an_endpoint_that_never_disappears` | Failed as expected | Passed |
| 24 | `reconnect_uses_the_original_open_host_after_falling_back` | Failed as expected | Passed |

[All assertion failures](../r1-1662-red/red.log) · [Commands and machine-readable measurements](r1-regressions.json) · [Exact-head verification](results.json)
