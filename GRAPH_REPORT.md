# Graph Report - AOI-capacity  (2026-10-30)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 3809 nodes · 9461 edges · 155 communities (140 shown, 15 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 457 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4b6a4382`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 151
- Community 152
- Community 153

## God Nodes (most connected - your core abstractions)
1. `make_cfg()` - 122 edges
2. `collect()` - 94 edges
3. `w()` - 58 edges
4. `_collect()` - 55 edges
5. `CollectPage` - 54 edges
6. `write_html()` - 52 edges
7. `MainWindow` - 49 edges
8. `rows_for_report()` - 48 edges
9. `h()` - 45 edges
10. `meta()` - 41 edges

## Surprising Connections (you probably didn't know these)
- `fake_run()` --calls--> `_Done`  [INFERRED]
  dev/tests/test_cli_update_rerun.py → scripts/collect_wafer_logs.py
- `_emit()` --calls--> `progress()`  [INFERRED]
  aoi_capacity/utils/updater.py → test.py
- `test_update_recheck_runs_every_30_minutes_and_skips_when_busy()` --uses--> `MainWindow`  [INFERRED]
  dev/tests/test_ui_smoke.py → aoi_capacity/ui/main_window.py
- `window()` --uses--> `MainWindow`  [INFERRED]
  dev/tests/test_ui_smoke.py → aoi_capacity/ui/main_window.py
- `fake_run()` --calls--> `_Done`  [INFERRED]
  dev/tests/test_cli_update_rerun.py → scripts/collect_wafer_logs.py

## Import Cycles
- 3-file cycle: `aoi_capacity/devices.py -> aoi_capacity/kla_drives.py -> aoi_capacity/utils/paths.py -> aoi_capacity/devices.py`

## Communities (155 total, 15 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (96): ALL_TABS, Animation(), B(), bootPhase(), byLayer(), CAUSE_CODES, CAUSE_RULES, CLOSE (+88 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (85): _a(), Ae(), Ao(), _assertThisInitialized(), Ba(), be(), bt(), cb() (+77 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (49): make_cfg(), _add_report(), _cache_of(), _count_nas_reads(), _dev_dir(), _entry_fp(), _entry_of(), _lock_replace_for() (+41 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (41): NasWriteRefused, _ansi(), app_icon(), _enabled(), Kind, latest_text(), _pointed_name(), _prune() (+33 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (74): applySettings(), behindAt(), bringToFront(), calloutFit(), canAnim(), closeTop(), countUp(), deckSnap() (+66 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (8): password_files(), read_credentials(), _remote_of(), _win_connect(), make_button(), set_role(), NoWheelDateEdit, NoWheelSpinBox

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (39): ini_roots_for(), _IniMemo, issue_text(), parse_report(), rows_for_report(), split_job_setup(), _backup_ini(), _live_ini() (+31 more)

### Community 7 - "Community 7"
Cohesion: 0.06
Nodes (33): em(), category(), family(), pt(), q(), q(), lotcore(), q() (+25 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (38): _cache_summary(), cached_days(), _collect_log(), _decode_report(), _drive_host(), _entry_sort_stamp(), estimate_run_sec(), estimate_sec() (+30 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (31): _active(), _build_html(), _open_recipe(), page(), test_brand_mark_has_no_tile_and_replays_every_10_seconds(), test_date_controls_keep_day_inside_the_visible_period(), test_device_popup_focus_inert_tab_trap_and_escape_return(), test_error_day_selection_matches_the_header_date() (+23 more)

### Community 10 - "Community 10"
Cohesion: 0.06
Nodes (14): MainWindow, _UpdateSignals, _UpdateWorker, _left_text(), NavBar, _repolish(), ask(), error() (+6 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (29): _assign_device_keys(), merge(), _DeviceIndex, _Dirty, _empty_cache(), fill_gaps(), fill_params(), _fill_setup() (+21 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (11): CollectPage, eta(), _days_text(), eta_text(), _row(), cache_file(), data_root(), output_dir() (+3 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (34): _batch_from_rows(), cause_field(), failed_batch_row(), _first(), _is_error_row(), _is_placeholder(), is_unmapped_status(), job_folder_variants() (+26 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (54): barsHtml(), calloutW(), causeText(), clock(), cnt(), collectChip(), cut(), dateControlsHtml() (+46 more)

### Community 15 - "Community 15"
Cohesion: 0.08
Nodes (23): check_target(), device_links(), _devices_csv(), fake_payload(), file_url(), guide_page(), hammer(), hold_test() (+15 more)

### Community 16 - "Community 16"
Cohesion: 0.07
Nodes (29): load_config(), main(), _print(), _progress_printer(), cb(), ConfigError, dashboard_settings(), fatal() (+21 more)

### Community 17 - "Community 17"
Cohesion: 0.07
Nodes (32): _backup_roots(), _cam_by_key(), _check(), read_one(), CollectCancelled, _Counter, _fill_params_into(), one() (+24 more)

### Community 18 - "Community 18"
Cohesion: 0.07
Nodes (29): cache_failures(), clamp_days(), _dev_name(), device_facts(), fetch_content(), file_path_of(), gather(), is_failure_record() (+21 more)

### Community 19 - "Community 19"
Cohesion: 0.07
Nodes (19): setup_logging(), install_root(), _project_root(), test_ensure_deps_is_noop_in_dev_tree(), test_setup_logging_writes_to_data_root(), test_cli_and_gui_share_the_app_log_file(), _no_input(), test_console_path_waits_for_enter() (+11 more)

### Community 20 - "Community 20"
Cohesion: 0.07
Nodes (25): _lot_rows(), meta(), _rdl(), screen(), test_dashboard_settings_override_the_attention_thresholds(), test_error_popup_shows_each_types_own_phrase_when_one_lot_has_two_types(), test_error_tab_leaves_kla_out(), test_floor_and_maker_filters_combine() (+17 more)

### Community 21 - "Community 21"
Cohesion: 0.06
Nodes (27): _assets_snapshot(), _fingerprint(), _load(), _on(), _package_assets_untouched(), test_build_paths_leave_the_package_folder_untouched(), test_default_temp_js_sits_next_to_the_template(), test_dev_requirements_declare_yaml_and_playwright_but_runtime_does_not() (+19 more)

### Community 22 - "Community 22"
Cohesion: 0.07
Nodes (6): _c(), DeviceStrip, LoadingOverlay, ProgressStrip, _PulseDot, _state_label()

### Community 23 - "Community 23"
Cohesion: 0.09
Nodes (22): collect_one(), copy_ini_for(), copy_report(), diagnose(), find_subdir(), list_folder(), lot_marks(), lot_parts() (+14 more)

### Community 24 - "Community 24"
Cohesion: 0.08
Nodes (25): _check_zip_entries(), _default_branch(), _describe_err(), _git_head(), _http_get(), _identity(), _is_ssl_verify_error(), latest_commit() (+17 more)

### Community 25 - "Community 25"
Cohesion: 0.09
Nodes (39): addDays(), buildModel(), buildModelLegacy(), buildModelV3(), causeOf(), dk(), fillModes(), groupJobs() (+31 more)

### Community 26 - "Community 26"
Cohesion: 0.09
Nodes (40): avg(), cmpDev(), crCell(), crSummary(), crTip(), devSortKey(), exFam(), f0() (+32 more)

### Community 27 - "Community 27"
Cohesion: 0.08
Nodes (18): output_html(), _pump(), test_collect_flow_writes_html_and_updates_status(), test_collect_range_is_editable_and_saved(), test_collect_refuses_out_of_scope_devices(), test_collect_refuses_without_devices(), test_gap_card_shows_missing_counts_and_fills_them(), test_html_days_is_editable_and_reaches_the_collect_cfg() (+10 more)

### Community 28 - "Community 28"
Cohesion: 0.09
Nodes (22): prefs_file(), load(), migrate(), _norm_dir(), patch(), Prefs, save(), test_apply_env_sets_hidpi_and_no_webengine_flags() (+14 more)

### Community 29 - "Community 29"
Cohesion: 0.10
Nodes (6): P(), card2(), card(), fmt(), ok(), pick()

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (24): collect(), test_cancel_before_any_read_leaves_cache_and_output_untouched(), stop(), test_cancel_still_works_while_reading_in_parallel(), test_collect_fixes_performance_values_instead_of_failing(), test_collector_reads_params_once_per_report_and_html_carries_them(), test_fill_params_reads_only_wafer_folders_of_reports_without_snapshots(), _make_rdl() (+16 more)

### Community 31 - "Community 31"
Cohesion: 0.17
Nodes (32): deps_blocked(), download_and_apply(), _emit(), last_error(), _app(), _branch_zip(), _exe_install(), _fake_pip() (+24 more)

### Community 32 - "Community 32"
Cohesion: 0.10
Nodes (17): list_top(), lot_table(), main(), parse_result(), parse_ts(), pick_copies(), pick_lots(), read_head() (+9 more)

### Community 33 - "Community 33"
Cohesion: 0.06
Nodes (19): _advance_cursor(), _collect(), advance_finished(), checkpoint(), flush_read(), log_seen(), save_partial(), _load_resume() (+11 more)

### Community 34 - "Community 34"
Cohesion: 0.06
Nodes (21): is_under(), test_device_index_exact_hits_and_legacy_path_fallback_agree_with_linear_search(), linear(), _cli_config(), count(), spy(), spy_bytes(), _count_report_reads() (+13 more)

### Community 35 - "Community 35"
Cohesion: 0.09
Nodes (18): apply_to_app(), colors(), normalize_color_mode(), palettes(), parse_template_tokens(), render_qss(), set_color_mode(), isolated_data() (+10 more)

### Community 36 - "Community 36"
Cohesion: 0.09
Nodes (17): backup_cutoff(), _candidates(), device_id(), dir_key(), _dirs_of(), display_name(), _entry(), find_subdir() (+9 more)

### Community 37 - "Community 37"
Cohesion: 0.09
Nodes (18): collect_kla(), merge(), p1(), p2(), p3(), _fmt(), _is_scanning_lock(), list_date() (+10 more)

### Community 38 - "Community 38"
Cohesion: 0.07
Nodes (17): cache_status(), read_ini(), read_recipe_settings(), read_recipes_info(), _validate_cache_file(), _read_all(), read_bytes(), read_text() (+9 more)

### Community 39 - "Community 39"
Cohesion: 0.11
Nodes (20): _pool_size(), with_dirs(), make_device(), _case_insensitive_isdir(), _cfg(), _many_devices(), _snapshot(), test_backup_cutoff_reads_every_folder_name_seen_on_30_machines() (+12 more)

### Community 40 - "Community 40"
Cohesion: 0.12
Nodes (22): _cache_of(), _count_htm_reads(), spy(), _csv(), _fingerprint(), _raw(), _row(), _same_mtime() (+14 more)

### Community 41 - "Community 41"
Cohesion: 0.15
Nodes (26): at(), run(), test_a_wafer_crossing_midnight_is_split_between_the_two_days_and_counted_once(), test_an_untimed_error_takes_the_uncovered_minutes_of_its_batch_window(), test_collection_day_denominator_is_the_last_record_of_all_devices(), test_day_falls_back_to_the_last_data_day_when_the_collection_day_has_no_data(), test_devices_follow_devices_sort_key_and_out_of_scope_devices_are_listed_apart(), test_estimate_only_fills_minutes_no_measurement_claims() (+18 more)

### Community 42 - "Community 42"
Cohesion: 0.08
Nodes (30): concurrency, cancel-in-progress, group, SHA, permissions, runs-on, steps, jobs (+22 more)

### Community 43 - "Community 43"
Cohesion: 0.11
Nodes (16): embedded(), load(), read_bytes(), sample_path(), sha256(), unfold(), test_home_rows_follow_device_order_and_save_copy_refolds_the_same_columns(), test_recipe_groups_apply_at_once_persist_in_browser_and_export() (+8 more)

### Community 44 - "Community 44"
Cohesion: 0.10
Nodes (7): _card(), _date_edit(), _GapRow, _label(), ModeCard, _repolish(), _tool()

### Community 45 - "Community 45"
Cohesion: 0.08
Nodes (11): _fingerprint(), _report(), test_a_report_without_a_lot_never_lists_the_setup_folder(), test_device_roots_are_listed_near_the_top_of_the_file(), test_diagnose_points_at_an_unexpected_report_folder_name(), test_loadport_placeholder_is_not_taken_as_the_lot(), test_lot_suffix_split(), test_norm_root_fixes_bare_drive_letter() (+3 more)

### Community 46 - "Community 46"
Cohesion: 0.09
Nodes (18): _utf8_len(), write_html(), test_write_html_failure_keeps_the_previous_html(), test_write_html_rejects_template_without_exactly_one_data_slot(), test_collect_writes_a_detailed_log_to_app_log_and_not_into_the_html(), _meta(), _nas_calls(), test_collect_with_bad_scope_raises_before_any_nas_call_and_writes_nothing() (+10 more)

### Community 47 - "Community 47"
Cohesion: 0.11
Nodes (15): _write_csv(), assert_local(), check_cfg(), roots_for_cfg(), _call_name(), _enclosing_function(), test_assert_local_and_check_cfg(), test_nas_guard_module_has_no_write_helpers() (+7 more)

### Community 48 - "Community 48"
Cohesion: 0.15
Nodes (5): write_devices_csv(), DevicesPage, devices_csv_path(), test_card_remembers_days_runs_and_blocks_collect(), window()

### Community 49 - "Community 49"
Cohesion: 0.15
Nodes (16): deps_installed(), deps_marker(), ensure_deps(), pip_install_cmd(), req_fingerprint(), req_lines(), write_deps_marker(), _root() (+8 more)

### Community 50 - "Community 50"
Cohesion: 0.11
Nodes (14): _default_run(), busy(), globals_(), _okw(), run_raw(), test_default_profile_is_product_with_the_four_rules_on_and_constants_match(), test_kla_tb500_job_names_are_shortened_for_display_only(), test_legacy_profile_equals_the_design_script_on_the_30_day_sample() (+6 more)

### Community 51 - "Community 51"
Cohesion: 0.12
Nodes (13): build(), graphify_cmds(), inline_scripts(), main(), write_inline_js(), git_sha(), main(), measure() (+5 more)

### Community 52 - "Community 52"
Cohesion: 0.14
Nodes (13): _make_nas(), _report(), _snapshot(), test_all_never_exceeds_ten_zip_parts(), test_all_reads_every_lot_in_window_bundles_results_and_dedups_params_across_lots(), put(), test_collects_read_only_dedups_and_splits(), test_encrypt_default_and_decode_round_trips() (+5 more)

### Community 53 - "Community 53"
Cohesion: 0.13
Nodes (16): _cfg(), _cursor_of(), _embedded(), test_auto_row_finds_allowed_machines_without_listing_the_share(), test_cli_run_stays_in_scope(), test_collect_entry_points_stay_in_scope(), test_display_rename_keeps_one_device_and_one_cursor(), test_failed_report_blocks_cursor_and_is_retried() (+8 more)

### Community 54 - "Community 54"
Cohesion: 0.17
Nodes (19): build_exe(), clean_stale_output(), _default_run(), _dir_size_mb(), _ensure_venv(), exe_out_dirname(), import_probe_cmd(), _load_portable_impl() (+11 more)

### Community 55 - "Community 55"
Cohesion: 0.13
Nodes (14): kla_name(), missed_in_scope(), allowed_keys(), allows_row(), describe(), is_allowed(), is_kla(), key() (+6 more)

### Community 56 - "Community 56"
Cohesion: 0.17
Nodes (12): CollectorSignals, CollectorWorker, _collect_signals(), test_csv_lock_completes_with_warnings_not_failed(), locked(), test_failure_is_reported_not_raised(), test_full_publish_result_reaches_the_done_result(), test_html_lock_is_still_reported_as_failure() (+4 more)

### Community 57 - "Community 57"
Cohesion: 0.09
Nodes (14): fake_nas(), _no_startup_side_effects(), qapp(), _qt_app(), _no_real_subprocess(), fake_win(), scoped_nas(), fixture() (+6 more)

### Community 58 - "Community 58"
Cohesion: 0.11
Nodes (14): _cache_device(), _carry_over(), newest_of(), _entry_newest(), parse_dt(), parse_mdy(), read_ext_meta(), read_scan_log() (+6 more)

### Community 59 - "Community 59"
Cohesion: 0.12
Nodes (12): plan_run(), RunPlan, test_plan_run_never_rederives_rows_and_memoizes_by_file_stamp(), _cache(), _sec_rows(), test_fill_gaps_fills_scan_ratio_from_wafer_folder_only_and_marks_reports(), test_fill_gaps_leaves_value_empty_when_folder_was_rewritten_later(), test_fill_gaps_stop_keeps_what_was_read() (+4 more)

### Community 60 - "Community 60"
Cohesion: 0.16
Nodes (13): _attach_dirs(), _dedupe_sort(), devices_from_csv(), devices_from_rows(), discover_devices(), _discover_under(), _log(), _norm_root() (+5 more)

### Community 61 - "Community 61"
Cohesion: 0.09
Nodes (8): test_browser_never_reads_the_nas_itself(), test_no_network_use_at_all(), test_removed_features_stay_removed(), test_screen_terms_are_the_design_terms_and_old_ones_are_gone(), test_the_dialogs_have_accessible_names(), test_vendor_block_makes_no_requests_either(), test_vendored_libraries_are_inline_with_their_notices(), _without_vendor()

### Community 62 - "Community 62"
Cohesion: 0.15
Nodes (15): empty_store(), _ounion(), put(), recipe_names(), snapshot(), test_param_tab_unpacks_a_job_on_demand_and_marks_differing_cells(), _meta(), _snap() (+7 more)

### Community 63 - "Community 63"
Cohesion: 0.20
Nodes (15): _bundle(), _layout(), _marker(), _mk(), test_first_run_uses_the_console_python(), test_later_runs_are_windowless(), test_missing_console_python_falls_back_to_pythonw(), test_swap_applies_pending_update() (+7 more)

### Community 64 - "Community 64"
Cohesion: 0.10
Nodes (11): _numbers(), test_decision_numbers_are_unique_and_unbroken(), test_hook_reads_the_korean_file_name_correctly(), test_last_updated_line_is_present(), test_newest_work_log_entry_points_at_a_real_commit(), test_numbers_in_claude_md_match_the_code(), test_progress_doc_numbers_match_the_code(), test_required_section_exists() (+3 more)

### Community 65 - "Community 65"
Cohesion: 0.19
Nodes (14): _default_branch_name(), _fetch_runtime(), _git_head(), _import_app_module(), _isolated(), missing_packages(), _normalize_dist(), portable_python() (+6 more)

### Community 66 - "Community 66"
Cohesion: 0.16
Nodes (12): _lot_keys(), _lot_screen(), test_lot_tab_groups_by_wafer_id_not_by_name_and_follows_devices(), test_lot_tab_ignores_slot_ids_and_parses_kla_names(), test_lot_tab_matrix_cells_show_defect_counts(), test_lot_tab_merges_one_char_ocr_misreads_but_not_other_wafers(), test_lot_tab_never_merges_past_25_wafers_and_shows_cross_rows(), test_lot_tab_tags_retries_rescans_and_lists_every_wafer() (+4 more)

### Community 67 - "Community 67"
Cohesion: 0.13
Nodes (13): _embed_rows(), _embedded(), _fixture_rows(), _meta(), _open_rows_page(), rdl2_page(), rdl_page(), _rdl_rows() (+5 more)

### Community 68 - "Community 68"
Cohesion: 0.14
Nodes (8): unpack(), test_extract_script_runs_on_the_product_sample(), build(), bundle_template(), encode_camel_attrs(), main(), offline_variant(), _res()

### Community 69 - "Community 69"
Cohesion: 0.10
Nodes (5): _DaysWorker, _GapFillWorker, _HtmlOnlyWorker, _LotPublishWorker, _PlanWorker

### Community 70 - "Community 70"
Cohesion: 0.12
Nodes (9): _fake_out(), _load(), test_run_build_lite_with_fakes(), test_verify_checks_pass_on_valid_lite_output(), test_verify_full_requires_packages_and_marker(), test_verify_lite_rejects_marker_and_internal(), test_verify_rejects_big_launcher_and_missing_template_placeholder(), test_version_stamp_json() (+1 more)

### Community 71 - "Community 71"
Cohesion: 0.18
Nodes (14): _add(), _cache(), _fake_lister(), _name_for(), _reports(), test_backfill_and_refresh_always_list_everything(), test_full_listing_interval_defaults_to_seven_days_and_is_configurable(), age_full_listing() (+6 more)

### Community 72 - "Community 72"
Cohesion: 0.14
Nodes (10): _launch(), page_factory(), test_tab_indicator_moves_like_a_body_dragged_by_its_front(), _fingerprint(), _load(), test_build_produces_one_closed_file_whose_logic_parses(), test_build_writes_only_where_it_is_told(), test_camel_attrs_are_encoded_only_in_markup_not_in_the_script() (+2 more)

### Community 73 - "Community 73"
Cohesion: 0.12
Nodes (12): categories(), find_subdir(), is_placeholder(), name_day(), norm_root(), read_bytes(), scan_dirs(), survey_device() (+4 more)

### Community 74 - "Community 74"
Cohesion: 0.14
Nodes (14): rerun_args(), rerun_without_update(), _bat(), test_cli_never_execs(), test_default_runner_uses_subprocess_run_and_propagates_returncode(), fake_run(), test_main_with_update_reruns_once_as_a_child_and_does_not_collect_in_the_parent(), test_main_without_a_new_version_collects_in_place() (+6 more)

### Community 75 - "Community 75"
Cohesion: 0.15
Nodes (13): _bundled_python(), _discard(), _ensure_deps(), _file_text(), _install_root(), _move(), _pending_dir(), _promote_in_place() (+5 more)

### Community 76 - "Community 76"
Cohesion: 0.21
Nodes (10): _q(), download(), git(), git_update(), is_git_repo(), main(), _opener(), repo_root() (+2 more)

### Community 77 - "Community 77"
Cohesion: 0.18
Nodes (12): _full(), local(), _make_zip(), _patch_download(), test_git_update_reports_already_up_to_date(), test_git_update_stops_when_working_tree_is_dirty(), fake_git(), test_main_uses_zip_when_folder_is_not_a_git_checkout() (+4 more)

### Community 78 - "Community 78"
Cohesion: 0.16
Nodes (16): ms_since(), now_s(), op_isdir(), op_isfile(), op_open_read(), op_os_read_once(), resolve_wafer(), _run_level() (+8 more)

### Community 79 - "Community 79"
Cohesion: 0.12
Nodes (9): params_for_range(), build_meta(), _canon(), _every(), _group_of(), job_key(), split_unit(), _struct() (+1 more)

### Community 80 - "Community 80"
Cohesion: 0.15
Nodes (4): is_dark_mode(), host_for(), _scrim_color(), SheetHost

### Community 81 - "Community 81"
Cohesion: 0.16
Nodes (9): _stage_tree(), _verify_staged(), _write_version(), _write_version_to(), _fake_repo(), test_github_archive_contains_only_deploy_files(), test_staging_real_tree_passes_verification_and_top_level_equals_allow_list(), test_staging_top_level_equals_allow_list_even_with_junk_in_source_root() (+1 more)

### Community 82 - "Community 82"
Cohesion: 0.17
Nodes (8): blob_key(), decode(), _keep(), normalize(), parse_ini(), parse_rtp(), prune_blobs(), _split_comment()

### Community 83 - "Community 83"
Cohesion: 0.17
Nodes (12): default_devices_csv(), _ensure_dir(), ensure_user_files(), log_file(), logo_path(), resource_path(), template_path(), test_data_root_is_never_inside_app_tree() (+4 more)

### Community 84 - "Community 84"
Cohesion: 0.19
Nodes (8): candidates(), load(), normalize(), _read(), test_load_picks_the_latest_saved_among_data_folder_and_downloads(), test_normalize_drops_bad_and_duplicate_entries(), test_write_html_embeds_recipe_groups(), _w()

### Community 85 - "Community 85"
Cohesion: 0.17
Nodes (10): _fail_move_when(), _loose_app(), _snapshot(), test_latest_self_healing_retries_default_branch(), fake(), test_promote_recovers_a_backup_left_by_an_earlier_failed_rollback(), test_promote_success_replaces_all_and_leaves_no_backups(), test_rollback_failure_keeps_backups_and_names_the_files() (+2 more)

### Community 86 - "Community 86"
Cohesion: 0.22
Nodes (7): collect_lot(), is_bundle(), pack_lot_all(), Packer, recipe_mode(), safe(), stamp()

### Community 87 - "Community 87"
Cohesion: 0.17
Nodes (8): check_rows(), probe(), probe(), _has_report(), _is_kla_root(), _probe_auto(), _CheckWorker, test_check_rows_reports_out_of_scope_without_touching()

### Community 88 - "Community 88"
Cohesion: 0.18
Nodes (3): dur_text(), CollectResult, test_stale_token_signals_are_ignored()

### Community 89 - "Community 89"
Cohesion: 0.22
Nodes (7): _ask(), _ask_int(), _ask_levels(), _ask_yes(), interactive(), main(), _pause()

### Community 90 - "Community 90"
Cohesion: 0.21
Nodes (12): cap(), run(), allocate(), log(), real_collect_summary(), _run(), run_cmd(), _run_real() (+4 more)

### Community 91 - "Community 91"
Cohesion: 0.19
Nodes (8): _app_root(), check_for_update(), current_version(), ensure_version_file(), _git_head_ref(), is_git_checkout(), _version_file(), test_current_version_prefers_git_head_over_a_stale_version_file()

### Community 92 - "Community 92"
Cohesion: 0.19
Nodes (7): job_alias(), model_version(), rules(), section(), text(), test_no_view_clock_in_the_model_section(), test_status_classification_matches_the_python_side_and_the_design_script()

### Community 93 - "Community 93"
Cohesion: 0.23
Nodes (6): _FakeBuild, _out(), _polluted(), test_no_zip_when_verification_fails(), test_polluted_dist_ships_no_cache_log_or_backup_but_keeps_runtime(), test_zip_layout_and_instructions()

### Community 94 - "Community 94"
Cohesion: 0.19
Nodes (8): _cache(), _picked(), test_bulk_listing_failure_falls_back_to_scandir(), test_full_listing_uses_the_bulk_lister_and_picks_the_same_reports(), test_ini_memo_classifies_missing_the_same(), test_os_open_in_nas_guard_is_read_only(), test_read_bytes_matches_builtin_open(), test_read_text_matches_builtin_open()

### Community 95 - "Community 95"
Cohesion: 0.22
Nodes (8): decode(), decrypt_bytes(), _enc_secret(), encrypt_bytes(), _keystream(), main(), parse_args(), say()

### Community 96 - "Community 96"
Cohesion: 0.22
Nodes (6): app_paths(), _error(), launch_cmd(), Layout, main(), swap_pending()

### Community 97 - "Community 97"
Cohesion: 0.27
Nodes (9): _ansi(), clean(), _desktop(), main(), make(), _url(), _write(), copy_app_tree() (+1 more)

### Community 98 - "Community 98"
Cohesion: 0.26
Nodes (11): _ci_gate(), _is_full_sha(), _run(), _runs(), _serve_runs(), test_atom_fallback_and_error_recording(), fake_get(), test_ci_gate_holds_on_pending_failed_or_missing() (+3 more)

### Community 99 - "Community 99"
Cohesion: 0.19
Nodes (6): content_sha(), entries(), test_every_archived_file_matches_its_original_fingerprint(), test_everything_under_archive_is_listed(), test_manifest_has_entries_and_no_duplicates(), test_no_compiled_python_is_tracked()

### Community 100 - "Community 100"
Cohesion: 0.21
Nodes (7): _clean_batches(), _hhmm(), test_report_tab_counts_a_batch_that_crosses_midnight_once(), test_report_tab_judges_time_per_wafer_within_each_device_not_across_the_fleet(), test_report_tab_leaves_out_a_batch_whose_time_per_wafer_is_far_from_its_group(), test_report_tab_reads_dia_after_an_underscore(), test_report_tab_regresses_only_with_five_or_more_clean_batches_and_lists_exclusions()

### Community 101 - "Community 101"
Cohesion: 0.21
Nodes (7): resolver(), _dns(), _snapshot(), test_other_share_on_same_server_is_allowed_but_noted(), test_read_devices_and_links(), test_refuses_under_device_root_and_same_share_in_any_spelling(), test_run_stops_without_devices_csv_unless_told()

### Community 102 - "Community 102"
Cohesion: 0.21
Nodes (3): Deadline, OpRecorder, real_collect_runs()

### Community 103 - "Community 103"
Cohesion: 0.18
Nodes (7): ensure_camtek_rows(), ensure_kla_rows(), read_devices_csv(), test_read_csv_cp949_and_utf8_and_aliases(), test_read_csv_without_header_and_comments(), test_write_then_read_roundtrip(), test_existing_devices_csv_gets_the_eight_kla_rows_once()

### Community 104 - "Community 104"
Cohesion: 0.26
Nodes (6): _decrypt(), import_zips(), man(), read(), _open_zips(), _wanted()

### Community 105 - "Community 105"
Cohesion: 0.17
Nodes (7): ctx, fs, html, input, path, stub(), vm

### Community 106 - "Community 106"
Cohesion: 0.30
Nodes (8): collect_files(), instructions_text(), _load_build_module(), main(), make_zip(), read_version(), should_include(), zip_basename()

### Community 107 - "Community 107"
Cohesion: 0.27
Nodes (9): pick(), run(), collect_one(), done_ok(), limit_reached(), run_all(), run_wide(), take() (+1 more)

### Community 108 - "Community 108"
Cohesion: 0.33
Nodes (11): navBox(), navCancel(), navGo(), navInd(), navNow(), navParts(), navRest(), navSet() (+3 more)

### Community 109 - "Community 109"
Cohesion: 0.18
Nodes (6): deps_changed(), _gate_info(), manual_check(), test_manual_check_reports_tls_failure(), test_ssl_verify_failure_stops_check_with_reason_and_no_retry(), _VerifyFailOpener

### Community 110 - "Community 110"
Cohesion: 0.25
Nodes (5): _git(), _load(), test_check_requires_the_doc_only_when_code_changed(), test_code_paths_match_the_opt_in_hook(), test_main_looks_at_the_merge_base_range_not_only_the_last_commit()

### Community 111 - "Community 111"
Cohesion: 0.29
Nodes (5): main(), measure(), old_write_html(), rss_mb(), timed()

### Community 112 - "Community 112"
Cohesion: 0.18
Nodes (10): env, PIP_DISABLE_PIP_VERSION_CHECK, jobs, progress-doc, name, permissions, contents, if (+2 more)

### Community 113 - "Community 113"
Cohesion: 0.29
Nodes (11): steps, steps, AOI_SHARD, QT_QPA_PLATFORM, steps, env, id, name (+3 more)

### Community 114 - "Community 114"
Cohesion: 0.22
Nodes (9): analyze(), _diff(), dist(), _dt_of(), med_ci(), parse_ini_bytes(), pct(), stage_times() (+1 more)

### Community 115 - "Community 115"
Cohesion: 0.29
Nodes (7): reconnect(), test_no_password_file_means_no_attempt(), test_not_windows_or_not_drive_letter_does_nothing(), test_out_of_scope_kla_row_never_reconnects(), test_single_line_is_password_for_current_account(), test_two_lines_are_account_then_password_and_output_dir_wins(), test_unknown_remote_is_not_invented()

### Community 116 - "Community 116"
Cohesion: 0.22
Nodes (6): _fingerprint(), test_corrupt_cache_is_preserved_as_bad_file_not_overwritten_silently(), test_reading_in_parallel_gives_exactly_the_same_result(), test_recover_targets_only_ini_states_that_can_come_back(), test_stop_keeps_what_was_read_and_next_run_continues(), test_worker_count_is_clamped_to_the_work_there_is()

### Community 117 - "Community 117"
Cohesion: 0.36
Nodes (6): _cfg(), _embedded(), _model(), test_a_chosen_period_draws_only_its_days_and_matches_the_whole_file(), test_default_html_is_the_last_html_days_of_the_data_in_one_file(), test_html_from_cache_needs_no_nas_and_keeps_report_paths()

### Community 118 - "Community 118"
Cohesion: 0.22
Nodes (7): file_times(), _ft(), op_find_exact(), op_getattr(), op_win_createfile_read(), _win(), win_find()

### Community 119 - "Community 119"
Cohesion: 0.22
Nodes (5): expand_roots(), normalize(), _share_root(), _unc_for_drive(), test_expand_roots_adds_share_root_for_unc()

### Community 121 - "Community 121"
Cohesion: 0.28
Nodes (3): tripwire(), wrap(), Tripwire

### Community 122 - "Community 122"
Cohesion: 0.25
Nodes (9): name, runs-on, strategy, timeout-minutes, strategy, browser, shard, fail-fast (+1 more)

### Community 123 - "Community 123"
Cohesion: 0.25
Nodes (3): find_pattern(), FoundEntry, _Stat

### Community 124 - "Community 124"
Cohesion: 0.25
Nodes (6): Aa(), Ca(), na(), Vb(), wb(), Xb()

### Community 125 - "Community 125"
Cohesion: 0.54
Nodes (6): _example(), _public(), test_every_default_config_key_is_in_the_example_or_explicitly_excused(), test_example_loads_through_the_cli_loader(), test_example_public_keys_are_a_subset_of_default_config_with_the_same_types(), test_example_scope_and_workers_show_the_real_defaults()

### Community 126 - "Community 126"
Cohesion: 0.25
Nodes (8): with, cache, cache-dependency-path, fetch-depth, key, node-version, path, python-version

### Community 129 - "Community 129"
Cohesion: 0.38
Nodes (3): bootCore(), loop(), S

### Community 130 - "Community 130"
Cohesion: 0.33
Nodes (4): ensure_html(), exists(), html_path(), test_ensure_html_creates_openable_file_without_collecting()

### Community 131 - "Community 131"
Cohesion: 0.29
Nodes (4): job_folder_variants(), lot_dir_of(), read_lot_all(), submit()

### Community 132 - "Community 132"
Cohesion: 0.29
Nodes (5): _list_files(), run_grouped(), stage_reports(), list_one(), Wafer

### Community 133 - "Community 133"
Cohesion: 0.33
Nodes (5): take(), test_ini_memo_lets_concurrent_readers_share_one_open(), slow(), test_run_stops_fast_without_waiting_for_slow_reads(), on_result()

### Community 134 - "Community 134"
Cohesion: 0.47
Nodes (5): bootScene(), assign(), build(), lotFrame(), waferLayout()

### Community 135 - "Community 135"
Cohesion: 0.47
Nodes (4): flatten(), full(), num(), same()

### Community 136 - "Community 136"
Cohesion: 0.33
Nodes (3): fake_run(), _Done, _Full

### Community 137 - "Community 137"
Cohesion: 0.53
Nodes (6): _extract(), test_safe_extract_accepts_github_layout_and_short_sha_root(), test_safe_extract_caps_file_count_and_total_size(), test_safe_extract_rejects_hostile_entries_without_writing(), test_safe_extract_rejects_symlinks(), _zip_of()

### Community 140 - "Community 140"
Cohesion: 0.50
Nodes (5): Context(), Db(), Eb(), Et(), fb()

### Community 144 - "Community 144"
Cohesion: 0.67
Nodes (4): makeLib(), curl(), noise(), mulberry()

### Community 145 - "Community 145"
Cohesion: 0.50
Nodes (4): name, runs-on, timeout-minutes, core

### Community 146 - "Community 146"
Cohesion: 0.50
Nodes (4): on, pull_request, push, branches

### Community 148 - "Community 148"
Cohesion: 0.67
Nodes (3): concurrency, cancel-in-progress, group

## Knowledge Gaps
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `collect()` connect `Community 30` to `Community 33`, `Community 2`, `Community 34`, `Community 102`, `Community 71`, `Community 8`, `Community 40`, `Community 74`, `Community 11`, `Community 39`, `Community 46`, `Community 16`, `Community 116`, `Community 117`, `Community 53`, `Community 56`, `Community 59`, `Community 94`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `collect()` (e.g. with `test_zero_new_rows_but_state_change_still_saves()` and `test_main_with_update_reruns_once_as_a_child_and_does_not_collect_in_the_parent()`) actually correct?**
  _`collect()` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.017239772621377318 - nodes in this community are weakly interconnected._
- **Why does `TableParser` connect `Community 128` to `Community 8`, `Community 6`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06730506155950752 - nodes in this community are weakly interconnected._
- **Why does `CollectPage` connect `Community 12` to `Community 130`, `Community 5`, `Community 10`, `Community 44`, `Community 141`, `Community 120`, `Community 142`, `Community 88`, `Community 27`, `Community 28`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.06151742993848257 - nodes in this community are weakly interconnected._