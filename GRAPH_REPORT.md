# Graph Report - AOI-capacity  (2026-11-04)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 3982 nodes · 9722 edges · 182 communities (132 shown, 50 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 470 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `02803677`
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
- Community 141
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

## God Nodes (most connected - your core abstractions)
1. `make_cfg()` - 123 edges
2. `collect()` - 95 edges
3. `w()` - 58 edges
4. `_collect()` - 56 edges
5. `CollectPage` - 54 edges
6. `write_html()` - 52 edges
7. `MainWindow` - 49 edges
8. `rows_for_report()` - 48 edges
9. `h()` - 45 edges
10. `meta()` - 41 edges

## Surprising Connections (you probably didn't know these)
- `_emit()` --calls--> `progress()`  [INFERRED]
  aoi_capacity/utils/updater.py → test.py
- `run()` --calls--> `log()`  [INFERRED]
  scripts/internal/portable_build.py → test.py
- `fake_run()` --calls--> `_Done`  [INFERRED]
  dev/tests/test_cli_update_rerun.py → scripts/collect_wafer_logs.py
- `fake_run()` --calls--> `_Done`  [INFERRED]
  dev/tests/test_cli_update_rerun.py → scripts/collect_wafer_logs.py
- `test_update_recheck_runs_every_30_minutes_and_skips_when_busy()` --uses--> `MainWindow`  [INFERRED]
  dev/tests/test_ui_smoke.py → aoi_capacity/ui/main_window.py

## Import Cycles
- 3-file cycle: `aoi_capacity/devices.py -> aoi_capacity/kla_drives.py -> aoi_capacity/utils/paths.py -> aoi_capacity/devices.py`

## Communities (182 total, 50 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (108): ALL_TABS, B(), barsColor(), barsCtl(), barsGeom(), barsListScene(), barsMake(), byLayer() (+100 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (42): em(), category(), family(), pt(), q(), q(), lotcore(), q() (+34 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (15): CollectPage, eta(), _days_text(), _DaysWorker, eta_text(), _GapFillWorker, _HtmlOnlyWorker, _LotPublishWorker (+7 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (83): _a(), Ae(), Ao(), _assertThisInitialized(), Ba(), be(), bt(), cc() (+75 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (6): make_button(), set_role(), NoWheelSpinBox, parse_int(), test_ensure_deps_is_noop_in_dev_tree(), test_setup_logging_writes_to_data_root()

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (43): categories(), collect_lot(), decode(), decrypt_bytes(), _enc_secret(), encrypt_bytes(), find_subdir(), _Full (+35 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (15): dur_text(), MainWindow, _UpdateSignals, _UpdateWorker, _left_text(), NavBar, _repolish(), ask() (+7 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (29): job_alias(), model_version(), rules(), section(), text(), _numbers(), test_decision_numbers_are_unique_and_unbroken(), test_hook_reads_the_korean_file_name_correctly() (+21 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (36): _IniMemo, issue_text(), parse_report(), rows_for_report(), split_job_setup(), _backup_ini(), _live_ini(), test_batch_row_lot_is_never_the_loadport_placeholder() (+28 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (29): _assign_device_keys(), _cache_device(), merge(), _DeviceIndex, _Dirty, fill_gaps(), fill_params(), _fill_params_into() (+21 more)

### Community 10 - "Community 10"
Cohesion: 0.06
Nodes (34): _add_report(), _cache_of(), _count_nas_reads(), count(), spy(), spy_bytes(), _dev_dir(), _entry_fp() (+26 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (29): _cache_summary(), cached_days(), _collect_log(), _entry_sort_stamp(), estimate_run_sec(), estimate_sec(), failed_batch_row(), _first_day() (+21 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (32): load_config(), ConfigError, dashboard_settings(), fatal(), is_single_name(), normalize_config(), parse_bool(), Problem (+24 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (23): check_target(), device_links(), _devices_csv(), fake_payload(), file_url(), guide_page(), hammer(), hold_test() (+15 more)

### Community 14 - "Community 14"
Cohesion: 0.07
Nodes (29): cache_failures(), clamp_days(), _dev_name(), device_facts(), fetch_content(), file_path_of(), gather(), is_failure_record() (+21 more)

### Community 15 - "Community 15"
Cohesion: 0.06
Nodes (11): _card(), _date_edit(), _GapRow, _label(), ModeCard, _repolish(), _row(), _tool() (+3 more)

### Community 16 - "Community 16"
Cohesion: 0.07
Nodes (33): _payload(), range_name(), _utf8_len(), write_html(), make_cfg(), test_write_html_failure_keeps_the_previous_html(), _lock_replace_for(), _run() (+25 more)

### Community 17 - "Community 17"
Cohesion: 0.08
Nodes (49): barsHtml(), calloutW(), clock(), cnt(), collectChip(), cut(), dateControlsHtml(), dayBasis() (+41 more)

### Community 18 - "Community 18"
Cohesion: 0.07
Nodes (27): _lot_rows(), meta(), _okw(), _rdl(), screen(), test_dashboard_settings_override_the_attention_thresholds(), test_error_popup_shows_each_types_own_phrase_when_one_lot_has_two_types(), test_error_tab_leaves_kla_out() (+19 more)

### Community 19 - "Community 19"
Cohesion: 0.07
Nodes (30): _batch_from_rows(), cause_field(), _first(), _is_error_row(), _is_placeholder(), is_unmapped_status(), issue_field(), _job_setup_by_table_lot() (+22 more)

### Community 20 - "Community 20"
Cohesion: 0.08
Nodes (47): avg(), crCell(), crSummary(), crTip(), exFam(), f0(), f1(), famIndex() (+39 more)

### Community 21 - "Community 21"
Cohesion: 0.06
Nodes (20): build(), embedded_text(), boot_js(), assemble(), install(), build(), bundle_template(), encode_camel_attrs() (+12 more)

### Community 22 - "Community 22"
Cohesion: 0.06
Nodes (27): _assets_snapshot(), _fingerprint(), _load(), _on(), _package_assets_untouched(), test_build_paths_leave_the_package_folder_untouched(), test_default_temp_js_sits_next_to_the_template(), test_dev_requirements_declare_yaml_and_playwright_but_runtime_does_not() (+19 more)

### Community 23 - "Community 23"
Cohesion: 0.08
Nodes (25): _age_text(), collect_kla(), merge(), p1(), p2(), p3(), _fmt(), _is_scanning_lock() (+17 more)

### Community 24 - "Community 24"
Cohesion: 0.09
Nodes (22): collect_one(), copy_ini_for(), copy_report(), diagnose(), find_subdir(), list_folder(), lot_marks(), lot_parts() (+14 more)

### Community 25 - "Community 25"
Cohesion: 0.07
Nodes (6): _c(), DeviceStrip, LoadingOverlay, ProgressStrip, _PulseDot, _state_label()

### Community 26 - "Community 26"
Cohesion: 0.09
Nodes (30): _ci_gate(), _is_full_sha(), _extract(), _fail_move_when(), _loose_app(), _run(), _runs(), _serve_runs() (+22 more)

### Community 27 - "Community 27"
Cohesion: 0.08
Nodes (27): setup_logging(), cache_file(), data_root(), default_devices_csv(), devices_csv_path(), _ensure_dir(), ensure_user_files(), install_root() (+19 more)

### Community 28 - "Community 28"
Cohesion: 0.07
Nodes (28): _check(), read_one(), CollectCancelled, _decode_report(), one(), wrapped(), one(), one() (+20 more)

### Community 29 - "Community 29"
Cohesion: 0.09
Nodes (41): behindAt(), calloutFit(), canAnim(), countUp(), deckSnap(), enterAnim(), enterView(), Flip() (+33 more)

### Community 30 - "Community 30"
Cohesion: 0.08
Nodes (19): test_card_remembers_days_runs_and_blocks_collect(), _pump(), test_collect_flow_writes_html_and_updates_status(), test_collect_range_is_editable_and_saved(), test_collect_refuses_out_of_scope_devices(), test_collect_refuses_without_devices(), test_gap_card_shows_missing_counts_and_fills_them(), test_html_days_is_editable_and_reaches_the_collect_cfg() (+11 more)

### Community 31 - "Community 31"
Cohesion: 0.09
Nodes (23): _check_zip_entries(), _default_branch(), _describe_err(), _http_get(), _is_ssl_verify_error(), latest_commit(), _latest_self_healing(), _latest_via_api() (+15 more)

### Community 32 - "Community 32"
Cohesion: 0.10
Nodes (17): list_top(), lot_table(), main(), parse_result(), parse_ts(), pick_copies(), pick_lots(), read_head() (+9 more)

### Community 33 - "Community 33"
Cohesion: 0.09
Nodes (25): is_recipe_tab_job(), scan_seconds(), test_fill_params_reads_only_wafer_folders_of_reports_without_snapshots(), test_import_zips_resolves_references_and_skips_out_of_scope(), _zip(), _make_rdl(), _rows(), test_multi_ignores_the_waferinfo_name_and_report_only_rows_stay_unknown() (+17 more)

### Community 34 - "Community 34"
Cohesion: 0.09
Nodes (23): prefs_file(), load(), migrate(), _norm_dir(), patch(), Prefs, save(), test_apply_env_sets_hidpi_and_no_webengine_flags() (+15 more)

### Community 35 - "Community 35"
Cohesion: 0.17
Nodes (28): at(), busy(), run(), test_a_wafer_crossing_midnight_is_split_between_the_two_days_and_counted_once(), test_an_untimed_error_takes_the_uncovered_minutes_of_its_batch_window(), test_collection_day_denominator_is_the_last_record_of_all_devices(), test_day_falls_back_to_the_last_data_day_when_the_collection_day_has_no_data(), test_default_profile_is_product_with_the_four_rules_on_and_constants_match() (+20 more)

### Community 36 - "Community 36"
Cohesion: 0.08
Nodes (17): backup_cutoff(), _candidates(), device_id(), dir_key(), _dirs_of(), display_name(), _entry(), find_subdir() (+9 more)

### Community 37 - "Community 37"
Cohesion: 0.10
Nodes (34): addDays(), buildModel(), buildModelLegacy(), buildModelV3(), causeOf(), causeText(), cmpDev(), devSortKey() (+26 more)

### Community 38 - "Community 38"
Cohesion: 0.09
Nodes (19): _cam_by_key(), _Counter, _drive_host(), _fill_kla_images_into(), checkpoint(), _fill_scan_sec_into(), apply(), checkpoint() (+11 more)

### Community 39 - "Community 39"
Cohesion: 0.11
Nodes (21): NasWriteRefused, publish_lot(), _cfg(), _publish_cfg(), test_full_and_lot_publish_do_not_touch_each_others_data(), test_full_publish_has_every_tab_ninety_days_and_its_own_files(), test_full_publish_refuses_a_folder_under_an_equipment_nas(), test_lot_shortcut_is_named_aoi_lot_and_the_old_named_file_is_removed() (+13 more)

### Community 40 - "Community 40"
Cohesion: 0.11
Nodes (33): applySettings(), bootPhase(), bringToFront(), closeTop(), errorPanel(), goDay(), init(), loadDemo() (+25 more)

### Community 41 - "Community 41"
Cohesion: 0.07
Nodes (18): _advance_cursor(), _collect(), advance_finished(), checkpoint(), flush_read(), save_partial(), _empty_cache(), _load_resume() (+10 more)

### Community 42 - "Community 42"
Cohesion: 0.08
Nodes (19): collect(), test_corrupt_and_missing_cache_are_always_saved(), test_cancel_before_any_read_leaves_cache_and_output_untouched(), stop(), test_cancel_still_works_while_reading_in_parallel(), test_on_device_callback_reports_states(), test_collect_fixes_performance_values_instead_of_failing(), test_collect_with_bad_scope_raises_before_any_nas_call_and_writes_nothing() (+11 more)

### Community 43 - "Community 43"
Cohesion: 0.11
Nodes (16): embedded(), load(), read_bytes(), sample_path(), sha256(), unfold(), test_home_rows_follow_device_order_and_save_copy_refolds_the_same_columns(), test_recipe_groups_apply_at_once_persist_in_browser_and_export() (+8 more)

### Community 44 - "Community 44"
Cohesion: 0.12
Nodes (22): _cache_of(), _count_htm_reads(), spy(), _csv(), _fingerprint(), _raw(), _row(), _same_mtime() (+14 more)

### Community 45 - "Community 45"
Cohesion: 0.08
Nodes (30): concurrency, cancel-in-progress, group, SHA, permissions, runs-on, steps, jobs (+22 more)

### Community 46 - "Community 46"
Cohesion: 0.11
Nodes (19): _cfg(), _cursor_of(), _embedded(), test_auto_row_finds_allowed_machines_without_listing_the_share(), test_check_rows_reports_out_of_scope_without_touching(), test_cli_run_stays_in_scope(), test_collect_entry_points_stay_in_scope(), test_display_name_rules() (+11 more)

### Community 47 - "Community 47"
Cohesion: 0.10
Nodes (17): check_rows(), probe(), probe(), _has_report(), _is_kla_root(), _probe_auto(), password_files(), read_credentials() (+9 more)

### Community 48 - "Community 48"
Cohesion: 0.11
Nodes (19): _pool_size(), with_dirs(), make_device(), _case_insensitive_isdir(), _cfg(), _many_devices(), _snapshot(), test_backup_cutoff_reads_every_folder_name_seen_on_30_machines() (+11 more)

### Community 49 - "Community 49"
Cohesion: 0.22
Nodes (26): deps_blocked(), download_and_apply(), _emit(), last_error(), _app(), _branch_zip(), _exe_install(), _fake_pip() (+18 more)

### Community 50 - "Community 50"
Cohesion: 0.08
Nodes (11): _fingerprint(), _report(), test_a_report_without_a_lot_never_lists_the_setup_folder(), test_device_roots_are_listed_near_the_top_of_the_file(), test_diagnose_points_at_an_unexpected_report_folder_name(), test_loadport_placeholder_is_not_taken_as_the_lot(), test_lot_suffix_split(), test_norm_root_fixes_bare_drive_letter() (+3 more)

### Community 51 - "Community 51"
Cohesion: 0.10
Nodes (14): _fingerprint(), _load(), test_build_produces_one_closed_file_whose_logic_parses(), test_build_writes_only_where_it_is_told(), test_camel_attrs_are_encoded_only_in_markup_not_in_the_script(), test_offline_variant_waits_for_window_data_instead_of_fetching(), _tracked_design_files_untouched(), resolver() (+6 more)

### Community 52 - "Community 52"
Cohesion: 0.12
Nodes (20): main(), _print(), _progress_printer(), cb(), rerun_args(), rerun_without_update(), _bat(), test_default_runner_uses_subprocess_run_and_propagates_returncode() (+12 more)

### Community 53 - "Community 53"
Cohesion: 0.09
Nodes (17): _backup_roots(), _carry_over(), newest_of(), _entry_newest(), one(), ini_roots_for(), job_folder_variants(), parse_dt() (+9 more)

### Community 54 - "Community 54"
Cohesion: 0.12
Nodes (16): _is_stable_key(), _rows_from_cache(), kla_name(), missed_in_scope(), allowed_keys(), allows_row(), describe(), is_allowed() (+8 more)

### Community 55 - "Community 55"
Cohesion: 0.16
Nodes (17): copy_app_tree(), _copytree(), _default_branch_name(), _fetch_runtime(), _git_head(), _import_app_module(), _isolated(), missing_packages() (+9 more)

### Community 56 - "Community 56"
Cohesion: 0.08
Nodes (15): cache_status(), read_ini(), read_recipe_settings(), read_recipes_info(), _validate_cache_file(), _read_all(), read_bytes(), read_text() (+7 more)

### Community 57 - "Community 57"
Cohesion: 0.08
Nodes (15): fake_nas(), _no_startup_side_effects(), qapp(), _qt_app(), _no_real_subprocess(), fake_win(), rdl_all(), scoped_nas() (+7 more)

### Community 58 - "Community 58"
Cohesion: 0.12
Nodes (14): _make_nas(), _report(), _snapshot(), test_all_never_exceeds_ten_zip_parts(), test_all_reads_every_lot_in_window_bundles_results_and_dedups_params_across_lots(), test_all_tops_up_sparse_jobs_from_older_lots(), put(), test_collects_read_only_dedups_and_splits() (+6 more)

### Community 59 - "Community 59"
Cohesion: 0.10
Nodes (13): _ansi(), _ensure_lnk(), Kind, _lnk_current(), lnk_target(), make_lnk(), _prune(), raw_stub_url() (+5 more)

### Community 61 - "Community 61"
Cohesion: 0.17
Nodes (19): build_exe(), clean_stale_output(), _default_run(), _dir_size_mb(), _ensure_venv(), exe_out_dirname(), import_probe_cmd(), _load_portable_impl() (+11 more)

### Community 62 - "Community 62"
Cohesion: 0.14
Nodes (16): deps_installed(), deps_marker(), ensure_deps(), pip_install_cmd(), req_fingerprint(), req_lines(), write_deps_marker(), _root() (+8 more)

### Community 63 - "Community 63"
Cohesion: 0.12
Nodes (12): plan_run(), RunPlan, test_plan_run_never_rederives_rows_and_memoizes_by_file_stamp(), _cache(), _sec_rows(), test_fill_gaps_fills_scan_ratio_from_wafer_folder_only_and_marks_reports(), test_fill_gaps_leaves_value_empty_when_folder_was_rewritten_later(), test_fill_gaps_stop_keeps_what_was_read() (+4 more)

### Community 64 - "Community 64"
Cohesion: 0.09
Nodes (14): ctx, fs, html, input, js, path, stub(), vm (+6 more)

### Community 65 - "Community 65"
Cohesion: 0.09
Nodes (8): _active(), test_device_popup_focus_inert_tab_trap_and_escape_return(), test_error_day_selection_matches_the_header_date(), test_error_popup_type_popup_trend_and_report_tab(), test_error_tab_period_popup_filters_and_no_total_link(), test_heavy_tab_indexes_are_built_in_idle_time_after_load(), test_recipe_group_of_multi_job_still_shows_single_on_the_same_row(), test_stackbar_stays_top_left_while_the_popup_scrolls_and_lot_panel_fades_in_once()

### Community 66 - "Community 66"
Cohesion: 0.20
Nodes (15): _bundle(), _layout(), _marker(), _mk(), test_first_run_uses_the_console_python(), test_later_runs_are_windowless(), test_missing_console_python_falls_back_to_pythonw(), test_swap_applies_pending_update() (+7 more)

### Community 67 - "Community 67"
Cohesion: 0.18
Nodes (12): _attach_dirs(), _dedupe_sort(), devices_from_csv(), devices_from_rows(), discover_devices(), _discover_under(), _log(), _norm_root() (+4 more)

### Community 68 - "Community 68"
Cohesion: 0.21
Nodes (11): CollectorWorker, _collect_signals(), test_csv_lock_completes_with_warnings_not_failed(), locked(), test_failure_is_reported_not_raised(), test_full_publish_result_reaches_the_done_result(), test_html_lock_is_still_reported_as_failure(), test_publish_result_reaches_the_done_result() (+3 more)

### Community 69 - "Community 69"
Cohesion: 0.16
Nodes (12): _lot_keys(), _lot_screen(), test_lot_tab_groups_by_wafer_id_not_by_name_and_follows_devices(), test_lot_tab_ignores_slot_ids_and_parses_kla_names(), test_lot_tab_matrix_cells_show_defect_counts(), test_lot_tab_merges_one_char_ocr_misreads_but_not_other_wafers(), test_lot_tab_never_merges_past_25_wafers_and_shows_cross_rows(), test_lot_tab_tags_retries_rescans_and_lists_every_wafer() (+4 more)

### Community 70 - "Community 70"
Cohesion: 0.12
Nodes (12): bootCore(), loop(), S, bootScene(), assign(), build(), lotFrame(), waferLayout() (+4 more)

### Community 71 - "Community 71"
Cohesion: 0.10
Nodes (11): params_for_range(), build_meta(), items_of(), _canon(), _every(), _file_items(), _group_of(), job_key() (+3 more)

### Community 72 - "Community 72"
Cohesion: 0.12
Nodes (9): _fake_out(), _load(), test_run_build_lite_with_fakes(), test_verify_checks_pass_on_valid_lite_output(), test_verify_full_requires_packages_and_marker(), test_verify_lite_rejects_marker_and_internal(), test_verify_rejects_big_launcher_and_missing_template_placeholder(), test_version_stamp_json() (+1 more)

### Community 73 - "Community 73"
Cohesion: 0.16
Nodes (18): log_seen(), cap(), allocate(), log(), now_s(), _run(), run_cmd(), _run_level() (+10 more)

### Community 74 - "Community 74"
Cohesion: 0.16
Nodes (10): _enabled(), latest_text(), _pointed_name(), _publish(), publish_after_collect(), publish_full(), _remove_legacy_shortcuts(), _run_one() (+2 more)

### Community 75 - "Community 75"
Cohesion: 0.17
Nodes (12): apply_to_app(), colors(), normalize_color_mode(), palettes(), parse_template_tokens(), render_qss(), set_color_mode(), styled_qapp() (+4 more)

### Community 76 - "Community 76"
Cohesion: 0.19
Nodes (14): _add(), _cache(), _fake_lister(), _name_for(), _reports(), test_backfill_and_refresh_always_list_everything(), test_full_listing_interval_defaults_to_seven_days_and_is_configurable(), age_full_listing() (+6 more)

### Community 77 - "Community 77"
Cohesion: 0.21
Nodes (10): _q(), download(), git(), git_update(), is_git_repo(), main(), _opener(), repo_root() (+2 more)

### Community 78 - "Community 78"
Cohesion: 0.15
Nodes (10): _write_csv(), assert_local(), check_cfg(), roots_for_cfg(), app_icon(), _remove_old_icon(), write_shortcut(), _write_text() (+2 more)

### Community 79 - "Community 79"
Cohesion: 0.14
Nodes (5): is_dark_mode(), host_for(), _native(), _scrim_color(), SheetHost

### Community 80 - "Community 80"
Cohesion: 0.18
Nodes (12): _full(), local(), _make_zip(), _patch_download(), test_git_update_reports_already_up_to_date(), test_git_update_stops_when_working_tree_is_dirty(), fake_git(), test_main_uses_zip_when_folder_is_not_a_git_checkout() (+4 more)

### Community 81 - "Community 81"
Cohesion: 0.16
Nodes (9): _stage_tree(), _verify_staged(), _write_version(), _write_version_to(), _fake_repo(), test_github_archive_contains_only_deploy_files(), test_staging_real_tree_passes_verification_and_top_level_equals_allow_list(), test_staging_top_level_equals_allow_list_even_with_junk_in_source_root() (+1 more)

### Community 82 - "Community 82"
Cohesion: 0.12
Nodes (9): expand_roots(), is_under(), normalize(), _share_root(), _unc_for_drive(), test_device_index_exact_hits_and_legacy_path_fallback_agree_with_linear_search(), linear(), test_expand_roots_adds_share_root_for_unc() (+1 more)

### Community 83 - "Community 83"
Cohesion: 0.15
Nodes (12): blob_key(), _ounion(), put(), recipe_names(), snapshot(), _meta(), _snap(), test_build_meta_majority_diff_every_label_zone_names_and_history() (+4 more)

### Community 84 - "Community 84"
Cohesion: 0.18
Nodes (10): _bundled_python(), _discard(), _ensure_deps(), _file_text(), _move(), _promote_in_place(), _remove(), _requirements_differ() (+2 more)

### Community 85 - "Community 85"
Cohesion: 0.15
Nodes (9): _clean_batches(), _hhmm(), test_report_tab_counts_a_batch_that_crosses_midnight_once(), test_report_tab_judges_time_per_wafer_within_each_device_not_across_the_fleet(), test_report_tab_keeps_batches_apart_when_the_report_name_is_empty(), test_report_tab_leaves_out_a_batch_whose_time_per_wafer_is_far_from_its_group(), test_report_tab_leaves_out_a_batch_whose_wafers_were_all_skipped(), test_report_tab_reads_dia_after_an_underscore() (+1 more)

### Community 86 - "Community 86"
Cohesion: 0.15
Nodes (9): _cache(), _picked(), test_bulk_listing_failure_falls_back_to_scandir(), test_file_growing_while_read_is_not_truncated(), test_full_listing_uses_the_bulk_lister_and_picks_the_same_reports(), test_ini_memo_classifies_missing_the_same(), test_os_open_in_nas_guard_is_read_only(), test_small_file_is_read_with_one_read_call() (+1 more)

### Community 87 - "Community 87"
Cohesion: 0.19
Nodes (10): f0(), f1(), grade(), img(), m(), mainok(), mrow(), rec() (+2 more)

### Community 88 - "Community 88"
Cohesion: 0.18
Nodes (9): _ask(), _ask_int(), _ask_levels(), _ask_yes(), interactive(), main(), _pause(), real_collect_summary() (+1 more)

### Community 89 - "Community 89"
Cohesion: 0.19
Nodes (8): candidates(), load(), normalize(), _read(), test_load_picks_the_latest_saved_among_data_folder_and_downloads(), test_normalize_drops_bad_and_duplicate_entries(), test_write_html_embeds_recipe_groups(), _w()

### Community 90 - "Community 90"
Cohesion: 0.15
Nodes (12): check_for_update(), deps_changed(), _gate_info(), _install_root(), manual_check(), _pending_dir(), update_pending(), test_check_and_manual_hold_when_ci_not_passed() (+4 more)

### Community 91 - "Community 91"
Cohesion: 0.17
Nodes (10): _app_root(), current_version(), ensure_version_file(), _git_head(), _git_head_ref(), _identity(), is_git_checkout(), _version_file() (+2 more)

### Community 92 - "Community 92"
Cohesion: 0.15
Nodes (8): _embed_rows(), test_embedded_rows_are_folded_into_a_string_pool(), _embedded(), _fixture_rows(), _meta(), test_boot_screen_covers_four_seconds_then_reveals_the_real_screen(), test_overkill_tab_lists_devices_and_lot_row_opens_lot_tracking_with_colored_cells(), test_param_tab_unpacks_a_job_on_demand_and_marks_differing_cells()

### Community 93 - "Community 93"
Cohesion: 0.19
Nodes (7): decode(), _keep(), normalize(), parse_ini(), parse_rtp(), prune_blobs(), _split_comment()

### Community 94 - "Community 94"
Cohesion: 0.15
Nodes (13): Aa(), Animation(), Ca(), Da(), ea(), la(), ma(), na() (+5 more)

### Community 95 - "Community 95"
Cohesion: 0.15
Nodes (10): _cli_config(), _count_report_reads(), spy(), test_cli_flags_and_exit_codes(), nas(), _cache_rows(), test_cache_keeps_codes_only_and_outputs_carry_the_sentence(), test_issue_text_renders_known_codes_and_keeps_unknown_ones_raw() (+2 more)

### Community 96 - "Community 96"
Cohesion: 0.23
Nodes (6): _FakeBuild, _out(), _polluted(), test_no_zip_when_verification_fails(), test_polluted_dist_ships_no_cache_log_or_backup_but_keeps_runtime(), test_zip_layout_and_instructions()

### Community 97 - "Community 97"
Cohesion: 0.20
Nodes (10): agg(), card(), cell(), fmt(), img(), load(), row(), scene_fps() (+2 more)

### Community 98 - "Community 98"
Cohesion: 0.15
Nodes (10): report_name_patterns(), file_times(), _ft(), _list_files(), op_find_exact(), op_getattr(), op_win_createfile_read(), list_one() (+2 more)

### Community 99 - "Community 99"
Cohesion: 0.18
Nodes (8): ensure_camtek_rows(), ensure_kla_rows(), read_devices_csv(), write_devices_csv(), test_read_csv_cp949_and_utf8_and_aliases(), test_read_csv_without_header_and_comments(), test_write_then_read_roundtrip(), test_existing_devices_csv_gets_the_eight_kla_rows_once()

### Community 100 - "Community 100"
Cohesion: 0.21
Nodes (6): _default_run(), test_extract_script_runs_on_the_product_sample(), git_sha(), main(), measure(), model_version()

### Community 101 - "Community 101"
Cohesion: 0.19
Nodes (6): isolated_data(), pytest_collection_modifyitems(), set_home(), shard_pick(), _It, test_shards_partition_all_tests_exactly()

### Community 102 - "Community 102"
Cohesion: 0.16
Nodes (9): _no_input(), test_console_path_waits_for_enter(), test_ensure_deps_failure_notifies_with_log_path_and_returns_false(), test_input_failures_fall_back_without_raising(), test_stdin_none_skips_input_and_prints_when_no_messagebox(), test_windows_uses_messagebox_when_stdin_is_none(), test_windows_without_windll_or_a_failing_box_prints_instead(), _message_box() (+1 more)

### Community 103 - "Community 103"
Cohesion: 0.22
Nodes (6): app_paths(), _error(), launch_cmd(), Layout, main(), swap_pending()

### Community 104 - "Community 104"
Cohesion: 0.23
Nodes (7): _call_name(), _enclosing_function(), _snapshot(), test_nas_guard_module_has_no_write_helpers(), test_publish_module_writes_only_in_guarded_functions(), test_static_every_write_function_guards_first(), test_static_write_calls_only_in_allowed_functions()

### Community 105 - "Community 105"
Cohesion: 0.19
Nodes (6): content_sha(), entries(), test_every_archived_file_matches_its_original_fingerprint(), test_everything_under_archive_is_listed(), test_manifest_has_entries_and_no_duplicates(), test_no_compiled_python_is_tracked()

### Community 106 - "Community 106"
Cohesion: 0.21
Nodes (3): Deadline, OpRecorder, real_collect_runs()

### Community 107 - "Community 107"
Cohesion: 0.21
Nodes (9): ms_since(), op_isdir(), op_isfile(), op_open_read(), op_os_read_once(), resolve_wafer(), stage_serial(), probe() (+1 more)

### Community 108 - "Community 108"
Cohesion: 0.26
Nodes (6): _decrypt(), import_zips(), man(), read(), _open_zips(), _wanted()

### Community 109 - "Community 109"
Cohesion: 0.26
Nodes (10): engineCore(), loop(), S, engineScene(), assign(), build(), makeLib(), curl() (+2 more)

### Community 110 - "Community 110"
Cohesion: 0.30
Nodes (8): collect_files(), instructions_text(), _load_build_module(), main(), make_zip(), read_version(), should_include(), zip_basename()

### Community 111 - "Community 111"
Cohesion: 0.33
Nodes (11): navBox(), navCancel(), navGo(), navInd(), navNow(), navParts(), navRest(), navSet() (+3 more)

### Community 112 - "Community 112"
Cohesion: 0.31
Nodes (7): _cfg(), _embedded(), _model(), test_a_chosen_period_draws_only_its_days_and_matches_the_whole_file(), test_default_html_is_the_last_html_days_of_the_data_in_one_file(), test_html_from_cache_needs_no_nas_and_keeps_report_paths(), test_rows_for_range_keeps_context_and_order()

### Community 113 - "Community 113"
Cohesion: 0.25
Nodes (5): _git(), _load(), test_check_requires_the_doc_only_when_code_changed(), test_code_paths_match_the_opt_in_hook(), test_main_looks_at_the_merge_base_range_not_only_the_last_commit()

### Community 114 - "Community 114"
Cohesion: 0.18
Nodes (10): env, PIP_DISABLE_PIP_VERSION_CHECK, jobs, progress-doc, name, permissions, contents, if (+2 more)

### Community 115 - "Community 115"
Cohesion: 0.29
Nodes (11): steps, steps, AOI_SHARD, QT_QPA_PLATFORM, steps, env, id, name (+3 more)

### Community 116 - "Community 116"
Cohesion: 0.22
Nodes (9): analyze(), _diff(), dist(), _dt_of(), med_ci(), parse_ini_bytes(), pct(), stage_times() (+1 more)

### Community 117 - "Community 117"
Cohesion: 0.27
Nodes (7): _open_rows_page(), rdl2_page(), rdl_page(), _rdl_rows(), add(), _row(), _ts()

### Community 118 - "Community 118"
Cohesion: 0.33
Nodes (5): build(), graphify_cmds(), inline_scripts(), main(), write_inline_js()

### Community 119 - "Community 119"
Cohesion: 0.22
Nodes (5): _open_recipe(), test_recipe_close_point_labels_do_not_overlap(), test_recipe_device_row_opens_popup_with_keyboard_and_row_stays_same_node(), test_recipe_how_summary_and_details_are_accessible(), test_recipe_no_match_clearly_identifies_retained_or_empty_detail()

### Community 120 - "Community 120"
Cohesion: 0.28
Nodes (3): tripwire(), wrap(), Tripwire

### Community 121 - "Community 121"
Cohesion: 0.25
Nodes (9): name, runs-on, strategy, timeout-minutes, strategy, browser, shard, fail-fast (+1 more)

### Community 122 - "Community 122"
Cohesion: 0.25
Nodes (3): find_pattern(), FoundEntry, _Stat

### Community 123 - "Community 123"
Cohesion: 0.25
Nodes (5): globals_(), run_raw(), test_kla_tb500_job_names_are_shortened_for_display_only(), test_unfold_rejects_out_of_range_pool_index_and_duplicate_columns(), ts()

### Community 124 - "Community 124"
Cohesion: 0.39
Nodes (7): BAR_G, BARS_IDLE, barsColor(), barsCtl(), barsGeom(), barsListScene(), barsMake()

### Community 125 - "Community 125"
Cohesion: 0.25
Nodes (8): with, cache, cache-dependency-path, fetch-depth, key, node-version, path, python-version

### Community 127 - "Community 127"
Cohesion: 0.29
Nodes (3): LABELS, PW, TH

### Community 128 - "Community 128"
Cohesion: 0.53
Nodes (3): _files(), _string_literals(), test_no_korean_string_literals_outside_i18n()

### Community 130 - "Community 130"
Cohesion: 0.33
Nodes (3): run_all.sh script, run_set.sh script, run_text.sh script

### Community 133 - "Community 133"
Cohesion: 0.40
Nodes (3): _build_html(), page(), test_brand_mark_has_no_tile_and_replays_every_10_seconds()

### Community 136 - "Community 136"
Cohesion: 0.50
Nodes (4): name, runs-on, timeout-minutes, core

### Community 137 - "Community 137"
Cohesion: 0.50
Nodes (4): on, pull_request, push, branches

### Community 141 - "Community 141"
Cohesion: 0.67
Nodes (3): concurrency, cancel-in-progress, group

## Knowledge Gaps
- **50 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CollectPage` connect `Community 2` to `Community 4`, `Community 6`, `Community 78`, `Community 15`, `Community 30`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `collect()` (e.g. with `test_zero_new_rows_but_state_change_still_saves()` and `test_main_with_update_reruns_once_as_a_child_and_does_not_collect_in_the_parent()`) actually correct?**
  _`collect()` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.015841907561652786 - nodes in this community are weakly interconnected._
- **Why does `_IniMemo` connect `Community 8` to `Community 38`, `Community 41`, `Community 11`, `Community 86`, `Community 56`, `Community 28`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.04247104247104247 - nodes in this community are weakly interconnected._
- **Why does `make_cfg()` connect `Community 16` to `Community 4`, `Community 10`, `Community 12`, `Community 14`, `Community 30`, `Community 33`, `Community 42`, `Community 44`, `Community 46`, `Community 47`, `Community 48`, `Community 63`, `Community 67`, `Community 68`, `Community 69`, `Community 76`, `Community 86`, `Community 95`, `Community 101`, `Community 104`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.03605015673981191 - nodes in this community are weakly interconnected._