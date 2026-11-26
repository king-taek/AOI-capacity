# Graph Report - AOI-capacity  (2026-11-26)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 4447 nodes · 10959 edges · 194 communities (155 shown, 39 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 507 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `58cba4f6`
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
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 172
- Community 173

## God Nodes (most connected - your core abstractions)
1. `make_cfg()` - 141 edges
2. `collect()` - 114 edges
3. `w()` - 73 edges
4. `CollectPage` - 65 edges
5. `write_html()` - 61 edges
6. `meta()` - 59 edges
7. `_collect()` - 58 edges
8. `screen()` - 54 edges
9. `rows_for_report()` - 53 edges
10. `MainWindow` - 50 edges

## Surprising Connections (you probably didn't know these)
- `fake_run()` --calls--> `_Done`  [INFERRED]
  dev/tests/test_cli_update_rerun.py → scripts/collect_wafer_logs.py
- `test_update_recheck_runs_every_30_minutes_and_skips_when_busy()` --uses--> `MainWindow`  [INFERRED]
  dev/tests/test_ui_smoke.py → aoi_capacity/ui/main_window.py
- `test_number_and_date_boxes_have_no_arrows_and_change_only_by_typing()` --uses--> `NoWheelDateEdit`  [INFERRED]
  dev/tests/test_ui_smoke.py → aoi_capacity/ui/widgets/inputs.py
- `test_out_dir_under_a_nas_root_is_refused()` --uses--> `NasWriteRefused`  [INFERRED]
  dev/tests/test_lot_publish.py → aoi_capacity/nas_guard.py
- `test_publish_refuses_a_folder_under_an_equipment_nas()` --uses--> `NasWriteRefused`  [INFERRED]
  dev/tests/test_lot_publish.py → aoi_capacity/nas_guard.py

## Import Cycles
- 3-file cycle: `aoi_capacity/devices.py -> aoi_capacity/kla_drives.py -> aoi_capacity/utils/paths.py -> aoi_capacity/devices.py`

## Communities (194 total, 39 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (102): ALL_TABS, B(), barsColor(), barsCtl(), barsGeom(), barsListScene(), barsMake(), byLayer() (+94 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (95): _a(), a(), Aa(), Ae(), Animation(), Ao(), _assertThisInitialized(), Ba() (+87 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (39): CacheUnreadable, _check_range(), _collect_log(), _entry_sort_stamp(), estimate_run_sec(), estimate_sec(), HtmlPrep, is_recipe_tab_job() (+31 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (42): _advance_cursor(), _assign_device_keys(), cached_days(), _collect(), advance_finished(), checkpoint(), flush_read(), log_seen() (+34 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (43): ini_roots_for(), _IniMemo, issue_text(), parse_report(), rows_for_report(), split_job_setup(), _backup_ini(), _ini_at() (+35 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (45): _add_report(), _cli_config(), _count_nas_reads(), count(), spy(), spy_bytes(), _count_report_reads(), spy() (+37 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (40): _lot_rows(), meta(), _okw(), _rdl(), screen(), test_attention_concept_is_gone_and_old_dashboard_settings_are_ignored(), test_device_popup_follows_the_list_order_and_separates_no_record_from_idle(), test_error_popup_shows_each_types_own_phrase_when_one_lot_has_two_types() (+32 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (41): apply(), params_for_range(), blob_key(), build_meta(), items_of(), _canon(), decode(), empty_store() (+33 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (30): _active(), _open_recipe(), test_bar_value_changes_slide_on_transform_not_width_or_height(), test_date_controls_keep_day_inside_the_visible_period(), test_device_popup_focus_inert_tab_trap_and_escape_return(), test_error_day_selection_matches_the_header_date(), test_error_job_list_offers_show_all_only_when_more_than_twelve(), test_error_lists_keep_rows_in_place_and_only_text_changes() (+22 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (63): barsHtml(), calloutW(), causeText(), clock(), cnt(), collectChip(), cut(), dateControlsHtml() (+55 more)

### Community 10 - "Community 10"
Cohesion: 0.06
Nodes (14): dur_text(), MainWindow, _UpdateSignals, _UpdateWorker, NavBar, _repolish(), ask(), error() (+6 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (23): category(), family(), q(), q(), lotcore(), q(), core(), q() (+15 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (26): _backup_roots(), _cache_summary(), _cam_by_key(), _Counter, _drive_host(), fill_gaps_budget_into(), _fill_kla_images_into(), _fill_params_into() (+18 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (31): load_config(), main(), _print(), _progress_printer(), cb(), rerun_args(), rerun_without_update(), ConfigError (+23 more)

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (4): _days_text(), _why_text(), make_button(), set_role()

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (34): _batch_from_rows(), cause_field(), failed_batch_row(), _first(), _is_error_row(), _is_placeholder(), is_unmapped_status(), job_folder_variants() (+26 more)

### Community 17 - "Community 17"
Cohesion: 0.06
Nodes (24): _pump(), test_closing_during_manual_publish_asks_and_waits_for_it(), test_collect_flow_writes_html_and_updates_status(), test_collect_range_is_editable_and_saved(), test_collect_refuses_out_of_scope_devices(), test_collect_refuses_without_devices(), test_device_check_does_not_mark_the_list_unsaved(), test_gap_card_shows_missing_counts_and_fills_them() (+16 more)

### Community 18 - "Community 18"
Cohesion: 0.07
Nodes (30): cache_failures(), clamp_days(), _dev_name(), device_facts(), fetch_content(), file_path_of(), gather(), is_failure_record() (+22 more)

### Community 19 - "Community 19"
Cohesion: 0.08
Nodes (23): check_target(), device_links(), _devices_csv(), fake_payload(), file_url(), guide_page(), hammer(), hold_test() (+15 more)

### Community 20 - "Community 20"
Cohesion: 0.08
Nodes (50): addDays(), buildModel(), buildModelLegacy(), buildModelV3(), causeOf(), cmpDev(), devSortKey(), dk() (+42 more)

### Community 21 - "Community 21"
Cohesion: 0.07
Nodes (27): _age_text(), collect_kla(), merge(), p1(), p2(), p3(), p3p(), _fmt() (+19 more)

### Community 22 - "Community 22"
Cohesion: 0.06
Nodes (27): _assets_snapshot(), _fingerprint(), _load(), _on(), _package_assets_untouched(), test_build_paths_leave_the_package_folder_untouched(), test_default_temp_js_sits_next_to_the_template(), test_dev_requirements_declare_yaml_and_playwright_but_runtime_does_not() (+19 more)

### Community 23 - "Community 23"
Cohesion: 0.08
Nodes (24): _att(), _lot_keys(), _lot_pick(), _lot_screen(), test_lot_tab_cards_count_distinct_wafers_and_skip_test_errors(), test_lot_tab_counts_rows_it_cannot_group_and_duplicate_ids(), test_lot_tab_groups_by_wafer_id_not_by_name_and_follows_devices(), test_lot_tab_ignores_slot_ids_and_parses_kla_names() (+16 more)

### Community 24 - "Community 24"
Cohesion: 0.07
Nodes (30): _cache_device(), _carry_over(), _check(), newest_of(), read_again(), read_one(), read_raw(), _decode_report() (+22 more)

### Community 25 - "Community 25"
Cohesion: 0.07
Nodes (29): write_html(), make_cfg(), test_write_html_failure_keeps_the_previous_html(), test_csv_on_nas_is_refused_not_downgraded_to_a_warning(), test_csv_programming_error_is_not_swallowed(), test_write_html_embeds_data_and_mode(), test_write_html_embeds_timing_and_counts(), test_collect_writes_a_detailed_log_to_app_log_and_not_into_the_html() (+21 more)

### Community 26 - "Community 26"
Cohesion: 0.09
Nodes (22): collect_one(), copy_ini_for(), copy_report(), diagnose(), find_subdir(), list_folder(), lot_marks(), lot_parts() (+14 more)

### Community 27 - "Community 27"
Cohesion: 0.09
Nodes (43): behindAt(), calloutFit(), canAnim(), countUp(), deckSnap(), enterAnim(), enterView(), Flip() (+35 more)

### Community 28 - "Community 28"
Cohesion: 0.13
Nodes (32): at(), busy(), _card(), run(), test_a_wafer_crossing_midnight_is_split_between_the_two_days_and_counted_once(), test_an_untimed_error_takes_the_uncovered_minutes_of_its_batch_window(), test_collection_day_denominator_is_the_last_record_of_all_devices(), test_day_falls_back_to_the_last_data_day_when_the_collection_day_has_no_data() (+24 more)

### Community 29 - "Community 29"
Cohesion: 0.08
Nodes (25): _check_zip_entries(), _default_branch(), _describe_err(), _git_head(), _http_get(), _identity(), _is_ssl_verify_error(), latest_commit() (+17 more)

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (24): prefs_file(), load(), migrate(), _norm_dir(), patch(), Prefs, _preserve_broken(), save() (+16 more)

### Community 31 - "Community 31"
Cohesion: 0.09
Nodes (16): CollectorSignals, CollectorWorker, CollectResult, _publish_why(), _collect_signals(), test_csv_lock_completes_with_warnings_not_failed(), locked(), test_failure_is_reported_not_raised() (+8 more)

### Community 32 - "Community 32"
Cohesion: 0.08
Nodes (22): backup_cutoff(), dir_key(), same_dir(), scan_dirs_of(), with_dirs(), _case_insensitive_isdir(), _cfg(), _many_devices() (+14 more)

### Community 33 - "Community 33"
Cohesion: 0.09
Nodes (23): app_icon(), publish_lot(), _cfg(), _publish_cfg(), test_data_file_replace_retries_a_brief_lock_and_stale_tmp_goes_first(), test_full_and_lot_publish_do_not_touch_each_others_data(), test_local_html_does_not_retry_a_lock(), test_lot_only_file_can_be_limited_to_recent_days() (+15 more)

### Community 34 - "Community 34"
Cohesion: 0.09
Nodes (39): afterPaint(), applyDate(), bootPhase(), errorPanel(), goDay(), gunzip64(), init(), layoutPairLabels() (+31 more)

### Community 35 - "Community 35"
Cohesion: 0.17
Nodes (31): deps_blocked(), download_and_apply(), last_error(), _app(), _branch_zip(), _exe_install(), _fake_pip(), _serve() (+23 more)

### Community 36 - "Community 36"
Cohesion: 0.09
Nodes (38): avg(), crCell(), crSummary(), crTip(), f0(), f1(), famIndex(), famStem() (+30 more)

### Community 37 - "Community 37"
Cohesion: 0.07
Nodes (18): job_alias(), model_version(), rules(), section(), text(), _numbers(), test_decision_numbers_are_unique_and_unbroken(), test_hook_reads_the_korean_file_name_correctly() (+10 more)

### Community 38 - "Community 38"
Cohesion: 0.11
Nodes (8): P(), card2(), card(), fmt(), ok(), pick(), assemble(), install()

### Community 39 - "Community 39"
Cohesion: 0.09
Nodes (13): install_excepthook(), hook(), wait_orphan_threads(), setup_logging(), test_apply_env_sets_hidpi_and_no_webengine_flags(), test_ensure_deps_is_noop_in_dev_tree(), test_setup_logging_writes_to_data_root(), test_cli_and_gui_share_the_app_log_file() (+5 more)

### Community 40 - "Community 40"
Cohesion: 0.09
Nodes (22): test_fill_params_skips_a_wafer_folder_rewritten_by_a_later_scan(), _make_rdl(), rdl_all(), _rows(), test_multi_ignores_the_waferinfo_name_and_report_only_rows_stay_unknown(), test_multi_scan_reads_every_recipe_from_recipesinfo(), test_rdl_patch_reads_only_the_wafer_inis_of_rdl_rows_missing_the_mode(), test_rdl_wafer_that_stopped_before_recipesinfo_is_not_called_single() (+14 more)

### Community 41 - "Community 41"
Cohesion: 0.12
Nodes (22): plan_run(), RunPlan, as_old_cache(), test_plan_run_tells_when_a_rebuild_or_refresh_was_left_half_done(), _cache(), _sec_rows(), test_fill_gaps_fills_scan_ratio_from_wafer_folder_only_and_marks_reports(), test_fill_gaps_leaves_value_empty_when_folder_was_rewritten_later() (+14 more)

### Community 42 - "Community 42"
Cohesion: 0.09
Nodes (17): assert_local(), _drop_stale_tmp(), _ensure_lnk(), Kind, latest_text(), lnk_target(), make_lnk(), _pointed_name() (+9 more)

### Community 43 - "Community 43"
Cohesion: 0.10
Nodes (17): embedded(), load(), read_bytes(), sample_path(), sha256(), unfold(), test_compressed_publish_data_opens_and_save_copy_stays_compressed(), test_home_rows_follow_device_order_and_save_copy_refolds_the_same_columns() (+9 more)

### Community 44 - "Community 44"
Cohesion: 0.09
Nodes (8): _card(), _date_edit(), _GapRow, _label(), ModeCard, _repolish(), _row(), _tool()

### Community 45 - "Community 45"
Cohesion: 0.10
Nodes (19): f0(), f1(), grade(), img(), mainok(), mrow(), rec(), t2card() (+11 more)

### Community 46 - "Community 46"
Cohesion: 0.12
Nodes (23): make_device(), _cache_of(), _count_htm_reads(), spy(), _csv(), _fingerprint(), _raw(), _row() (+15 more)

### Community 47 - "Community 47"
Cohesion: 0.10
Nodes (14): globals_(), run_raw(), test_kla_tb500_job_names_are_shortened_for_display_only(), test_legacy_profile_equals_the_design_script_on_the_30_day_sample(), test_product_model_invariants_hold_on_the_30_day_sample(), test_unfold_rejects_out_of_range_pool_index_and_duplicate_columns(), test_extract_script_runs_on_the_product_sample(), test_js_classification_matches_python_and_the_fixture() (+6 more)

### Community 48 - "Community 48"
Cohesion: 0.11
Nodes (17): _found(), kla_name(), missed_in_scope(), _probe_auto(), allowed_keys(), allows_row(), describe(), is_allowed() (+9 more)

### Community 49 - "Community 49"
Cohesion: 0.08
Nodes (30): concurrency, cancel-in-progress, group, SHA, permissions, runs-on, steps, jobs (+22 more)

### Community 50 - "Community 50"
Cohesion: 0.07
Nodes (16): cache_status(), parse_recipe_settings(), _read_cache_text(), read_ini(), read_recipe_settings(), read_recipes_info(), _validate_cache_file(), decode_text() (+8 more)

### Community 51 - "Community 51"
Cohesion: 0.08
Nodes (16): _batch(), _clean_batches(), _hhmm(), test_recipe_lot_unit_verdict_shows_per_day_throughput_and_hour_labels(), test_report_popup_marks_slow_batches_by_time_per_wafer_not_by_batch_length(), test_report_tab_counts_a_batch_that_crosses_midnight_once(), test_report_tab_defect_is_the_per_wafer_median_with_the_mean_in_small_text(), test_report_tab_first_card_is_the_device_median_like_the_bars() (+8 more)

### Community 52 - "Community 52"
Cohesion: 0.11
Nodes (18): _cfg(), _cursor_of(), _embedded(), test_auto_row_finds_allowed_machines_without_listing_the_share(), test_auto_row_pointing_at_an_out_of_scope_machine_itself_is_blocked(), test_cli_run_stays_in_scope(), test_collect_entry_points_stay_in_scope(), test_display_name_rules() (+10 more)

### Community 53 - "Community 53"
Cohesion: 0.10
Nodes (17): collect(), test_corrupt_and_missing_cache_are_always_saved(), _cache_of(), _stop_after_reads(), test_cancel_before_any_read_leaves_cache_and_output_untouched(), stop(), test_cancel_still_works_while_reading_in_parallel(), test_on_device_callback_reports_states() (+9 more)

### Community 54 - "Community 54"
Cohesion: 0.11
Nodes (19): _embed_rows(), g(), test_embedded_rows_are_folded_into_a_string_pool(), _meta(), _open_rows_page(), rdl2_page(), rdl_page(), _rdl_rows() (+11 more)

### Community 55 - "Community 55"
Cohesion: 0.07
Nodes (11): test_boot_screen_runs_before_the_data_and_moves_on_the_compositor_only(), test_browser_never_reads_the_nas_itself(), test_light_only_theme(), test_links_to_new_tabs_have_no_opener(), test_no_network_use_at_all(), test_removed_features_stay_removed(), test_screen_terms_are_the_design_terms_and_old_ones_are_gone(), test_the_dialogs_have_accessible_names() (+3 more)

### Community 56 - "Community 56"
Cohesion: 0.13
Nodes (15): list_top(), lot_table(), main(), parse_result(), parse_ts(), pick_copies(), pick_lots(), read_head() (+7 more)

### Community 57 - "Community 57"
Cohesion: 0.08
Nodes (11): _fingerprint(), _report(), test_a_report_without_a_lot_never_lists_the_setup_folder(), test_device_roots_are_listed_near_the_top_of_the_file(), test_diagnose_points_at_an_unexpected_report_folder_name(), test_loadport_placeholder_is_not_taken_as_the_lot(), test_lot_suffix_split(), test_norm_root_fixes_bare_drive_letter() (+3 more)

### Community 58 - "Community 58"
Cohesion: 0.14
Nodes (17): _default_run(), deps_installed(), deps_marker(), ensure_deps(), pip_install_cmd(), req_fingerprint(), req_lines(), write_deps_marker() (+9 more)

### Community 59 - "Community 59"
Cohesion: 0.16
Nodes (16): copy_app_tree(), _copytree(), _default_branch_name(), _fetch_runtime(), _git_head(), _import_app_module(), _isolated(), missing_packages() (+8 more)

### Community 60 - "Community 60"
Cohesion: 0.08
Nodes (14): CollectCancelled, _list_all(), _list_new_reports(), one(), _needs_recovery(), RebuildRejected, report_name_patterns(), _run() (+6 more)

### Community 61 - "Community 61"
Cohesion: 0.17
Nodes (19): cache_file(), data_root(), default_devices_csv(), devices_csv_path(), _ensure_dir(), ensure_user_files(), install_root(), log_file() (+11 more)

### Community 62 - "Community 62"
Cohesion: 0.12
Nodes (14): _make_nas(), _report(), _snapshot(), test_all_never_exceeds_ten_zip_parts(), test_all_reads_every_lot_in_window_bundles_results_and_dedups_params_across_lots(), test_all_tops_up_sparse_jobs_from_older_lots(), put(), test_collects_read_only_dedups_and_splits() (+6 more)

### Community 63 - "Community 63"
Cohesion: 0.12
Nodes (16): allocate(), _ask(), _ask_int(), _ask_levels(), _ask_yes(), file_times(), _ft(), interactive() (+8 more)

### Community 64 - "Community 64"
Cohesion: 0.11
Nodes (15): _candidates(), _dedupe_sort(), device_id(), _dirs_of(), display_name(), _entry(), find_subdir(), is_floor4() (+7 more)

### Community 65 - "Community 65"
Cohesion: 0.17
Nodes (19): build_exe(), clean_stale_output(), _default_run(), _dir_size_mb(), _ensure_venv(), exe_out_dirname(), import_probe_cmd(), _load_portable_impl() (+11 more)

### Community 66 - "Community 66"
Cohesion: 0.08
Nodes (4): _DaysWorker, _GapFillWorker, _PlanWorker, _PublishWorker

### Community 67 - "Community 67"
Cohesion: 0.09
Nodes (14): ctx, fs, html, input, js, path, stub(), vm (+6 more)

### Community 68 - "Community 68"
Cohesion: 0.20
Nodes (15): _bundle(), _layout(), _marker(), _mk(), test_first_run_uses_the_console_python(), test_later_runs_are_windowless(), test_missing_console_python_falls_back_to_pythonw(), test_swap_applies_pending_update() (+7 more)

### Community 69 - "Community 69"
Cohesion: 0.10
Nodes (14): read_cache_file(), test_cache_rows_are_folded_on_disk_and_come_back_exactly(), test_corrupt_cache_is_preserved_as_bad_file_not_overwritten_silently(), test_reading_in_parallel_gives_exactly_the_same_result(), test_recover_targets_only_ini_states_that_can_come_back(), test_save_cache_validates_what_it_wrote_and_uses_a_unique_tmp(), test_worker_count_is_clamped_to_the_work_there_is(), nas() (+6 more)

### Community 70 - "Community 70"
Cohesion: 0.13
Nodes (14): _ansi(), _enabled(), error_kind(), _lnk_has(), _lnk_points_to(), publish_after_collect(), _run_one(), _same_folder() (+6 more)

### Community 71 - "Community 71"
Cohesion: 0.11
Nodes (8): isolated_data(), pytest_collection_modifyitems(), set_home(), shard_pick(), _It, test_shards_partition_all_tests_exactly(), test_issue_text_renders_known_codes_and_keeps_unknown_ones_raw(), test_render_issue_rows_fills_new_rows_only_and_never_mutates_or_touches_old_rows()

### Community 72 - "Community 72"
Cohesion: 0.18
Nodes (15): _add(), _cache(), _fake_lister(), _name_for(), _reports(), test_backfill_and_recover_always_list_everything(), test_full_listing_interval_defaults_to_seven_days_and_is_configurable(), age_full_listing() (+7 more)

### Community 73 - "Community 73"
Cohesion: 0.12
Nodes (12): bootCore(), loop(), S, bootScene(), assign(), build(), lotFrame(), waferLayout() (+4 more)

### Community 74 - "Community 74"
Cohesion: 0.19
Nodes (11): _attach_dirs(), devices_from_csv(), devices_from_rows(), discover_devices(), _discover_under(), _log(), _norm_root(), _pmap() (+3 more)

### Community 76 - "Community 76"
Cohesion: 0.16
Nodes (12): apply_to_app(), colors(), normalize_color_mode(), palettes(), parse_template_tokens(), render_qss(), set_color_mode(), styled_qapp() (+4 more)

### Community 77 - "Community 77"
Cohesion: 0.14
Nodes (4): SettingsPage, hrow(), pub_row(), NoWheelSpinBox

### Community 78 - "Community 78"
Cohesion: 0.12
Nodes (13): em(), pt(), bt(), bt(), flatten(), full(), num(), same() (+5 more)

### Community 79 - "Community 79"
Cohesion: 0.10
Nodes (13): fake_nas(), _no_startup_side_effects(), qapp(), _qt_app(), _no_real_subprocess(), fake_win(), scoped_nas(), fixture() (+5 more)

### Community 80 - "Community 80"
Cohesion: 0.12
Nodes (9): _fake_out(), _load(), test_run_build_lite_with_fakes(), test_verify_checks_pass_on_valid_lite_output(), test_verify_full_requires_packages_and_marker(), test_verify_lite_rejects_marker_and_internal(), test_verify_rejects_big_launcher_and_missing_template_placeholder(), test_version_stamp_json() (+1 more)

### Community 81 - "Community 81"
Cohesion: 0.14
Nodes (10): _launch(), page_factory(), test_tab_indicator_moves_like_a_body_dragged_by_its_front(), _fingerprint(), _load(), test_build_produces_one_closed_file_whose_logic_parses(), test_build_writes_only_where_it_is_told(), test_camel_attrs_are_encoded_only_in_markup_not_in_the_script() (+2 more)

### Community 82 - "Community 82"
Cohesion: 0.12
Nodes (12): categories(), find_subdir(), is_placeholder(), name_day(), norm_root(), read_bytes(), scan_dirs(), survey_device() (+4 more)

### Community 83 - "Community 83"
Cohesion: 0.14
Nodes (11): password_files(), read_credentials(), reconnect(), _remote_of(), _win_connect(), test_no_password_file_means_no_attempt(), test_not_windows_or_not_drive_letter_does_nothing(), test_out_of_scope_kla_row_never_reconnects() (+3 more)

### Community 84 - "Community 84"
Cohesion: 0.14
Nodes (15): scandir(), _list_files(), ms_since(), op_isdir(), op_isfile(), op_open_read(), op_os_read_once(), resolve_wafer() (+7 more)

### Community 85 - "Community 85"
Cohesion: 0.16
Nodes (10): candidates(), download_dirs(), load(), normalize(), _read(), _shell_downloads(), test_load_picks_the_latest_saved_among_data_folder_and_downloads(), test_normalize_drops_bad_and_duplicate_entries() (+2 more)

### Community 86 - "Community 86"
Cohesion: 0.15
Nodes (13): _bundled_python(), _discard(), _ensure_deps(), _file_text(), _install_root(), _move(), _pending_dir(), _promote_in_place() (+5 more)

### Community 87 - "Community 87"
Cohesion: 0.16
Nodes (9): build(), graphify_cmds(), inline_scripts(), main(), write_inline_js(), changed_files(), check(), is_code() (+1 more)

### Community 88 - "Community 88"
Cohesion: 0.14
Nodes (10): _no_input(), test_console_path_waits_for_enter(), test_ensure_deps_failure_notifies_with_log_path_and_returns_false(), test_input_failures_fall_back_without_raising(), test_notice_path_never_imports_pyqt6(), test_stdin_none_skips_input_and_prints_when_no_messagebox(), test_windows_uses_messagebox_when_stdin_is_none(), test_windows_without_windll_or_a_failing_box_prints_instead() (+2 more)

### Community 89 - "Community 89"
Cohesion: 0.21
Nodes (10): _q(), download(), git(), git_update(), is_git_repo(), main(), _opener(), repo_root() (+2 more)

### Community 90 - "Community 90"
Cohesion: 0.15
Nodes (9): unpack(), build(), embedded_text(), build(), bundle_template(), encode_camel_attrs(), main(), offline_variant() (+1 more)

### Community 91 - "Community 91"
Cohesion: 0.12
Nodes (3): eta(), eta_text(), Collapsible

### Community 92 - "Community 92"
Cohesion: 0.22
Nodes (13): _cfg(), _files(), _make_cache(), _meta_of(), test_one_button_opens_both_files_in_turn_and_collects_the_results(), browser(), test_one_button_stop_while_waiting(), test_one_button_without_a_download_asks_for_the_band_numbers() (+5 more)

### Community 93 - "Community 93"
Cohesion: 0.18
Nodes (12): _full(), local(), _make_zip(), _patch_download(), test_git_update_reports_already_up_to_date(), test_git_update_stops_when_working_tree_is_dirty(), fake_git(), test_main_uses_zip_when_folder_is_not_a_git_checkout() (+4 more)

### Community 94 - "Community 94"
Cohesion: 0.17
Nodes (10): _fold_rows(), _save_cache(), _unique_tmp(), _cfg(), _embedded(), _model(), test_a_chosen_period_draws_only_its_days_and_matches_the_whole_file(), test_default_html_is_the_last_html_days_of_the_data_in_one_file() (+2 more)

### Community 95 - "Community 95"
Cohesion: 0.16
Nodes (9): _stage_tree(), _verify_staged(), _write_version(), _write_version_to(), _fake_repo(), test_github_archive_contains_only_deploy_files(), test_staging_real_tree_passes_verification_and_top_level_equals_allow_list(), test_staging_top_level_equals_allow_list_even_with_junk_in_source_root() (+1 more)

### Community 96 - "Community 96"
Cohesion: 0.15
Nodes (9): _out_of_scope_meta(), ensure_camtek_rows(), ensure_kla_rows(), read_devices_csv(), write_devices_csv(), test_read_csv_cp949_and_utf8_and_aliases(), test_read_csv_without_header_and_comments(), test_write_then_read_roundtrip() (+1 more)

### Community 97 - "Community 97"
Cohesion: 0.18
Nodes (3): host_for(), SheetHost, _toggle()

### Community 98 - "Community 98"
Cohesion: 0.15
Nodes (9): _cache(), _picked(), test_bulk_listing_failure_falls_back_to_scandir(), test_file_growing_while_read_is_not_truncated(), test_full_listing_uses_the_bulk_lister_and_picks_the_same_reports(), test_ini_memo_classifies_missing_the_same(), test_os_open_in_nas_guard_is_read_only(), test_small_file_is_read_with_one_read_call() (+1 more)

### Community 99 - "Community 99"
Cohesion: 0.21
Nodes (16): log(), now_s(), progress(), _run(), run_cmd(), _run_level(), _run_real(), step() (+8 more)

### Community 100 - "Community 100"
Cohesion: 0.18
Nodes (9): default_root(), file_digest(), _lot_open_lines(), _one(), open_in_browser(), _remove(), render_summary(), _sec() (+1 more)

### Community 102 - "Community 102"
Cohesion: 0.17
Nodes (12): _bat(), test_cli_never_execs(), test_default_runner_uses_subprocess_run_and_propagates_returncode(), fake_run(), test_main_with_update_reruns_once_as_a_child_and_does_not_collect_in_the_parent(), test_main_without_a_new_version_collects_in_place(), test_rerun_without_update_waits_for_the_child_and_returns_its_exit_code(), fake_run() (+4 more)

### Community 103 - "Community 103"
Cohesion: 0.17
Nodes (10): _fail_move_when(), _loose_app(), _snapshot(), test_latest_self_healing_retries_default_branch(), fake(), test_promote_recovers_a_backup_left_by_an_earlier_failed_rollback(), test_promote_success_replaces_all_and_leaves_no_backups(), test_rollback_failure_keeps_backups_and_names_the_files() (+2 more)

### Community 104 - "Community 104"
Cohesion: 0.22
Nodes (7): collect_lot(), is_bundle(), pack_lot_all(), Packer, recipe_mode(), safe(), stamp()

### Community 105 - "Community 105"
Cohesion: 0.15
Nodes (9): _gzip64(), _build_html(), _embedded(), _fixture_rows(), _open_quiet(), page(), test_boot_screen_covers_four_seconds_then_reveals_the_real_screen(), test_brand_mark_has_no_tile_and_replays_every_10_seconds() (+1 more)

### Community 106 - "Community 106"
Cohesion: 0.22
Nodes (14): bringToFront(), closeTop(), h(), e(), f(), i(), s(), t() (+6 more)

### Community 107 - "Community 107"
Cohesion: 0.23
Nodes (6): _FakeBuild, _out(), _polluted(), test_no_zip_when_verification_fails(), test_polluted_dist_ships_no_cache_log_or_backup_but_keeps_runtime(), test_zip_layout_and_instructions()

### Community 108 - "Community 108"
Cohesion: 0.16
Nodes (7): check_rows(), probe(), probe(), _has_report(), _is_kla_root(), _CheckWorker, test_check_rows_reports_out_of_scope_without_touching()

### Community 110 - "Community 110"
Cohesion: 0.19
Nodes (8): _app_root(), check_for_update(), current_version(), ensure_version_file(), _git_head_ref(), is_git_checkout(), _version_file(), test_current_version_prefers_git_head_over_a_stale_version_file()

### Community 111 - "Community 111"
Cohesion: 0.22
Nodes (9): _call_name(), _enclosing_function(), _snapshot(), test_assert_local_and_check_cfg(), test_nas_guard_module_has_no_write_helpers(), test_publish_module_writes_only_in_guarded_functions(), test_static_every_write_function_guards_first(), test_static_write_calls_only_in_allowed_functions() (+1 more)

### Community 112 - "Community 112"
Cohesion: 0.20
Nodes (8): resolver(), _dns(), _snapshot(), test_other_share_on_same_server_is_allowed_but_noted(), test_read_devices_and_links(), test_refuses_under_device_root_and_same_share_in_any_spelling(), test_run_stops_without_devices_csv_unless_told(), test_run_writes_only_inside_probe_dir_and_clean_removes_only_own_files()

### Community 113 - "Community 113"
Cohesion: 0.22
Nodes (8): decode(), decrypt_bytes(), _enc_secret(), encrypt_bytes(), _keystream(), main(), parse_args(), say()

### Community 114 - "Community 114"
Cohesion: 0.22
Nodes (6): app_paths(), _error(), launch_cmd(), Layout, main(), swap_pending()

### Community 115 - "Community 115"
Cohesion: 0.15
Nodes (6): _jobs(), _lot_open_result(), _make_dir(), _move(), run(), _write_text()

### Community 116 - "Community 116"
Cohesion: 0.19
Nodes (7): wait_download(), _Clock, _result(), stop(), test_wait_download_finds_the_tokened_file_and_skips_others(), sleep(), test_wait_download_times_out_and_stops()

### Community 117 - "Community 117"
Cohesion: 0.26
Nodes (11): _ci_gate(), _is_full_sha(), _run(), _runs(), _serve_runs(), test_atom_fallback_and_error_recording(), fake_get(), test_ci_gate_holds_on_pending_failed_or_missing() (+3 more)

### Community 118 - "Community 118"
Cohesion: 0.19
Nodes (6): content_sha(), entries(), test_every_archived_file_matches_its_original_fingerprint(), test_everything_under_archive_is_listed(), test_manifest_has_entries_and_no_duplicates(), test_no_compiled_python_is_tracked()

### Community 119 - "Community 119"
Cohesion: 0.21
Nodes (3): Deadline, OpRecorder, real_collect_runs()

### Community 120 - "Community 120"
Cohesion: 0.26
Nodes (6): _decrypt(), import_zips(), man(), read(), _open_zips(), _wanted()

### Community 121 - "Community 121"
Cohesion: 0.26
Nodes (10): engineCore(), loop(), S, engineScene(), assign(), build(), makeLib(), curl() (+2 more)

### Community 122 - "Community 122"
Cohesion: 0.30
Nodes (8): collect_files(), instructions_text(), _load_build_module(), main(), make_zip(), read_version(), should_include(), zip_basename()

### Community 123 - "Community 123"
Cohesion: 0.27
Nodes (9): pick(), run(), collect_one(), done_ok(), limit_reached(), run_all(), run_wide(), take() (+1 more)

### Community 125 - "Community 125"
Cohesion: 0.33
Nodes (11): navBox(), navCancel(), navGo(), navInd(), navNow(), navParts(), navRest(), navSet() (+3 more)

### Community 126 - "Community 126"
Cohesion: 0.18
Nodes (6): deps_changed(), _gate_info(), manual_check(), test_manual_check_reports_tls_failure(), test_ssl_verify_failure_stops_check_with_reason_and_no_retry(), _VerifyFailOpener

### Community 127 - "Community 127"
Cohesion: 0.24
Nodes (3): _c(), ProgressStrip, _PulseDot

### Community 129 - "Community 129"
Cohesion: 0.25
Nodes (5): _git(), _load(), test_check_requires_the_doc_only_when_code_changed(), test_code_paths_match_the_opt_in_hook(), test_main_looks_at_the_merge_base_range_not_only_the_last_commit()

### Community 130 - "Community 130"
Cohesion: 0.29
Nodes (5): main(), measure(), old_write_html(), rss_mb(), timed()

### Community 131 - "Community 131"
Cohesion: 0.18
Nodes (10): env, PIP_DISABLE_PIP_VERSION_CHECK, jobs, progress-doc, name, permissions, contents, if (+2 more)

### Community 132 - "Community 132"
Cohesion: 0.29
Nodes (11): steps, steps, AOI_SHARD, QT_QPA_PLATFORM, steps, env, id, name (+3 more)

### Community 133 - "Community 133"
Cohesion: 0.22
Nodes (9): analyze(), _diff(), dist(), _dt_of(), med_ci(), parse_ini_bytes(), pct(), stage_times() (+1 more)

### Community 134 - "Community 134"
Cohesion: 0.20
Nodes (5): is_under(), normalize(), test_device_index_exact_hits_and_legacy_path_fallback_agree_with_linear_search(), linear(), test_is_under_windows_semantics()

### Community 135 - "Community 135"
Cohesion: 0.24
Nodes (5): _emb_json(), _payload(), _payload_join(), _old_embed(), test_embed_and_payload_match_the_old_copy_then_fold_then_dump()

### Community 136 - "Community 136"
Cohesion: 0.20
Nodes (6): expand_roots(), roots_for_cfg(), _share_root(), _unc_for_drive(), test_expand_roots_adds_share_root_for_unc(), test_roots_for_cfg_reads_every_row_even_disabled()

### Community 137 - "Community 137"
Cohesion: 0.20
Nodes (6): NasWriteRefused, publish_full(), test_full_publish_has_every_tab_ninety_days_and_its_own_files(), test_full_publish_refuses_a_folder_under_an_equipment_nas(), test_publish_error_kind_names_the_reason(), __init__()

### Community 138 - "Community 138"
Cohesion: 0.20
Nodes (5): raw_stub_url(), shortcut_bytes(), shortcut_text(), stub_url(), write_shortcut()

### Community 140 - "Community 140"
Cohesion: 0.22
Nodes (3): check(), Stopped, PerfTestWorker

### Community 141 - "Community 141"
Cohesion: 0.25
Nodes (5): ensure_html(), exists(), html_path(), last_collect_time(), test_ensure_html_creates_openable_file_without_collecting()

### Community 142 - "Community 142"
Cohesion: 0.28
Nodes (3): tripwire(), wrap(), Tripwire

### Community 143 - "Community 143"
Cohesion: 0.25
Nodes (9): name, runs-on, strategy, timeout-minutes, strategy, browser, shard, fail-fast (+1 more)

### Community 144 - "Community 144"
Cohesion: 0.25
Nodes (3): find_pattern(), FoundEntry, _Stat

### Community 145 - "Community 145"
Cohesion: 0.54
Nodes (6): _example(), _public(), test_every_default_config_key_is_in_the_example_or_explicitly_excused(), test_example_loads_through_the_cli_loader(), test_example_public_keys_are_a_subset_of_default_config_with_the_same_types(), test_example_scope_and_workers_show_the_real_defaults()

### Community 146 - "Community 146"
Cohesion: 0.39
Nodes (7): BAR_G, BARS_IDLE, barsColor(), barsCtl(), barsGeom(), barsListScene(), barsMake()

### Community 147 - "Community 147"
Cohesion: 0.25
Nodes (8): with, cache, cache-dependency-path, fetch-depth, key, node-version, path, python-version

### Community 150 - "Community 150"
Cohesion: 0.29
Nodes (3): LABELS, PW, TH

### Community 151 - "Community 151"
Cohesion: 0.29
Nodes (4): job_folder_variants(), lot_dir_of(), read_lot_all(), submit()

### Community 152 - "Community 152"
Cohesion: 0.33
Nodes (4): Ca(), Vb(), wb(), Xb()

### Community 154 - "Community 154"
Cohesion: 0.53
Nodes (3): _files(), _string_literals(), test_no_korean_string_literals_outside_i18n()

### Community 155 - "Community 155"
Cohesion: 0.33
Nodes (3): fake_run(), _Done, _Full

### Community 156 - "Community 156"
Cohesion: 0.33
Nodes (3): test_locked_cache_is_not_treated_as_corrupt(), locked(), test_save_failure_leaves_no_tmp_and_keeps_the_old_cache()

### Community 157 - "Community 157"
Cohesion: 0.53
Nodes (6): _extract(), test_safe_extract_accepts_github_layout_and_short_sha_root(), test_safe_extract_caps_file_count_and_total_size(), test_safe_extract_rejects_hostile_entries_without_writing(), test_safe_extract_rejects_symlinks(), _zip_of()

### Community 159 - "Community 159"
Cohesion: 0.33
Nodes (3): run_all.sh script, run_set.sh script, run_text.sh script

### Community 161 - "Community 161"
Cohesion: 0.40
Nodes (3): _lnk_current(), test_lnk_current_checks_the_icon_path(), test_lnk_current_checks_the_target_path()

### Community 162 - "Community 162"
Cohesion: 0.50
Nodes (5): Context(), Db(), Eb(), Et(), fb()

### Community 164 - "Community 164"
Cohesion: 0.40
Nodes (3): test_ini_memo_lets_concurrent_readers_share_one_open(), slow(), test_run_stops_fast_without_waiting_for_slow_reads()

### Community 166 - "Community 166"
Cohesion: 0.50
Nodes (4): name, runs-on, timeout-minutes, core

### Community 167 - "Community 167"
Cohesion: 0.50
Nodes (4): on, pull_request, push, branches

### Community 169 - "Community 169"
Cohesion: 0.67
Nodes (3): concurrency, cancel-in-progress, group

## Knowledge Gaps
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MainWindow` connect `Community 10` to `Community 97`, `Community 66`, `Community 39`, `Community 11`, `Community 75`, `Community 109`, `Community 15`, `Community 17`, `Community 18`, `Community 153`, `Community 31`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `collect()` (e.g. with `run()` and `test_zero_new_rows_but_state_change_still_saves()`) actually correct?**
  _`collect()` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.016823266219239373 - nodes in this community are weakly interconnected._
- **Why does `DeviceStrip` connect `Community 128` to `Community 139`, `Community 127`, `Community 15`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05789473684210526 - nodes in this community are weakly interconnected._
- **Why does `make_cfg()` connect `Community 25` to `Community 5`, `Community 7`, `Community 14`, `Community 17`, `Community 18`, `Community 23`, `Community 156`, `Community 31`, `Community 32`, `Community 39`, `Community 40`, `Community 41`, `Community 46`, `Community 52`, `Community 53`, `Community 69`, `Community 71`, `Community 72`, `Community 74`, `Community 83`, `Community 98`, `Community 111`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.03163503163503163 - nodes in this community are weakly interconnected._