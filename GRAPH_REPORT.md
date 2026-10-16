# Graph Report - AOI-capacity  (2026-10-16)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 3314 nodes · 8232 edges · 149 communities (119 shown, 30 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 387 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `eb479068`
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
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148

## God Nodes (most connected - your core abstractions)
1. `make_cfg()` - 113 edges
2. `_collect()` - 52 edges
3. `CollectPage` - 49 edges
4. `rows_for_report()` - 48 edges
5. `w()` - 46 edges
6. `h()` - 46 edges
7. `write_html()` - 46 edges
8. `MainWindow` - 45 edges
9. `collect()` - 40 edges
10. `render()` - 39 edges

## Surprising Connections (you probably didn't know these)
- `fake_run()` --calls--> `_Done`  [INFERRED]
  dev/tests/test_cli_update_rerun.py → scripts/collect_wafer_logs.py
- `_emit()` --calls--> `progress()`  [INFERRED]
  aoi_capacity/utils/updater.py → test.py
- `fake_run()` --calls--> `_Done`  [INFERRED]
  dev/tests/test_cli_update_rerun.py → scripts/collect_wafer_logs.py
- `window()` --uses--> `MainWindow`  [INFERRED]
  dev/tests/test_ui_smoke.py → aoi_capacity/ui/main_window.py
- `test_default_html_is_the_last_html_days_of_the_data_in_one_file()` --indirect_call--> `collect()`  [INFERRED]
  dev/tests/test_html_range.py → aoi_capacity/collect.py

## Import Cycles
- None detected.

## Communities (149 total, 30 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (97): Animation(), avg(), B(), byLayer(), CAUSE_CODES, CAUSE_RULES, CLOSE, crTip() (+89 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (62): at(), busy(), _clean_batches(), globals_(), _hhmm(), _lot_rows(), meta(), _rdl() (+54 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (91): _a(), Ae(), Ao(), _assertThisInitialized(), Ba(), be(), bt(), cb() (+83 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (53): make_cfg(), _add_report(), _cache_of(), _dev_dir(), _entry_fp(), _entry_of(), _fingerprint(), _lock_replace_for() (+45 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (74): barsHtml(), bringToFront(), calloutW(), clock(), closeTop(), cmpDev(), cnt(), collectChip() (+66 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (38): _IniMemo, issue_text(), parse_report(), rows_for_report(), split_job_setup(), _backup_ini(), _live_ini(), test_batch_row_lot_is_never_the_loadport_placeholder() (+30 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (33): _advance_cursor(), _cache_summary(), cached_days(), _collect_log(), _entry_sort_stamp(), estimate_run_sec(), estimate_sec(), _first_day() (+25 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (29): _assign_device_keys(), _collect(), advance_finished(), checkpoint(), flush_read(), merge(), save_partial(), _Dirty (+21 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (33): _batch_from_rows(), cause_field(), failed_batch_row(), _first(), _is_error_row(), _is_placeholder(), is_unmapped_status(), issue_field() (+25 more)

### Community 9 - "Community 9"
Cohesion: 0.07
Nodes (28): load_config(), check_or_raise(), ConfigError, dashboard_settings(), fatal(), is_single_name(), normalize_config(), parse_bool() (+20 more)

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (6): assert_local(), CollectPage, eta(), _days_text(), eta_text(), to_collect_cfg()

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (19): category(), family(), q(), q(), lotcore(), q(), core(), q() (+11 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (27): _assets_snapshot(), _fingerprint(), _load(), _on(), _package_assets_untouched(), test_build_paths_leave_the_package_folder_untouched(), test_default_temp_js_sits_next_to_the_template(), test_dev_requirements_declare_yaml_and_playwright_but_runtime_does_not() (+19 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (44): behindAt(), calloutFit(), canAnim(), countUp(), deckSnap(), enterAnim(), enterView(), Flip() (+36 more)

### Community 15 - "Community 15"
Cohesion: 0.07
Nodes (25): _Counter, _drive_host(), fill_params(), one(), is_rdl_job(), _issue_dec(), nas_group(), _needs_rdl_patch() (+17 more)

### Community 16 - "Community 16"
Cohesion: 0.07
Nodes (40): addDays(), buildModel(), buildModelLegacy(), buildModelV3(), causeOf(), causeText(), dk(), famStem() (+32 more)

### Community 17 - "Community 17"
Cohesion: 0.08
Nodes (23): ensure_camtek_rows(), ensure_kla_rows(), read_devices_csv(), with_dirs(), write_devices_csv(), _case_insensitive_isdir(), _cfg(), _many_devices() (+15 more)

### Community 18 - "Community 18"
Cohesion: 0.09
Nodes (23): _check_zip_entries(), _default_branch(), _describe_err(), _http_get(), _is_ssl_verify_error(), latest_commit(), _latest_self_healing(), _latest_via_api() (+15 more)

### Community 19 - "Community 19"
Cohesion: 0.10
Nodes (6): P(), card2(), card(), fmt(), ok(), pick()

### Community 20 - "Community 20"
Cohesion: 0.17
Nodes (32): deps_blocked(), download_and_apply(), _emit(), last_error(), _app(), _branch_zip(), _exe_install(), _fake_pip() (+24 more)

### Community 21 - "Community 21"
Cohesion: 0.11
Nodes (21): collect_one(), copy_ini_for(), copy_report(), diagnose(), find_subdir(), list_folder(), lot_marks(), lot_parts() (+13 more)

### Community 22 - "Community 22"
Cohesion: 0.10
Nodes (17): list_top(), lot_table(), main(), parse_result(), parse_ts(), pick_copies(), pick_lots(), read_head() (+9 more)

### Community 23 - "Community 23"
Cohesion: 0.10
Nodes (26): make_device(), _cache_of(), _count_htm_reads(), spy(), _csv(), _fingerprint(), _raw(), _row() (+18 more)

### Community 24 - "Community 24"
Cohesion: 0.08
Nodes (20): backup_cutoff(), _candidates(), device_id(), dir_key(), _dirs_of(), display_name(), _entry(), find_subdir() (+12 more)

### Community 25 - "Community 25"
Cohesion: 0.08
Nodes (21): collect_kla(), merge(), p1(), p2(), p3(), p3p(), _fmt(), list_date() (+13 more)

### Community 26 - "Community 26"
Cohesion: 0.06
Nodes (15): _active(), _launch(), page_factory(), test_date_controls_keep_day_inside_the_visible_period(), test_device_popup_focus_inert_tab_trap_and_escape_return(), test_error_day_selection_matches_the_header_date(), test_error_lists_keep_rows_in_place_and_only_text_changes(), test_error_popup_type_popup_trend_and_report_tab() (+7 more)

### Community 27 - "Community 27"
Cohesion: 0.10
Nodes (21): collect(), scan_seconds(), _make_rdl(), rdl_all(), _rows(), test_multi_ignores_the_waferinfo_name_and_report_only_rows_stay_unknown(), test_multi_scan_reads_every_recipe_from_recipesinfo(), test_rdl_patch_reads_only_the_wafer_inis_of_rdl_rows_missing_the_mode() (+13 more)

### Community 28 - "Community 28"
Cohesion: 0.08
Nodes (18): build_meta(), items_of(), _canon(), decode(), _every(), _file_items(), _group_of(), _keep() (+10 more)

### Community 29 - "Community 29"
Cohesion: 0.09
Nodes (17): job_alias(), model_version(), rules(), section(), text(), _numbers(), test_decision_numbers_are_unique_and_unbroken(), test_hook_reads_the_korean_file_name_correctly() (+9 more)

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (5): _c(), DeviceStrip, LoadingOverlay, ProgressStrip, _PulseDot

### Community 31 - "Community 31"
Cohesion: 0.12
Nodes (17): _card(), SettingsPage, prefs_file(), load(), migrate(), patch(), Prefs, save() (+9 more)

### Community 32 - "Community 32"
Cohesion: 0.07
Nodes (12): _fingerprint(), nas(), _report(), test_a_report_without_a_lot_never_lists_the_setup_folder(), test_device_roots_are_listed_near_the_top_of_the_file(), test_diagnose_points_at_an_unexpected_report_folder_name(), test_loadport_placeholder_is_not_taken_as_the_lot(), test_lot_suffix_split() (+4 more)

### Community 33 - "Community 33"
Cohesion: 0.11
Nodes (17): probe(), _is_kla_root(), kla_name(), _probe_auto(), allowed_keys(), allows_row(), describe(), is_allowed() (+9 more)

### Community 34 - "Community 34"
Cohesion: 0.07
Nodes (11): test_browser_never_reads_the_nas_itself(), test_light_only_theme(), test_links_to_new_tabs_have_no_opener(), test_no_network_use_at_all(), test_removed_features_stay_removed(), test_screen_terms_are_the_design_terms_and_old_ones_are_gone(), test_status_classification_matches_the_python_side_and_the_design_script(), test_the_dialogs_have_accessible_names() (+3 more)

### Community 35 - "Community 35"
Cohesion: 0.17
Nodes (20): cache_file(), data_root(), default_devices_csv(), devices_csv_path(), _ensure_dir(), ensure_user_files(), install_root(), log_file() (+12 more)

### Community 36 - "Community 36"
Cohesion: 0.14
Nodes (17): deps_installed(), deps_marker(), ensure_deps(), pip_install_cmd(), req_fingerprint(), req_lines(), write_deps_marker(), _ensure_deps() (+9 more)

### Community 37 - "Community 37"
Cohesion: 0.10
Nodes (10): setup_logging(), test_apply_env_sets_hidpi_and_no_webengine_flags(), test_ensure_deps_is_noop_in_dev_tree(), test_setup_logging_writes_to_data_root(), test_cli_and_gui_share_the_app_log_file(), test_version_text_reads_sha_and_branch(), _apply_env(), _ensure_deps_installed() (+2 more)

### Community 38 - "Community 38"
Cohesion: 0.11
Nodes (16): _ask(), _ask_int(), _ask_levels(), _ask_yes(), file_times(), _ft(), interactive(), main() (+8 more)

### Community 39 - "Community 39"
Cohesion: 0.09
Nodes (15): fake_nas(), isolated_data(), _no_startup_side_effects(), qapp(), _qt_app(), set_home(), styled_qapp(), _no_real_subprocess() (+7 more)

### Community 40 - "Community 40"
Cohesion: 0.15
Nodes (17): copy_app_tree(), _copytree(), _default_branch_name(), _fetch_runtime(), _git_head(), _q(), _import_app_module(), _isolated() (+9 more)

### Community 41 - "Community 41"
Cohesion: 0.13
Nodes (14): _make_nas(), _report(), _snapshot(), test_all_never_exceeds_ten_zip_parts(), test_all_reads_every_lot_in_window_bundles_results_and_dedups_params_across_lots(), test_all_tops_up_sparse_jobs_from_older_lots(), put(), test_collects_read_only_dedups_and_splits() (+6 more)

### Community 42 - "Community 42"
Cohesion: 0.12
Nodes (18): _cfg(), _cursor_of(), _embedded(), test_auto_row_finds_allowed_machines_without_listing_the_share(), test_check_rows_reports_out_of_scope_without_touching(), test_cli_run_stays_in_scope(), test_collect_entry_points_stay_in_scope(), test_display_name_rules() (+10 more)

### Community 43 - "Community 43"
Cohesion: 0.10
Nodes (16): _pump(), test_collect_flow_writes_html_and_updates_status(), test_collect_range_is_editable_and_saved(), test_collect_refuses_out_of_scope_devices(), test_collect_refuses_without_devices(), test_html_days_is_editable_and_reaches_the_collect_cfg(), test_html_only_card_builds_from_cache_without_collecting(), test_mode_cards_pick_one_situation_and_map_to_worker_options() (+8 more)

### Community 44 - "Community 44"
Cohesion: 0.16
Nodes (5): MainWindow, ask(), error(), info(), _show()

### Community 45 - "Community 45"
Cohesion: 0.10
Nodes (6): _card(), _label(), ModeCard, _repolish(), Collapsible, default_out_dir()

### Community 46 - "Community 46"
Cohesion: 0.17
Nodes (19): build_exe(), clean_stale_output(), _default_run(), _dir_size_mb(), _ensure_venv(), exe_out_dirname(), import_probe_cmd(), _load_portable_impl() (+11 more)

### Community 47 - "Community 47"
Cohesion: 0.08
Nodes (13): cache_status(), parse_mdy(), read_ext_meta(), read_ini(), read_recipe_settings(), read_recipes_info(), read_scan_log(), _validate_cache_file() (+5 more)

### Community 48 - "Community 48"
Cohesion: 0.10
Nodes (13): is_under(), normalize(), test_device_index_exact_hits_and_legacy_path_fallback_agree_with_linear_search(), linear(), _call_name(), _enclosing_function(), _snapshot(), test_assert_local_and_check_cfg() (+5 more)

### Community 49 - "Community 49"
Cohesion: 0.16
Nodes (14): _attach_dirs(), check_rows(), _dedupe_sort(), devices_from_csv(), devices_from_rows(), probe(), discover_devices(), _discover_under() (+6 more)

### Community 50 - "Community 50"
Cohesion: 0.12
Nodes (11): _default_run(), test_extract_script_runs_on_the_product_sample(), main(), git_sha(), main(), measure(), model_version(), changed_files() (+3 more)

### Community 51 - "Community 51"
Cohesion: 0.14
Nodes (24): applySettings(), errorPanel(), init(), layoutPairLabels(), loadDemo(), log(), recipePopupHtml(), rgAdd() (+16 more)

### Community 52 - "Community 52"
Cohesion: 0.09
Nodes (12): _embed_rows(), one(), _rel_key(), _rel_under_device(), report_key(), report_name_patterns(), _strip_long_prefix(), test_rel_under_device_is_string_only_and_os_independent() (+4 more)

### Community 53 - "Community 53"
Cohesion: 0.14
Nodes (14): apply_to_app(), color_mode(), colors(), is_dark_mode(), normalize_color_mode(), palettes(), parse_template_tokens(), render_qss() (+6 more)

### Community 54 - "Community 54"
Cohesion: 0.20
Nodes (15): _bundle(), _layout(), _marker(), _mk(), test_first_run_uses_the_console_python(), test_later_runs_are_windowless(), test_missing_console_python_falls_back_to_pythonw(), test_swap_applies_pending_update() (+7 more)

### Community 55 - "Community 55"
Cohesion: 0.11
Nodes (14): _check(), CollectCancelled, RebuildRejected, _run(), take(), _workers(), test_ini_memo_lets_concurrent_readers_share_one_open(), slow() (+6 more)

### Community 56 - "Community 56"
Cohesion: 0.09
Nodes (5): _DaysWorker, _HtmlOnlyWorker, _ParamFillWorker, _ParamZipWorker, _PlanWorker

### Community 57 - "Community 57"
Cohesion: 0.15
Nodes (10): load_tool(), ToolOutdated, WaferLogsWorker, _run(), _snapshot(), test_worker_collects_through_the_scope_gate(), test_worker_names_an_outdated_tool_file(), test_worker_reads_nothing_out_of_scope() (+2 more)

### Community 59 - "Community 59"
Cohesion: 0.20
Nodes (10): CollectorSignals, CollectorWorker, _collect_signals(), test_csv_lock_completes_with_warnings_not_failed(), locked(), test_failure_is_reported_not_raised(), test_html_lock_is_still_reported_as_failure(), test_run_emits_done_with_result() (+2 more)

### Community 60 - "Community 60"
Cohesion: 0.12
Nodes (9): _fake_out(), _load(), test_run_build_lite_with_fakes(), test_verify_checks_pass_on_valid_lite_output(), test_verify_full_requires_packages_and_marker(), test_verify_lite_rejects_marker_and_internal(), test_verify_rejects_big_launcher_and_missing_template_placeholder(), test_version_stamp_json() (+1 more)

### Community 61 - "Community 61"
Cohesion: 0.18
Nodes (14): _add(), _cache(), _fake_lister(), _name_for(), _reports(), test_backfill_and_refresh_always_list_everything(), test_full_listing_interval_defaults_to_seven_days_and_is_configurable(), age_full_listing() (+6 more)

### Community 62 - "Community 62"
Cohesion: 0.12
Nodes (12): categories(), find_subdir(), is_placeholder(), name_day(), norm_root(), read_bytes(), scan_dirs(), survey_device() (+4 more)

### Community 63 - "Community 63"
Cohesion: 0.17
Nodes (9): blob_key(), load(), read_bytes(), sample_path(), sha256(), sample(), _fixture_phrases(), test_old_samples_are_intact_and_covered_by_the_30_day_status_fixture() (+1 more)

### Community 64 - "Community 64"
Cohesion: 0.14
Nodes (10): _no_input(), test_console_path_waits_for_enter(), test_ensure_deps_failure_notifies_with_log_path_and_returns_false(), test_input_failures_fall_back_without_raising(), test_notice_path_never_imports_pyqt6(), test_stdin_none_skips_input_and_prints_when_no_messagebox(), test_windows_uses_messagebox_when_stdin_is_none(), test_windows_without_windll_or_a_failing_box_prints_instead() (+2 more)

### Community 65 - "Community 65"
Cohesion: 0.13
Nodes (11): _cache_device(), _carry_over(), newest_of(), _DeviceIndex, _entry_newest(), _is_stable_key(), parse_dt(), _rows_from_cache() (+3 more)

### Community 66 - "Community 66"
Cohesion: 0.18
Nodes (12): _full(), local(), _make_zip(), _patch_download(), test_git_update_reports_already_up_to_date(), test_git_update_stops_when_working_tree_is_dirty(), fake_git(), test_main_uses_zip_when_folder_is_not_a_git_checkout() (+4 more)

### Community 67 - "Community 67"
Cohesion: 0.18
Nodes (17): run(), allocate(), log(), now_s(), _run(), run_cmd(), _run_level(), one() (+9 more)

### Community 68 - "Community 68"
Cohesion: 0.16
Nodes (12): _bundled_python(), _discard(), _file_text(), _install_root(), _move(), _pending_dir(), _promote_in_place(), _remove() (+4 more)

### Community 69 - "Community 69"
Cohesion: 0.16
Nodes (8): test_no_compiled_python_is_tracked(), _fingerprint(), _load(), test_build_produces_one_closed_file_whose_logic_parses(), test_build_writes_only_where_it_is_told(), test_camel_attrs_are_encoded_only_in_markup_not_in_the_script(), test_offline_variant_waits_for_window_data_instead_of_fetching(), _tracked_design_files_untouched()

### Community 70 - "Community 70"
Cohesion: 0.24
Nodes (9): download(), git(), git_update(), is_git_repo(), main(), _opener(), repo_root(), say() (+1 more)

### Community 71 - "Community 71"
Cohesion: 0.14
Nodes (13): _diff(), _dt_of(), ms_since(), op_isdir(), op_isfile(), op_open_read(), op_os_read_once(), parse_ini_bytes() (+5 more)

### Community 72 - "Community 72"
Cohesion: 0.13
Nodes (11): _backup_roots(), read_one(), _decode_report(), ini_roots_for(), job_folder_variants(), test_ini_roots_start_with_the_backup_whose_cutoff_is_after_the_batch(), test_job_folder_variants_are_exact_names_in_order(), test_job_folder_variants_match_the_app() (+3 more)

### Community 73 - "Community 73"
Cohesion: 0.13
Nodes (9): plan_run(), RunPlan, test_plan_run_never_rederives_rows_and_memoizes_by_file_stamp(), test_collector_reads_params_once_per_report_and_html_carries_them(), test_fill_params_reads_only_wafer_folders_of_reports_without_snapshots(), test_fill_params_stop_keeps_what_was_read_and_resumes(), test_import_zips_resolves_references_and_skips_out_of_scope(), test_measurements_and_camera_position_are_not_kept() (+1 more)

### Community 74 - "Community 74"
Cohesion: 0.15
Nodes (9): _read_all(), read_bytes(), test_file_growing_while_read_is_not_truncated(), test_missing_and_directory_raise_the_same_kinds_as_before(), test_os_open_in_nas_guard_is_read_only(), test_read_bytes_matches_builtin_open(), test_read_text_matches_builtin_open(), test_small_file_is_read_with_one_read_call() (+1 more)

### Community 75 - "Community 75"
Cohesion: 0.16
Nodes (4): host_for(), _native(), _scrim_color(), SheetHost

### Community 76 - "Community 76"
Cohesion: 0.17
Nodes (10): _app_root(), check_for_update(), current_version(), ensure_version_file(), _git_head(), _git_head_ref(), _identity(), is_git_checkout() (+2 more)

### Community 77 - "Community 77"
Cohesion: 0.14
Nodes (9): em(), pt(), bt(), bt(), flatten(), full(), num(), same() (+1 more)

### Community 78 - "Community 78"
Cohesion: 0.19
Nodes (7): unpack(), build(), bundle_template(), encode_camel_attrs(), main(), offline_variant(), _res()

### Community 79 - "Community 79"
Cohesion: 0.19
Nodes (8): candidates(), load(), normalize(), _read(), test_load_picks_the_latest_saved_among_data_folder_and_downloads(), test_normalize_drops_bad_and_duplicate_entries(), test_write_html_embeds_recipe_groups(), _w()

### Community 80 - "Community 80"
Cohesion: 0.18
Nodes (8): _stage_tree(), _verify_staged(), _write_version(), _write_version_to(), _fake_repo(), test_staging_real_tree_passes_verification_and_top_level_equals_allow_list(), test_staging_top_level_equals_allow_list_even_with_junk_in_source_root(), test_verify_rejects_unexpected_top_level_entry()

### Community 81 - "Community 81"
Cohesion: 0.17
Nodes (12): _bat(), test_cli_never_execs(), test_default_runner_uses_subprocess_run_and_propagates_returncode(), fake_run(), test_main_with_update_reruns_once_as_a_child_and_does_not_collect_in_the_parent(), test_main_without_a_new_version_collects_in_place(), test_rerun_without_update_waits_for_the_child_and_returns_its_exit_code(), fake_run() (+4 more)

### Community 82 - "Community 82"
Cohesion: 0.14
Nodes (10): _cli_config(), _count_nas_reads(), count(), spy(), spy_bytes(), _count_report_reads(), spy(), test_cli_flags_and_exit_codes() (+2 more)

### Community 83 - "Community 83"
Cohesion: 0.17
Nodes (10): _fail_move_when(), _loose_app(), _snapshot(), test_latest_self_healing_retries_default_branch(), fake(), test_promote_recovers_a_backup_left_by_an_earlier_failed_rollback(), test_promote_success_replaces_all_and_leaves_no_backups(), test_rollback_failure_keeps_backups_and_names_the_files() (+2 more)

### Community 84 - "Community 84"
Cohesion: 0.23
Nodes (6): collect_lot(), pack_lot_all(), Packer, recipe_mode(), safe(), stamp()

### Community 85 - "Community 85"
Cohesion: 0.20
Nodes (9): decode(), decrypt_bytes(), _enc_secret(), encrypt_bytes(), is_bundle(), _keystream(), main(), parse_args() (+1 more)

### Community 86 - "Community 86"
Cohesion: 0.19
Nodes (7): _cache_rows(), test_old_free_text_rows_and_new_coded_rows_coexist_and_wording_changes_need_no_recollection(), spy(), test_render_issue_rows_fills_new_rows_only_and_never_mutates_or_touches_old_rows(), _files(), _string_literals(), test_no_korean_string_literals_outside_i18n()

### Community 87 - "Community 87"
Cohesion: 0.23
Nodes (6): _FakeBuild, _out(), _polluted(), test_no_zip_when_verification_fails(), test_polluted_dist_ships_no_cache_log_or_backup_but_keeps_runtime(), test_zip_layout_and_instructions()

### Community 88 - "Community 88"
Cohesion: 0.22
Nodes (6): app_paths(), _error(), launch_cmd(), Layout, main(), swap_pending()

### Community 90 - "Community 90"
Cohesion: 0.26
Nodes (11): _ci_gate(), _is_full_sha(), _run(), _runs(), _serve_runs(), test_atom_fallback_and_error_recording(), fake_get(), test_ci_gate_holds_on_pending_failed_or_missing() (+3 more)

### Community 91 - "Community 91"
Cohesion: 0.21
Nodes (10): _embedded(), _fixture_rows(), _meta(), _open_rows_page(), rdl2_page(), rdl_page(), _rdl_rows(), add() (+2 more)

### Community 92 - "Community 92"
Cohesion: 0.21
Nodes (3): Deadline, OpRecorder, real_collect_runs()

### Community 93 - "Community 93"
Cohesion: 0.26
Nodes (8): main(), _print(), _progress_printer(), cb(), rerun_args(), rerun_without_update(), test_rerun_args_strip_only_update_and_keep_everything_else(), test_cli_prints_warnings_and_stops_on_fatal_config()

### Community 94 - "Community 94"
Cohesion: 0.26
Nodes (6): _decrypt(), import_zips(), man(), read(), _open_zips(), _wanted()

### Community 95 - "Community 95"
Cohesion: 0.20
Nodes (4): warn(), _pump(), test_card_runs_and_blocks_collect_meanwhile(), __init__()

### Community 96 - "Community 96"
Cohesion: 0.17
Nodes (7): ctx, fs, html, input, path, stub(), vm

### Community 97 - "Community 97"
Cohesion: 0.30
Nodes (8): collect_files(), instructions_text(), _load_build_module(), main(), make_zip(), read_version(), should_include(), zip_basename()

### Community 98 - "Community 98"
Cohesion: 0.27
Nodes (9): pick(), run(), collect_one(), done_ok(), limit_reached(), run_all(), run_wide(), take() (+1 more)

### Community 99 - "Community 99"
Cohesion: 0.33
Nodes (11): navBox(), navCancel(), navGo(), navInd(), navNow(), navParts(), navRest(), navSet() (+3 more)

### Community 100 - "Community 100"
Cohesion: 0.18
Nodes (6): deps_changed(), _gate_info(), manual_check(), test_manual_check_reports_tls_failure(), test_ssl_verify_failure_stops_check_with_reason_and_no_retry(), _VerifyFailOpener

### Community 101 - "Community 101"
Cohesion: 0.25
Nodes (5): ensure_html(), exists(), html_path(), last_collect_time(), test_ensure_html_creates_openable_file_without_collecting()

### Community 102 - "Community 102"
Cohesion: 0.24
Nodes (5): content_sha(), entries(), test_every_archived_file_matches_its_original_fingerprint(), test_everything_under_archive_is_listed(), test_manifest_has_entries_and_no_duplicates()

### Community 103 - "Community 103"
Cohesion: 0.31
Nodes (7): _cfg(), _embedded(), _model(), test_a_chosen_period_draws_only_its_days_and_matches_the_whole_file(), test_default_html_is_the_last_html_days_of_the_data_in_one_file(), test_html_from_cache_needs_no_nas_and_keeps_report_paths(), test_rows_for_range_keeps_context_and_order()

### Community 104 - "Community 104"
Cohesion: 0.25
Nodes (5): _git(), _load(), test_check_requires_the_doc_only_when_code_changed(), test_code_paths_match_the_opt_in_hook(), test_main_looks_at_the_merge_base_range_not_only_the_last_commit()

### Community 105 - "Community 105"
Cohesion: 0.20
Nodes (6): expand_roots(), roots_for_cfg(), _share_root(), _unc_for_drive(), test_expand_roots_adds_share_root_for_unc(), test_roots_for_cfg_reads_every_row_even_disabled()

### Community 107 - "Community 107"
Cohesion: 0.33
Nodes (5): build(), graphify_cmds(), inline_scripts(), main(), write_inline_js()

### Community 108 - "Community 108"
Cohesion: 0.28
Nodes (7): ac(), flatten(), full(), norm(), num(), q(), same()

### Community 109 - "Community 109"
Cohesion: 0.28
Nodes (6): embedded(), unfold(), test_collect_writes_a_detailed_log_to_app_log_and_not_into_the_html(), test_home_rows_follow_device_order_and_save_copy_refolds_the_same_columns(), test_recipe_groups_apply_at_once_persist_in_browser_and_export(), test_unfold_maps_columns_by_name_and_validates_the_pool()

### Community 110 - "Community 110"
Cohesion: 0.22
Nodes (5): _open_recipe(), test_recipe_close_point_labels_do_not_overlap(), test_recipe_device_row_opens_popup_with_keyboard_and_row_stays_same_node(), test_recipe_how_summary_and_details_are_accessible(), test_recipe_no_match_clearly_identifies_retained_or_empty_detail()

### Community 112 - "Community 112"
Cohesion: 0.25
Nodes (3): find_pattern(), FoundEntry, _Stat

### Community 113 - "Community 113"
Cohesion: 0.25
Nodes (6): Aa(), Ca(), na(), Vb(), wb(), Xb()

### Community 115 - "Community 115"
Cohesion: 0.54
Nodes (6): _example(), _public(), test_every_default_config_key_is_in_the_example_or_explicitly_excused(), test_example_loads_through_the_cli_loader(), test_example_public_keys_are_a_subset_of_default_config_with_the_same_types(), test_example_scope_and_workers_show_the_real_defaults()

### Community 119 - "Community 119"
Cohesion: 0.29
Nodes (4): job_folder_variants(), lot_dir_of(), read_lot_all(), submit()

### Community 121 - "Community 121"
Cohesion: 0.33
Nodes (3): fake_run(), _Done, _Full

### Community 122 - "Community 122"
Cohesion: 0.33
Nodes (3): test_corrupt_cache_is_preserved_as_bad_file_not_overwritten_silently(), test_recover_targets_only_ini_states_that_can_come_back(), test_worker_count_is_clamped_to_the_work_there_is()

### Community 123 - "Community 123"
Cohesion: 0.33
Nodes (4): _cache(), _picked(), test_bulk_listing_failure_falls_back_to_scandir(), test_full_listing_uses_the_bulk_lister_and_picks_the_same_reports()

### Community 124 - "Community 124"
Cohesion: 0.53
Nodes (6): _extract(), test_safe_extract_accepts_github_layout_and_short_sha_root(), test_safe_extract_caps_file_count_and_total_size(), test_safe_extract_rejects_hostile_entries_without_writing(), test_safe_extract_rejects_symlinks(), _zip_of()

### Community 126 - "Community 126"
Cohesion: 0.40
Nodes (5): analyze(), dist(), med_ci(), pct(), agree()

### Community 128 - "Community 128"
Cohesion: 0.40
Nodes (4): _list_all(), scandir(), _list_files(), list_one()

### Community 129 - "Community 129"
Cohesion: 0.50
Nodes (5): Context(), Db(), Eb(), Et(), fb()

### Community 133 - "Community 133"
Cohesion: 0.40
Nodes (3): fs_spy(), wrap(), _Spy

## Knowledge Gaps
- **30 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MainWindow` connect `Community 44` to `Community 130`, `Community 131`, `Community 35`, `Community 37`, `Community 10`, `Community 75`, `Community 106`, `Community 43`, `Community 14`, `Community 53`, `Community 89`, `Community 58`, `Community 59`, `Community 57`, `Community 30`, `Community 95`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.017482517482517484 - nodes in this community are weakly interconnected._
- **Why does `make_cfg()` connect `Community 3` to `Community 7`, `Community 9`, `Community 15`, `Community 17`, `Community 23`, `Community 25`, `Community 27`, `Community 37`, `Community 39`, `Community 42`, `Community 43`, `Community 48`, `Community 49`, `Community 57`, `Community 59`, `Community 61`, `Community 73`, `Community 74`, `Community 82`, `Community 86`, `Community 109`, `Community 122`, `Community 123`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05407111298127498 - nodes in this community are weakly interconnected._
- **Why does `run_tool()` connect `Community 22` to `Community 40`, `Community 11`, `Community 21`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.06258958432871477 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.057911392405063294 - nodes in this community are weakly interconnected._