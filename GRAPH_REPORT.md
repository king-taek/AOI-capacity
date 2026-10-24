# Graph Report - AOI-capacity  (2026-10-24)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 3741 nodes · 9330 edges · 153 communities (137 shown, 16 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 446 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9cf88298`
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
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149

## God Nodes (most connected - your core abstractions)
1. `make_cfg()` - 127 edges
2. `collect()` - 92 edges
3. `CollectPage` - 68 edges
4. `MainWindow` - 54 edges
5. `_collect()` - 54 edges
6. `w()` - 48 edges
7. `rows_for_report()` - 48 edges
8. `write_html()` - 47 edges
9. `h()` - 46 edges
10. `load()` - 44 edges

## Surprising Connections (you probably didn't know these)
- `_emit()` --calls--> `progress()`  [INFERRED]
  aoi_capacity/utils/updater.py → test.py
- `test_update_recheck_runs_every_30_minutes_and_skips_when_busy()` --uses--> `MainWindow`  [INFERRED]
  dev/tests/test_ui_smoke.py → aoi_capacity/ui/main_window.py
- `window()` --uses--> `MainWindow`  [INFERRED]
  dev/tests/test_ui_smoke.py → aoi_capacity/ui/main_window.py
- `test_ini_memo_classifies_missing_the_same()` --calls--> `_IniMemo`  [EXTRACTED]
  dev/tests/test_nas_read.py → aoi_capacity/collect.py
- `fake_run()` --calls--> `_Done`  [INFERRED]
  dev/tests/test_cli_update_rerun.py → scripts/collect_wafer_logs.py

## Import Cycles
- 3-file cycle: `aoi_capacity/devices.py -> aoi_capacity/kla_drives.py -> aoi_capacity/utils/paths.py -> aoi_capacity/devices.py`

## Communities (153 total, 16 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (94): Animation(), B(), byLayer(), CAUSE_CODES, CAUSE_RULES, CLOSE, cut(), Da() (+86 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (66): at(), busy(), _clean_batches(), globals_(), _hhmm(), _lot_keys(), _lot_rows(), _lot_screen() (+58 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (89): _a(), Aa(), Ae(), Ao(), _assertThisInitialized(), Ba(), be(), bt() (+81 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (36): em(), category(), family(), pt(), q(), q(), lotcore(), q() (+28 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (43): categories(), collect_lot(), decode(), decrypt_bytes(), _enc_secret(), encrypt_bytes(), find_subdir(), _Full (+35 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (42): ini_roots_for(), _IniMemo, issue_text(), job_folder_variants(), parse_report(), rows_for_report(), split_job_setup(), _backup_ini() (+34 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (46): make_cfg(), _add_report(), _count_nas_reads(), _dev_dir(), _entry_fp(), _entry_of(), _fingerprint(), _lock_replace_for() (+38 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (4): make_button(), set_role(), NoWheelSpinBox, test_render_issue_rows_fills_new_rows_only_and_never_mutates_or_touches_old_rows()

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (37): load_config(), assert_valid(), check_or_raise(), ConfigError, dashboard_settings(), fatal(), is_single_name(), normalize_config() (+29 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (58): barsHtml(), bringToFront(), calloutW(), clock(), closeTop(), cnt(), collectChip(), dateControlsHtml() (+50 more)

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (4): CollectPage, _days_text(), to_collect_cfg(), test_card_buttons_follow_the_running_job()

### Community 11 - "Community 11"
Cohesion: 0.07
Nodes (27): _assign_device_keys(), merge(), _Dirty, _empty_cache(), fill_gaps(), fill_params(), _fill_setup(), _fresh_key() (+19 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (33): _backup_roots(), _cache_summary(), _cam_by_key(), _check(), newest_of(), read_one(), _Counter, _decode_report() (+25 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (23): check_target(), device_links(), _devices_csv(), fake_payload(), file_url(), guide_page(), hammer(), hold_test() (+15 more)

### Community 14 - "Community 14"
Cohesion: 0.07
Nodes (30): _batch_from_rows(), cause_field(), _first(), _is_error_row(), _is_placeholder(), is_unmapped_status(), issue_field(), _job_setup_by_table_lot() (+22 more)

### Community 15 - "Community 15"
Cohesion: 0.04
Nodes (20): _active(), test_date_controls_keep_day_inside_the_visible_period(), test_device_popup_focus_inert_tab_trap_and_escape_return(), test_error_day_selection_matches_the_header_date(), test_error_lists_keep_rows_in_place_and_only_text_changes(), test_error_popup_type_popup_trend_and_report_tab(), test_error_tab_period_popup_filters_and_no_total_link(), test_floor_and_maker_filters_are_picked_separately() (+12 more)

### Community 16 - "Community 16"
Cohesion: 0.07
Nodes (22): test_card_remembers_days_runs_and_blocks_collect(), _pump(), test_collect_flow_writes_html_and_updates_status(), test_collect_range_is_editable_and_saved(), test_collect_refuses_out_of_scope_devices(), test_collect_refuses_without_devices(), test_gap_card_shows_missing_counts_and_fills_them(), test_html_days_is_editable_and_reaches_the_collect_cfg() (+14 more)

### Community 17 - "Community 17"
Cohesion: 0.07
Nodes (19): setup_logging(), test_apply_env_sets_hidpi_and_no_webengine_flags(), test_ensure_deps_is_noop_in_dev_tree(), test_setup_logging_writes_to_data_root(), test_cli_and_gui_share_the_app_log_file(), _no_input(), test_console_path_waits_for_enter(), test_ensure_deps_failure_notifies_with_log_path_and_returns_false() (+11 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (27): _assets_snapshot(), _fingerprint(), _load(), _on(), _package_assets_untouched(), test_build_paths_leave_the_package_folder_untouched(), test_default_temp_js_sits_next_to_the_template(), test_dev_requirements_declare_yaml_and_playwright_but_runtime_does_not() (+19 more)

### Community 19 - "Community 19"
Cohesion: 0.05
Nodes (24): _collect_log(), _entry_sort_stamp(), estimate_run_sec(), estimate_sec(), failed_batch_row(), is_recipe_tab_job(), _issue_dec(), _issue_enc() (+16 more)

### Community 20 - "Community 20"
Cohesion: 0.09
Nodes (22): collect_one(), copy_ini_for(), copy_report(), diagnose(), find_subdir(), list_folder(), lot_marks(), lot_parts() (+14 more)

### Community 21 - "Community 21"
Cohesion: 0.08
Nodes (42): avg(), crCell(), crSummary(), crTip(), exFam(), f0(), f1(), famIndex() (+34 more)

### Community 22 - "Community 22"
Cohesion: 0.08
Nodes (25): _check_zip_entries(), _default_branch(), _describe_err(), _git_head(), _http_get(), _identity(), _is_ssl_verify_error(), latest_commit() (+17 more)

### Community 23 - "Community 23"
Cohesion: 0.06
Nodes (17): job_alias(), model_version(), rules(), section(), text(), test_browser_never_reads_the_nas_itself(), test_light_only_theme(), test_links_to_new_tabs_have_no_opener() (+9 more)

### Community 24 - "Community 24"
Cohesion: 0.07
Nodes (11): _card(), _date_edit(), _GapRow, _label(), ModeCard, _repolish(), _row(), _tool() (+3 more)

### Community 25 - "Community 25"
Cohesion: 0.09
Nodes (40): behindAt(), calloutFit(), canAnim(), countUp(), deckSnap(), enterAnim(), enterView(), Flip() (+32 more)

### Community 26 - "Community 26"
Cohesion: 0.08
Nodes (18): SettingsPage, prefs_file(), load(), migrate(), patch(), Prefs, save(), test_prefs_from_dict_keeps_good_fields_and_never_resets_scope_for_a_bad_version() (+10 more)

### Community 27 - "Community 27"
Cohesion: 0.10
Nodes (17): list_top(), lot_table(), main(), parse_result(), parse_ts(), pick_copies(), pick_lots(), read_head() (+9 more)

### Community 28 - "Community 28"
Cohesion: 0.17
Nodes (32): deps_blocked(), download_and_apply(), _emit(), last_error(), _app(), _branch_zip(), _exe_install(), _fake_pip() (+24 more)

### Community 29 - "Community 29"
Cohesion: 0.10
Nodes (25): make_device(), _cache_of(), _count_htm_reads(), spy(), _csv(), _fingerprint(), _raw(), _row() (+17 more)

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (21): collect(), _cache_of(), _stop_after_reads(), test_cancel_before_any_read_leaves_cache_and_output_untouched(), stop(), test_cancel_still_works_while_reading_in_parallel(), test_plan_run_tells_when_a_rebuild_or_refresh_was_left_half_done(), test_rebuild_stop_saves_candidate_aside_and_resumes() (+13 more)

### Community 31 - "Community 31"
Cohesion: 0.09
Nodes (17): backup_cutoff(), _candidates(), device_id(), dir_key(), _dirs_of(), display_name(), _entry(), find_subdir() (+9 more)

### Community 32 - "Community 32"
Cohesion: 0.10
Nodes (17): collect_kla(), merge(), p1(), p2(), p3(), p3p(), _fmt(), _is_scanning_lock() (+9 more)

### Community 33 - "Community 33"
Cohesion: 0.08
Nodes (30): concurrency, cancel-in-progress, group, SHA, permissions, runs-on, steps, jobs (+22 more)

### Community 34 - "Community 34"
Cohesion: 0.13
Nodes (7): small(), P(), card2(), card(), fmt(), ok(), pick()

### Community 35 - "Community 35"
Cohesion: 0.07
Nodes (17): _advance_cursor(), _collect(), advance_finished(), checkpoint(), flush_read(), log_seen(), save_partial(), _load_resume() (+9 more)

### Community 36 - "Community 36"
Cohesion: 0.12
Nodes (18): cache_failures(), clamp_days(), _dev_name(), device_facts(), gather(), is_failure_record(), log_errors(), _log_paths() (+10 more)

### Community 37 - "Community 37"
Cohesion: 0.11
Nodes (3): DeviceStrip, LoadingOverlay, _state_label()

### Community 38 - "Community 38"
Cohesion: 0.11
Nodes (29): applySettings(), errorPanel(), goDay(), init(), layoutPairLabels(), loadDemo(), log(), navWarm() (+21 more)

### Community 39 - "Community 39"
Cohesion: 0.08
Nodes (11): _fingerprint(), _report(), test_a_report_without_a_lot_never_lists_the_setup_folder(), test_device_roots_are_listed_near_the_top_of_the_file(), test_diagnose_points_at_an_unexpected_report_folder_name(), test_loadport_placeholder_is_not_taken_as_the_lot(), test_lot_suffix_split(), test_norm_root_fixes_bare_drive_letter() (+3 more)

### Community 40 - "Community 40"
Cohesion: 0.12
Nodes (16): default_devices_csv(), ensure_user_files(), install_root(), logo_path(), _project_root(), resource_path(), template_path(), test_notice_path_never_imports_pyqt6() (+8 more)

### Community 41 - "Community 41"
Cohesion: 0.13
Nodes (15): kla_name(), missed_in_scope(), allowed_keys(), allows_row(), describe(), is_allowed(), is_kla(), key() (+7 more)

### Community 42 - "Community 42"
Cohesion: 0.11
Nodes (18): _pool_size(), with_dirs(), _case_insensitive_isdir(), _cfg(), _many_devices(), _snapshot(), test_backup_cutoff_reads_every_folder_name_seen_on_30_machines(), test_backups_that_differ_only_by_case_or_separator_are_deduped_and_live_folder_kept_first() (+10 more)

### Community 43 - "Community 43"
Cohesion: 0.16
Nodes (18): clamp_days(), gather(), gather_pixel(), is_pi(), pick_by_terms(), pick_samples(), pixel_is_zero(), render_pixel_summary() (+10 more)

### Community 44 - "Community 44"
Cohesion: 0.10
Nodes (15): _read_all(), read_bytes(), read_wafer_files(), _cache(), _picked(), test_bulk_listing_failure_falls_back_to_scandir(), test_file_growing_while_read_is_not_truncated(), test_full_listing_uses_the_bulk_lister_and_picks_the_same_reports() (+7 more)

### Community 45 - "Community 45"
Cohesion: 0.12
Nodes (26): addDays(), buildModel(), buildModelLegacy(), buildModelV3(), causeOf(), causeText(), cmpDev(), devSortKey() (+18 more)

### Community 46 - "Community 46"
Cohesion: 0.14
Nodes (7): MainWindow, ask(), error(), info(), _show(), warn(), test_periodic_update_check_only_shows_a_badge_and_badge_asks()

### Community 47 - "Community 47"
Cohesion: 0.15
Nodes (16): deps_installed(), deps_marker(), ensure_deps(), pip_install_cmd(), req_fingerprint(), req_lines(), write_deps_marker(), _root() (+8 more)

### Community 48 - "Community 48"
Cohesion: 0.12
Nodes (14): _make_nas(), _report(), _snapshot(), test_all_never_exceeds_ten_zip_parts(), test_all_reads_every_lot_in_window_bundles_results_and_dedups_params_across_lots(), test_all_tops_up_sparse_jobs_from_older_lots(), put(), test_collects_read_only_dedups_and_splits() (+6 more)

### Community 49 - "Community 49"
Cohesion: 0.17
Nodes (16): copy_app_tree(), _copytree(), _default_branch_name(), _fetch_runtime(), _git_head(), _import_app_module(), _isolated(), missing_packages() (+8 more)

### Community 50 - "Community 50"
Cohesion: 0.10
Nodes (14): _cache_device(), _carry_over(), _DeviceIndex, _entry_newest(), _is_stable_key(), parse_mdy(), read_ext_meta(), _rows_from_cache() (+6 more)

### Community 51 - "Community 51"
Cohesion: 0.13
Nodes (16): _cfg(), _cursor_of(), _embedded(), test_auto_row_finds_allowed_machines_without_listing_the_share(), test_cli_run_stays_in_scope(), test_collect_entry_points_stay_in_scope(), test_display_rename_keeps_one_device_and_one_cursor(), test_failed_report_blocks_cursor_and_is_retried() (+8 more)

### Community 52 - "Community 52"
Cohesion: 0.17
Nodes (19): build_exe(), clean_stale_output(), _default_run(), _dir_size_mb(), _ensure_venv(), exe_out_dirname(), import_probe_cmd(), _load_portable_impl() (+11 more)

### Community 53 - "Community 53"
Cohesion: 0.14
Nodes (16): _make_rdl(), rdl_all(), _rows(), test_multi_ignores_the_waferinfo_name_and_report_only_rows_stay_unknown(), test_multi_scan_reads_every_recipe_from_recipesinfo(), test_rdl_patch_reads_only_the_wafer_inis_of_rdl_rows_missing_the_mode(), test_recipesinfo_is_only_opened_at_the_exact_wafer_folder(), test_recipesinfo_sets_scan_mode_only_for_rdl_jobs() (+8 more)

### Community 54 - "Community 54"
Cohesion: 0.09
Nodes (14): fake_nas(), _no_startup_side_effects(), qapp(), _qt_app(), styled_qapp(), _no_real_subprocess(), scoped_nas(), fixture() (+6 more)

### Community 55 - "Community 55"
Cohesion: 0.13
Nodes (3): dur_text(), CollectResult, test_stale_token_signals_are_ignored()

### Community 56 - "Community 56"
Cohesion: 0.20
Nodes (15): _bundle(), _layout(), _marker(), _mk(), test_first_run_uses_the_console_python(), test_later_runs_are_windowless(), test_missing_console_python_falls_back_to_pythonw(), test_swap_applies_pending_update() (+7 more)

### Community 57 - "Community 57"
Cohesion: 0.10
Nodes (11): _numbers(), test_decision_numbers_are_unique_and_unbroken(), test_hook_reads_the_korean_file_name_correctly(), test_last_updated_line_is_present(), test_newest_work_log_entry_points_at_a_real_commit(), test_numbers_in_claude_md_match_the_code(), test_progress_doc_numbers_match_the_code(), test_required_section_exists() (+3 more)

### Community 58 - "Community 58"
Cohesion: 0.18
Nodes (12): _attach_dirs(), _dedupe_sort(), devices_from_csv(), devices_from_rows(), discover_devices(), _discover_under(), _log(), _norm_root() (+4 more)

### Community 59 - "Community 59"
Cohesion: 0.12
Nodes (12): password_files(), read_credentials(), reconnect(), _remote_of(), _win_connect(), fake_win(), test_no_password_file_means_no_attempt(), test_not_windows_or_not_drive_letter_does_nothing() (+4 more)

### Community 60 - "Community 60"
Cohesion: 0.10
Nodes (11): cache_status(), read_ini(), read_recipe_settings(), read_recipes_info(), read_scan_log(), _validate_cache_file(), read_text(), test_cache_load_is_strict_utf8_but_report_reading_stays_lenient() (+3 more)

### Community 61 - "Community 61"
Cohesion: 0.11
Nodes (13): CollectCancelled, RebuildRejected, _run(), take(), _workers(), test_ini_memo_lets_concurrent_readers_share_one_open(), slow(), test_run_stops_fast_without_waiting_for_slow_reads() (+5 more)

### Community 62 - "Community 62"
Cohesion: 0.12
Nodes (11): is_under(), test_device_index_exact_hits_and_legacy_path_fallback_agree_with_linear_search(), linear(), _call_name(), _enclosing_function(), _snapshot(), test_dynamic_no_write_under_nas(), test_is_under_windows_semantics() (+3 more)

### Community 63 - "Community 63"
Cohesion: 0.16
Nodes (13): apply_to_app(), color_mode(), colors(), normalize_color_mode(), palettes(), parse_template_tokens(), render_qss(), set_color_mode() (+5 more)

### Community 64 - "Community 64"
Cohesion: 0.10
Nodes (5): _DaysWorker, _GapFillWorker, _HtmlOnlyWorker, _ParamZipWorker, _PlanWorker

### Community 66 - "Community 66"
Cohesion: 0.20
Nodes (10): CollectorSignals, CollectorWorker, _collect_signals(), test_csv_lock_completes_with_warnings_not_failed(), locked(), test_failure_is_reported_not_raised(), test_html_lock_is_still_reported_as_failure(), test_run_emits_done_with_result() (+2 more)

### Community 67 - "Community 67"
Cohesion: 0.16
Nodes (10): load_tool(), ToolOutdated, WaferLogsWorker, _run(), _snapshot(), test_worker_collects_through_the_scope_gate(), test_worker_names_an_outdated_tool_file(), test_worker_reads_nothing_out_of_scope() (+2 more)

### Community 68 - "Community 68"
Cohesion: 0.15
Nodes (9): main(), measure(), old_write_html(), rss_mb(), timed(), changed_files(), check(), is_code() (+1 more)

### Community 69 - "Community 69"
Cohesion: 0.12
Nodes (9): _fake_out(), _load(), test_run_build_lite_with_fakes(), test_verify_checks_pass_on_valid_lite_output(), test_verify_full_requires_packages_and_marker(), test_verify_lite_rejects_marker_and_internal(), test_verify_rejects_big_launcher_and_missing_template_placeholder(), test_version_stamp_json() (+1 more)

### Community 70 - "Community 70"
Cohesion: 0.13
Nodes (11): _launch(), page_factory(), test_tab_indicator_moves_like_a_body_dragged_by_its_front(), test_gather_and_write_report(), resolver(), _dns(), _snapshot(), test_other_share_on_same_server_is_allowed_but_noted() (+3 more)

### Community 71 - "Community 71"
Cohesion: 0.14
Nodes (13): _embed_rows(), test_embedded_rows_are_folded_into_a_string_pool(), _embedded(), _fixture_rows(), _meta(), _open_rows_page(), rdl2_page(), rdl_page() (+5 more)

### Community 72 - "Community 72"
Cohesion: 0.16
Nodes (11): cache_file(), data_root(), devices_csv_path(), _ensure_dir(), log_file(), output_dir(), output_html(), load_tool() (+3 more)

### Community 73 - "Community 73"
Cohesion: 0.15
Nodes (13): _bundled_python(), _discard(), _ensure_deps(), _file_text(), _install_root(), _move(), _pending_dir(), _promote_in_place() (+5 more)

### Community 74 - "Community 74"
Cohesion: 0.19
Nodes (14): _add(), _cache(), _fake_lister(), _name_for(), _reports(), test_backfill_and_refresh_always_list_everything(), test_full_listing_interval_defaults_to_seven_days_and_is_configurable(), age_full_listing() (+6 more)

### Community 75 - "Community 75"
Cohesion: 0.21
Nodes (10): _q(), download(), git(), git_update(), is_git_repo(), main(), _opener(), repo_root() (+2 more)

### Community 76 - "Community 76"
Cohesion: 0.14
Nodes (5): is_dark_mode(), host_for(), _native(), _scrim_color(), SheetHost

### Community 77 - "Community 77"
Cohesion: 0.14
Nodes (9): isolated_data(), pytest_collection_modifyitems(), set_home(), shard_pick(), _It, test_shards_partition_all_tests_exactly(), _cfg(), test_out_of_scope_log_error_is_dropped_and_never_read() (+1 more)

### Community 78 - "Community 78"
Cohesion: 0.18
Nodes (8): load(), read_bytes(), sample_path(), sha256(), sample(), _fixture_phrases(), test_old_samples_are_intact_and_covered_by_the_30_day_status_fixture(), test_thirty_day_sample_has_the_recorded_fingerprint_and_row_counts()

### Community 79 - "Community 79"
Cohesion: 0.14
Nodes (14): _bat(), test_cli_never_execs(), test_default_runner_uses_subprocess_run_and_propagates_returncode(), fake_run(), test_main_with_update_reruns_once_as_a_child_and_does_not_collect_in_the_parent(), fake_run(), test_main_without_a_new_version_collects_in_place(), test_rerun_without_update_waits_for_the_child_and_returns_its_exit_code() (+6 more)

### Community 80 - "Community 80"
Cohesion: 0.18
Nodes (12): _full(), local(), _make_zip(), _patch_download(), test_git_update_reports_already_up_to_date(), test_git_update_stops_when_working_tree_is_dirty(), fake_git(), test_main_uses_zip_when_folder_is_not_a_git_checkout() (+4 more)

### Community 81 - "Community 81"
Cohesion: 0.16
Nodes (16): ms_since(), now_s(), op_isdir(), op_isfile(), op_open_read(), op_os_read_once(), resolve_wafer(), _run_level() (+8 more)

### Community 82 - "Community 82"
Cohesion: 0.16
Nodes (11): cached_days(), _row_day(), rows_for_range(), _wafer_key(), _cfg(), _embedded(), _model(), test_a_chosen_period_draws_only_its_days_and_matches_the_whole_file() (+3 more)

### Community 83 - "Community 83"
Cohesion: 0.16
Nodes (9): _stage_tree(), _verify_staged(), _write_version(), _write_version_to(), _fake_repo(), test_github_archive_contains_only_deploy_files(), test_staging_real_tree_passes_verification_and_top_level_equals_allow_list(), test_staging_top_level_equals_allow_list_even_with_junk_in_source_root() (+1 more)

### Community 84 - "Community 84"
Cohesion: 0.12
Nodes (9): build_meta(), items_of(), _canon(), _every(), _file_items(), _group_of(), split_unit(), _struct() (+1 more)

### Community 85 - "Community 85"
Cohesion: 0.12
Nodes (13): _cli_config(), count(), spy(), spy_bytes(), _count_report_reads(), spy(), test_cli_flags_and_exit_codes(), test_cli_help_describes_what_backfill_really_does() (+5 more)

### Community 86 - "Community 86"
Cohesion: 0.21
Nodes (9): plan_run(), RunPlan, test_plan_run_never_rederives_rows_and_memoizes_by_file_stamp(), _cache(), _sec_rows(), test_fill_gaps_fills_scan_ratio_from_wafer_folder_only_and_marks_reports(), test_fill_gaps_leaves_value_empty_when_folder_was_rewritten_later(), test_fill_gaps_stop_keeps_what_was_read() (+1 more)

### Community 87 - "Community 87"
Cohesion: 0.15
Nodes (11): blob_key(), _ounion(), put(), recipe_names(), snapshot(), _meta(), _snap(), test_build_meta_majority_diff_every_label_zone_names_and_history() (+3 more)

### Community 88 - "Community 88"
Cohesion: 0.19
Nodes (7): unpack(), build(), bundle_template(), encode_camel_attrs(), main(), offline_variant(), _res()

### Community 89 - "Community 89"
Cohesion: 0.17
Nodes (10): _fail_move_when(), _loose_app(), _snapshot(), test_latest_self_healing_retries_default_branch(), fake(), test_promote_recovers_a_backup_left_by_an_earlier_failed_rollback(), test_promote_success_replaces_all_and_leaves_no_backups(), test_rollback_failure_keeps_backups_and_names_the_files() (+2 more)

### Community 90 - "Community 90"
Cohesion: 0.17
Nodes (8): check_rows(), probe(), probe(), _has_report(), _is_kla_root(), _probe_auto(), _CheckWorker, test_check_rows_reports_out_of_scope_without_touching()

### Community 91 - "Community 91"
Cohesion: 0.21
Nodes (10): parse_terms(), pick_pixel_samples(), _row(), test_default_terms_parse_to_the_two_reported_lots(), test_gather_gives_devices_their_stable_key(), test_parse_terms_and_pick_by_terms_ignores_the_day_window(), test_pick_pixel_samples_skips_non_multi_and_round_robins_devices(), test_pick_pixel_samples_spreads_lots_per_job_and_prefers_defects() (+2 more)

### Community 92 - "Community 92"
Cohesion: 0.19
Nodes (7): decode(), _keep(), normalize(), parse_ini(), parse_rtp(), prune_blobs(), _split_comment()

### Community 93 - "Community 93"
Cohesion: 0.14
Nodes (7): eta(), eta_text(), ensure_html(), exists(), html_path(), last_collect_time(), test_ensure_html_creates_openable_file_without_collecting()

### Community 94 - "Community 94"
Cohesion: 0.19
Nodes (7): _fingerprint(), _load(), test_build_produces_one_closed_file_whose_logic_parses(), test_build_writes_only_where_it_is_told(), test_camel_attrs_are_encoded_only_in_markup_not_in_the_script(), test_offline_variant_waits_for_window_data_instead_of_fetching(), _tracked_design_files_untouched()

### Community 95 - "Community 95"
Cohesion: 0.17
Nodes (9): kla_nas(), klarf(), make_kla(), wafer(), test_collect_reads_kla_once_per_wafer_folder_and_builds_rows(), test_in_scope_device_that_could_not_be_reached_is_reported(), test_kla_outside_scope_is_never_touched(), test_locked_fresh_wafer_is_scanning_not_partial() (+1 more)

### Community 96 - "Community 96"
Cohesion: 0.23
Nodes (6): _FakeBuild, _out(), _polluted(), test_no_zip_when_verification_fails(), test_polluted_dist_ships_no_cache_log_or_backup_but_keeps_runtime(), test_zip_layout_and_instructions()

### Community 97 - "Community 97"
Cohesion: 0.22
Nodes (8): _ask(), _ask_int(), _ask_levels(), _ask_yes(), interactive(), main(), _pause(), real_collect_summary()

### Community 98 - "Community 98"
Cohesion: 0.18
Nodes (8): ensure_camtek_rows(), ensure_kla_rows(), read_devices_csv(), write_devices_csv(), test_read_csv_cp949_and_utf8_and_aliases(), test_read_csv_without_header_and_comments(), test_write_then_read_roundtrip(), test_existing_devices_csv_gets_the_eight_kla_rows_once()

### Community 99 - "Community 99"
Cohesion: 0.16
Nodes (10): _fmt_time(), _list_sub(), _list_top(), read_pixel(), _read_small(), render_listing(), survey_wafer(), read_head() (+2 more)

### Community 100 - "Community 100"
Cohesion: 0.18
Nodes (3): _c(), ProgressStrip, _PulseDot

### Community 101 - "Community 101"
Cohesion: 0.21
Nodes (6): _default_run(), test_extract_script_runs_on_the_product_sample(), git_sha(), main(), measure(), model_version()

### Community 102 - "Community 102"
Cohesion: 0.19
Nodes (8): _app_root(), check_for_update(), current_version(), ensure_version_file(), _git_head_ref(), is_git_checkout(), _version_file(), test_current_version_prefers_git_head_over_a_stale_version_file()

### Community 103 - "Community 103"
Cohesion: 0.20
Nodes (9): embedded(), unfold(), test_collect_writes_a_detailed_log_to_app_log_and_not_into_the_html(), test_home_rows_follow_device_order_and_save_copy_refolds_the_same_columns(), test_recipe_groups_apply_at_once_persist_in_browser_and_export(), test_load_picks_the_latest_saved_among_data_folder_and_downloads(), test_write_html_embeds_recipe_groups(), _w() (+1 more)

### Community 104 - "Community 104"
Cohesion: 0.22
Nodes (6): app_paths(), _error(), launch_cmd(), Layout, main(), swap_pending()

### Community 105 - "Community 105"
Cohesion: 0.19
Nodes (3): Deadline, OpRecorder, real_collect_runs()

### Community 106 - "Community 106"
Cohesion: 0.23
Nodes (11): cap(), run(), allocate(), log(), _run(), run_cmd(), _run_real(), step() (+3 more)

### Community 107 - "Community 107"
Cohesion: 0.26
Nodes (11): _ci_gate(), _is_full_sha(), _run(), _runs(), _serve_runs(), test_atom_fallback_and_error_recording(), fake_get(), test_ci_gate_holds_on_pending_failed_or_missing() (+3 more)

### Community 108 - "Community 108"
Cohesion: 0.19
Nodes (6): content_sha(), entries(), test_every_archived_file_matches_its_original_fingerprint(), test_everything_under_archive_is_listed(), test_manifest_has_entries_and_no_duplicates(), test_no_compiled_python_is_tracked()

### Community 109 - "Community 109"
Cohesion: 0.30
Nodes (8): collect_files(), instructions_text(), _load_build_module(), main(), make_zip(), read_version(), should_include(), zip_basename()

### Community 110 - "Community 110"
Cohesion: 0.29
Nodes (7): main(), _print(), _progress_printer(), cb(), rerun_args(), rerun_without_update(), test_rerun_args_strip_only_update_and_keep_everything_else()

### Community 111 - "Community 111"
Cohesion: 0.27
Nodes (6): _decrypt(), import_zips(), man(), read(), _open_zips(), _wanted()

### Community 112 - "Community 112"
Cohesion: 0.25
Nodes (5): candidates(), load(), normalize(), _read(), test_normalize_drops_bad_and_duplicate_entries()

### Community 113 - "Community 113"
Cohesion: 0.33
Nodes (11): navBox(), navCancel(), navGo(), navInd(), navNow(), navParts(), navRest(), navSet() (+3 more)

### Community 115 - "Community 115"
Cohesion: 0.18
Nodes (6): deps_changed(), _gate_info(), manual_check(), test_manual_check_reports_tls_failure(), test_ssl_verify_failure_stops_check_with_reason_and_no_retry(), _VerifyFailOpener

### Community 116 - "Community 116"
Cohesion: 0.38
Nodes (7): ShareProbeWorker, _csv(), _run(), test_empty_target_and_missing_tool_say_why(), test_hammer_needs_devices_csv_and_stops_on_request(), test_probe_then_clean_writes_only_inside_the_probe_folder(), test_refuses_a_target_on_the_device_nas()

### Community 117 - "Community 117"
Cohesion: 0.25
Nodes (5): _git(), _load(), test_check_requires_the_doc_only_when_code_changed(), test_code_paths_match_the_opt_in_hook(), test_main_looks_at_the_merge_base_range_not_only_the_last_commit()

### Community 118 - "Community 118"
Cohesion: 0.18
Nodes (10): env, PIP_DISABLE_PIP_VERSION_CHECK, jobs, progress-doc, name, permissions, contents, if (+2 more)

### Community 119 - "Community 119"
Cohesion: 0.29
Nodes (11): steps, steps, AOI_SHARD, QT_QPA_PLATFORM, steps, env, id, name (+3 more)

### Community 120 - "Community 120"
Cohesion: 0.22
Nodes (9): analyze(), _diff(), dist(), _dt_of(), med_ci(), parse_ini_bytes(), pct(), stage_times() (+1 more)

### Community 121 - "Community 121"
Cohesion: 0.22
Nodes (5): assert_local(), NasWriteRefused, roots_for_cfg(), test_assert_local_and_check_cfg(), test_roots_for_cfg_reads_every_row_even_disabled()

### Community 122 - "Community 122"
Cohesion: 0.33
Nodes (5): build(), graphify_cmds(), inline_scripts(), main(), write_inline_js()

### Community 123 - "Community 123"
Cohesion: 0.22
Nodes (7): file_times(), _ft(), op_find_exact(), op_getattr(), op_win_createfile_read(), _win(), win_find()

### Community 124 - "Community 124"
Cohesion: 0.22
Nodes (5): expand_roots(), normalize(), _share_root(), _unc_for_drive(), test_expand_roots_adds_share_root_for_unc()

### Community 125 - "Community 125"
Cohesion: 0.22
Nodes (4): ctx, html, input, stub()

### Community 126 - "Community 126"
Cohesion: 0.22
Nodes (5): _open_recipe(), test_recipe_close_point_labels_do_not_overlap(), test_recipe_device_row_opens_popup_with_keyboard_and_row_stays_same_node(), test_recipe_how_summary_and_details_are_accessible(), test_recipe_no_match_clearly_identifies_retained_or_empty_detail()

### Community 127 - "Community 127"
Cohesion: 0.28
Nodes (3): tripwire(), wrap(), Tripwire

### Community 128 - "Community 128"
Cohesion: 0.25
Nodes (9): strategy, name, runs-on, strategy, timeout-minutes, core, shard, fail-fast (+1 more)

### Community 129 - "Community 129"
Cohesion: 0.25
Nodes (3): find_pattern(), FoundEntry, _Stat

### Community 130 - "Community 130"
Cohesion: 0.25
Nodes (8): with, cache, cache-dependency-path, fetch-depth, key, node-version, path, python-version

### Community 132 - "Community 132"
Cohesion: 0.29
Nodes (5): _list_files(), run_grouped(), stage_reports(), list_one(), Wafer

### Community 133 - "Community 133"
Cohesion: 0.33
Nodes (4): fetch_content(), file_path_of(), test_fetch_content_respects_scope_and_device_roots(), test_file_path_of_unescapes_kla_error()

### Community 134 - "Community 134"
Cohesion: 0.33
Nodes (4): Ca(), Vb(), wb(), Xb()

### Community 136 - "Community 136"
Cohesion: 0.53
Nodes (6): _extract(), test_safe_extract_accepts_github_layout_and_short_sha_root(), test_safe_extract_caps_file_count_and_total_size(), test_safe_extract_rejects_hostile_entries_without_writing(), test_safe_extract_rejects_symlinks(), _zip_of()

### Community 139 - "Community 139"
Cohesion: 0.50
Nodes (5): Context(), Db(), Eb(), Et(), fb()

### Community 146 - "Community 146"
Cohesion: 0.50
Nodes (4): name, runs-on, timeout-minutes, browser

### Community 147 - "Community 147"
Cohesion: 0.50
Nodes (4): branches, True, pull_request, push

### Community 149 - "Community 149"
Cohesion: 0.67
Nodes (3): concurrency, cancel-in-progress, group

## Knowledge Gaps
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `make_cfg()` connect `Community 6` to `Community 7`, `Community 8`, `Community 16`, `Community 17`, `Community 29`, `Community 30`, `Community 42`, `Community 43`, `Community 44`, `Community 51`, `Community 53`, `Community 58`, `Community 59`, `Community 62`, `Community 66`, `Community 67`, `Community 74`, `Community 77`, `Community 85`, `Community 86`, `Community 91`, `Community 95`, `Community 103`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `collect()` (e.g. with `test_zero_new_rows_but_state_change_still_saves()` and `test_main_with_update_reruns_once_as_a_child_and_does_not_collect_in_the_parent()`) actually correct?**
  _`collect()` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.017780441514334232 - nodes in this community are weakly interconnected._
- **Why does `CollectPage` connect `Community 10` to `Community 7`, `Community 72`, `Community 140`, `Community 46`, `Community 16`, `Community 116`, `Community 55`, `Community 24`, `Community 26`, `Community 93`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.051344286781179985 - nodes in this community are weakly interconnected._
- **Why does `collect()` connect `Community 30` to `Community 6`, `Community 11`, `Community 19`, `Community 29`, `Community 35`, `Community 42`, `Community 44`, `Community 51`, `Community 53`, `Community 62`, `Community 66`, `Community 74`, `Community 79`, `Community 82`, `Community 85`, `Community 86`, `Community 95`, `Community 103`, `Community 105`, `Community 110`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.0651685393258427 - nodes in this community are weakly interconnected._