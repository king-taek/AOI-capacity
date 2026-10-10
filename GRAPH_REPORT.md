# Graph Report - AOI-capacity  (2026-10-10)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 3078 nodes · 7561 edges · 129 communities (104 shown, 25 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 355 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `dfa02a5f`
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
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126

## God Nodes (most connected - your core abstractions)
1. `collect()` - 111 edges
2. `make_cfg()` - 100 edges
3. `MainWindow` - 46 edges
4. `write_html()` - 45 edges
5. `h()` - 43 edges
6. `rows_for_report()` - 41 edges
7. `w()` - 40 edges
8. `CollectPage` - 39 edges
9. `r()` - 37 edges
10. `download_and_apply()` - 37 edges

## Surprising Connections (you probably didn't know these)
- `_emit()` --calls--> `progress()`  [INFERRED]
  aoi_capacity/utils/updater.py → test.py
- `run()` --calls--> `log()`  [INFERRED]
  scripts/internal/portable_build.py → test.py
- `window()` --uses--> `MainWindow`  [INFERRED]
  dev/tests/test_ui_smoke.py → aoi_capacity/ui/main_window.py
- `test_ini_memo_classifies_missing_the_same()` --calls--> `_IniMemo`  [EXTRACTED]
  dev/tests/test_nas_read.py → aoi_capacity/collect.py
- `fake_run()` --calls--> `_Done`  [INFERRED]
  dev/tests/test_cli_update_rerun.py → scripts/collect_wafer_logs.py

## Import Cycles
- None detected.

## Communities (129 total, 25 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (84): B(), byLayer(), CAUSE_CODES, CAUSE_RULES, cb(), CLOSE, devStatus, di() (+76 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (55): at(), busy(), _clean_batches(), globals_(), _hhmm(), _lot_rows(), meta(), _rdl() (+47 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (52): plan_run(), make_cfg(), _add_report(), _cache_of(), _count_nas_reads(), _dev_dir(), _entry_fp(), _entry_of() (+44 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (62): _a(), Ae(), Ao(), be(), cc(), ce(), $d(), de() (+54 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (29): _cache_device(), _cache_summary(), cached_days(), _carry_over(), _DeviceIndex, _drive_host(), _entry_newest(), is_rdl_job() (+21 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (25): _assign_device_keys(), _Dirty, _entry_sort_stamp(), _fresh_key(), html_from_cache(), _load_cache(), _mark_device_status(), _migrate_cursors() (+17 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (31): parse_report(), rows_for_report(), split_job_setup(), _live_ini(), test_batch_row_lot_is_never_the_loadport_placeholder(), test_embedded_rows_are_folded_into_a_string_pool(), test_empty_lot_never_builds_an_ini_path(), test_failed_batch_becomes_one_row_with_batch_times() (+23 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (26): ConfigError, dashboard_settings(), is_single_name(), normalize_config(), parse_bool(), parse_int(), Problem, _show() (+18 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (47): avg(), exFam(), f0(), f1(), famIndex(), famStem(), Fd(), fillModes() (+39 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (22): _advance_cursor(), _check(), collect(), newest_of(), read_one(), CollectCancelled, _Counter, _decode_report() (+14 more)

### Community 10 - "Community 10"
Cohesion: 0.04
Nodes (19): _active(), test_date_controls_keep_day_inside_the_visible_period(), test_device_popup_focus_inert_tab_trap_and_escape_return(), test_error_day_selection_matches_the_header_date(), test_error_lists_keep_rows_in_place_and_only_text_changes(), test_error_popup_type_popup_trend_and_report_tab(), test_error_tab_period_popup_filters_and_no_total_link(), test_floor_and_maker_filters_are_picked_separately() (+11 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (27): _assets_snapshot(), _fingerprint(), _load(), _on(), _package_assets_untouched(), test_build_paths_leave_the_package_folder_untouched(), test_default_temp_js_sits_next_to_the_template(), test_dev_requirements_declare_yaml_and_playwright_but_runtime_does_not() (+19 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (22): category(), family(), q(), q(), lotcore(), q(), core(), q() (+14 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (25): _read_all(), read_bytes(), _call_name(), _enclosing_function(), _snapshot(), test_is_under_windows_semantics(), test_nas_guard_module_has_no_write_helpers(), test_roots_for_cfg_reads_every_row_even_disabled() (+17 more)

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (6): P(), card2(), card(), fmt(), ok(), pick()

### Community 16 - "Community 16"
Cohesion: 0.10
Nodes (43): barsHtml(), bringToFront(), calloutW(), clock(), closeTop(), cnt(), collectChip(), cut() (+35 more)

### Community 17 - "Community 17"
Cohesion: 0.06
Nodes (17): job_alias(), model_version(), rules(), section(), text(), test_browser_never_reads_the_nas_itself(), test_light_only_theme(), test_links_to_new_tabs_have_no_opener() (+9 more)

### Community 18 - "Community 18"
Cohesion: 0.09
Nodes (41): behindAt(), calloutFit(), canAnim(), countUp(), deckSnap(), enterAnim(), enterView(), Flip() (+33 more)

### Community 19 - "Community 19"
Cohesion: 0.08
Nodes (24): _check_zip_entries(), _default_branch(), deps_changed(), _describe_err(), _http_get(), _is_ssl_verify_error(), latest_commit(), _latest_self_healing() (+16 more)

### Community 20 - "Community 20"
Cohesion: 0.08
Nodes (18): test_apply_env_sets_hidpi_and_no_webengine_flags(), test_ensure_deps_is_noop_in_dev_tree(), test_setup_logging_writes_to_data_root(), _no_input(), test_console_path_waits_for_enter(), test_ensure_deps_failure_notifies_with_log_path_and_returns_false(), test_input_failures_fall_back_without_raising(), test_notice_path_never_imports_pyqt6() (+10 more)

### Community 21 - "Community 21"
Cohesion: 0.10
Nodes (27): _ci_gate(), _is_full_sha(), _extract(), _fail_move_when(), _loose_app(), _run(), _runs(), _serve_runs() (+19 more)

### Community 22 - "Community 22"
Cohesion: 0.10
Nodes (17): list_top(), lot_table(), main(), parse_result(), parse_ts(), pick_copies(), pick_lots(), read_head() (+9 more)

### Community 23 - "Community 23"
Cohesion: 0.08
Nodes (20): backup_cutoff(), _candidates(), device_id(), dir_key(), _dirs_of(), display_name(), _entry(), find_subdir() (+12 more)

### Community 24 - "Community 24"
Cohesion: 0.08
Nodes (5): _c(), DeviceStrip, LoadingOverlay, ProgressStrip, _PulseDot

### Community 25 - "Community 25"
Cohesion: 0.11
Nodes (21): collect_one(), copy_ini_for(), copy_report(), diagnose(), find_subdir(), list_folder(), lot_marks(), lot_parts() (+13 more)

### Community 26 - "Community 26"
Cohesion: 0.09
Nodes (20): collect_kla(), p1(), p2(), p3(), p3p(), _fmt(), list_date(), list_dates() (+12 more)

### Community 27 - "Community 27"
Cohesion: 0.10
Nodes (24): _cache_of(), _count_htm_reads(), spy(), _csv(), _fingerprint(), _raw(), _row(), _same_mtime() (+16 more)

### Community 28 - "Community 28"
Cohesion: 0.08
Nodes (18): cache_status(), _embed_rows(), _empty_cache(), read_ini(), read_recipes_info(), _save_cache(), _unique_tmp(), _validate_cache_file() (+10 more)

### Community 29 - "Community 29"
Cohesion: 0.09
Nodes (16): _default_run(), test_ini_memo_lets_concurrent_readers_share_one_open(), slow(), test_legacy_profile_equals_the_design_script_on_the_30_day_sample(), test_extract_script_runs_on_the_product_sample(), _git(), _load(), test_check_requires_the_doc_only_when_code_changed() (+8 more)

### Community 30 - "Community 30"
Cohesion: 0.11
Nodes (19): _batch_from_rows(), cause_field(), failed_batch_row(), _first(), _is_error_row(), is_unmapped_status(), _lead_error_row(), norm_causes() (+11 more)

### Community 31 - "Community 31"
Cohesion: 0.12
Nodes (19): load_config(), prefs_file(), load(), migrate(), patch(), Prefs, save(), to_collect_cfg() (+11 more)

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (21): setup_logging(), cache_file(), data_root(), default_devices_csv(), devices_csv_path(), _ensure_dir(), ensure_user_files(), install_root() (+13 more)

### Community 34 - "Community 34"
Cohesion: 0.07
Nodes (13): _fingerprint(), nas(), _report(), test_a_report_without_a_lot_never_lists_the_setup_folder(), test_device_roots_are_listed_near_the_top_of_the_file(), test_diagnose_points_at_an_unexpected_report_folder_name(), test_loadport_placeholder_is_not_taken_as_the_lot(), test_lot_suffix_split() (+5 more)

### Community 35 - "Community 35"
Cohesion: 0.11
Nodes (4): MainWindow, _pump(), test_card_runs_and_blocks_collect_meanwhile(), __init__()

### Community 36 - "Community 36"
Cohesion: 0.22
Nodes (26): deps_blocked(), download_and_apply(), _emit(), last_error(), _app(), _branch_zip(), _exe_install(), _fake_pip() (+18 more)

### Community 37 - "Community 37"
Cohesion: 0.13
Nodes (13): em(), pt(), bt(), bt(), flatten(), full(), num(), same() (+5 more)

### Community 38 - "Community 38"
Cohesion: 0.08
Nodes (15): fake_nas(), isolated_data(), _no_startup_side_effects(), qapp(), _qt_app(), set_home(), _no_real_subprocess(), rdl_all() (+7 more)

### Community 39 - "Community 39"
Cohesion: 0.12
Nodes (18): _cfg(), _cursor_of(), _embedded(), test_auto_row_finds_allowed_machines_without_listing_the_share(), test_check_rows_reports_out_of_scope_without_touching(), test_cli_run_stays_in_scope(), test_collect_entry_points_stay_in_scope(), test_display_name_rules() (+10 more)

### Community 40 - "Community 40"
Cohesion: 0.16
Nodes (17): copy_app_tree(), _copytree(), _default_branch_name(), _fetch_runtime(), _git_head(), _import_app_module(), _isolated(), missing_packages() (+9 more)

### Community 41 - "Community 41"
Cohesion: 0.13
Nodes (17): _backup_roots(), with_dirs(), make_device(), _case_insensitive_isdir(), _cfg(), _many_devices(), _snapshot(), test_backups_that_differ_only_by_case_or_separator_are_deduped_and_live_folder_kept_first() (+9 more)

### Community 42 - "Community 42"
Cohesion: 0.13
Nodes (27): applySettings(), errorPanel(), init(), layoutPairLabels(), loadDemo(), log(), rcpToggleKind(), recipeMap() (+19 more)

### Community 44 - "Community 44"
Cohesion: 0.15
Nodes (16): deps_installed(), deps_marker(), ensure_deps(), pip_install_cmd(), req_fingerprint(), req_lines(), write_deps_marker(), _root() (+8 more)

### Community 45 - "Community 45"
Cohesion: 0.12
Nodes (14): _make_nas(), _report(), _snapshot(), test_all_never_exceeds_ten_zip_parts(), test_all_reads_every_lot_in_window_bundles_results_and_dedups_params_across_lots(), test_all_tops_up_sparse_jobs_from_older_lots(), put(), test_collects_read_only_dedups_and_splits() (+6 more)

### Community 46 - "Community 46"
Cohesion: 0.13
Nodes (17): report_name_patterns(), _add(), _cache(), _fake_lister(), _name_for(), _reports(), test_backfill_and_refresh_always_list_everything(), test_full_listing_interval_defaults_to_seven_days_and_is_configurable() (+9 more)

### Community 47 - "Community 47"
Cohesion: 0.13
Nodes (13): embedded(), load(), read_bytes(), sample_path(), sha256(), unfold(), test_home_rows_follow_device_order_and_save_copy_refolds_the_same_columns(), test_recipe_groups_apply_at_once_persist_in_browser_and_export() (+5 more)

### Community 48 - "Community 48"
Cohesion: 0.11
Nodes (16): _pump(), test_collect_flow_writes_html_and_updates_status(), test_collect_range_is_editable_and_saved(), test_collect_refuses_out_of_scope_devices(), test_collect_refuses_without_devices(), test_html_days_is_editable_and_reaches_the_collect_cfg(), test_html_only_card_builds_from_cache_without_collecting(), test_mode_cards_pick_one_situation_and_map_to_worker_options() (+8 more)

### Community 49 - "Community 49"
Cohesion: 0.17
Nodes (19): build_exe(), clean_stale_output(), _default_run(), _dir_size_mb(), _ensure_venv(), exe_out_dirname(), import_probe_cmd(), _load_portable_impl() (+11 more)

### Community 50 - "Community 50"
Cohesion: 0.13
Nodes (14): kla_name(), allowed_keys(), allows_row(), describe(), is_allowed(), is_kla(), key(), path_tail() (+6 more)

### Community 51 - "Community 51"
Cohesion: 0.13
Nodes (10): is_dark_mode(), ask(), error(), host_for(), info(), _native(), _scrim_color(), SheetHost (+2 more)

### Community 52 - "Community 52"
Cohesion: 0.09
Nodes (9): _IniMemo, issue_text(), _backup_ini(), test_ini_is_found_in_the_backup_folder_with_one_lookup(), test_ini_is_found_under_the_machines_own_job_folder_name(), test_missing_ini_falls_back_to_every_root_and_a_move_flag_means_moved_only(), test_report_without_any_job_keeps_its_rows_and_builds_no_ini_path(), test_rows_for_report_flags_mismatch_and_reversed_time() (+1 more)

### Community 53 - "Community 53"
Cohesion: 0.13
Nodes (11): default_out_dir(), load_tool(), ToolOutdated, WaferLogsWorker, _run(), _snapshot(), test_worker_collects_through_the_scope_gate(), test_worker_names_an_outdated_tool_file() (+3 more)

### Community 54 - "Community 54"
Cohesion: 0.11
Nodes (21): Aa(), Animation(), Ba(), Ca(), Da(), ea(), FlipBatch(), FlipState() (+13 more)

### Community 55 - "Community 55"
Cohesion: 0.20
Nodes (15): _bundle(), _layout(), _marker(), _mk(), test_first_run_uses_the_console_python(), test_later_runs_are_windowless(), test_missing_console_python_falls_back_to_pythonw(), test_swap_applies_pending_update() (+7 more)

### Community 56 - "Community 56"
Cohesion: 0.10
Nodes (11): _numbers(), test_decision_numbers_are_unique_and_unbroken(), test_hook_reads_the_korean_file_name_correctly(), test_last_updated_line_is_present(), test_newest_work_log_entry_points_at_a_real_commit(), test_numbers_in_claude_md_match_the_code(), test_progress_doc_numbers_match_the_code(), test_required_section_exists() (+3 more)

### Community 57 - "Community 57"
Cohesion: 0.12
Nodes (16): rerun_args(), _bat(), test_cli_never_execs(), test_default_runner_uses_subprocess_run_and_propagates_returncode(), fake_run(), test_main_with_update_reruns_once_as_a_child_and_does_not_collect_in_the_parent(), fake_run(), test_main_without_a_new_version_collects_in_place() (+8 more)

### Community 58 - "Community 58"
Cohesion: 0.19
Nodes (12): _attach_dirs(), _dedupe_sort(), devices_from_csv(), devices_from_rows(), discover_devices(), _discover_under(), _log(), _norm_root() (+4 more)

### Community 59 - "Community 59"
Cohesion: 0.11
Nodes (16): main(), _print(), _progress_printer(), cb(), rerun_without_update(), check_or_raise(), fatal(), _cli_config() (+8 more)

### Community 60 - "Community 60"
Cohesion: 0.13
Nodes (14): _app_root(), check_for_update(), current_version(), ensure_version_file(), _git_head(), _git_head_ref(), _identity(), is_git_checkout() (+6 more)

### Community 61 - "Community 61"
Cohesion: 0.12
Nodes (9): _fake_out(), _load(), test_run_build_lite_with_fakes(), test_verify_checks_pass_on_valid_lite_output(), test_verify_full_requires_packages_and_marker(), test_verify_lite_rejects_marker_and_internal(), test_verify_rejects_big_launcher_and_missing_template_placeholder(), test_version_stamp_json() (+1 more)

### Community 62 - "Community 62"
Cohesion: 0.12
Nodes (12): categories(), find_subdir(), is_placeholder(), name_day(), norm_root(), read_bytes(), scan_dirs(), survey_device() (+4 more)

### Community 63 - "Community 63"
Cohesion: 0.17
Nodes (13): apply_to_app(), color_mode(), colors(), normalize_color_mode(), palettes(), parse_template_tokens(), render_qss(), set_color_mode() (+5 more)

### Community 64 - "Community 64"
Cohesion: 0.15
Nodes (13): _bundled_python(), _discard(), _ensure_deps(), _file_text(), _install_root(), _move(), _pending_dir(), _promote_in_place() (+5 more)

### Community 65 - "Community 65"
Cohesion: 0.16
Nodes (9): build(), graphify_cmds(), inline_scripts(), main(), write_inline_js(), changed_files(), check(), is_code() (+1 more)

### Community 66 - "Community 66"
Cohesion: 0.21
Nodes (10): _q(), download(), git(), git_update(), is_git_repo(), main(), _opener(), repo_root() (+2 more)

### Community 67 - "Community 67"
Cohesion: 0.15
Nodes (14): scandir(), _list_files(), ms_since(), op_isdir(), op_isfile(), op_open_read(), op_os_read_once(), resolve_wafer() (+6 more)

### Community 68 - "Community 68"
Cohesion: 0.15
Nodes (4): _card(), _label(), ModeCard, _repolish()

### Community 69 - "Community 69"
Cohesion: 0.16
Nodes (9): _ask(), _ask_int(), _ask_levels(), _ask_yes(), Deadline, interactive(), main(), _pause() (+1 more)

### Community 70 - "Community 70"
Cohesion: 0.18
Nodes (17): allocate(), log(), now_s(), _run(), run_cmd(), _run_level(), one(), _run_real() (+9 more)

### Community 71 - "Community 71"
Cohesion: 0.11
Nodes (13): _is_placeholder(), job_folder_variants(), _job_setup_by_table_lot(), lot_tokens(), scan_type(), test_job_folder_variants_are_exact_names_in_order(), test_job_setup_by_table_lot(), test_norm_status() (+5 more)

### Community 72 - "Community 72"
Cohesion: 0.25
Nodes (9): CollectorWorker, _collect_signals(), test_csv_lock_completes_with_warnings_not_failed(), locked(), test_failure_is_reported_not_raised(), test_html_lock_is_still_reported_as_failure(), test_run_emits_done_with_result(), test_stop_before_run_emits_cancelled_and_leaves_no_cache() (+1 more)

### Community 73 - "Community 73"
Cohesion: 0.19
Nodes (7): collect_lot(), is_bundle(), pack_lot_all(), Packer, recipe_mode(), safe(), stamp()

### Community 74 - "Community 74"
Cohesion: 0.17
Nodes (16): addDays(), buildModel(), buildModelLegacy(), buildModelV3(), causeOf(), causeText(), cmpDev(), devSortKey() (+8 more)

### Community 75 - "Community 75"
Cohesion: 0.21
Nodes (11): _full(), _make_zip(), _patch_download(), test_git_update_reports_already_up_to_date(), test_git_update_stops_when_working_tree_is_dirty(), fake_git(), test_main_uses_zip_when_folder_is_not_a_git_checkout(), test_zip_update_check_only_changes_nothing() (+3 more)

### Community 76 - "Community 76"
Cohesion: 0.15
Nodes (9): _issue_dec(), parse_issue_codes(), render_issue_rows(), _cache_rows(), test_cache_keeps_codes_only_and_outputs_carry_the_sentence(), test_issue_field_round_trips_params_with_separators_paths_and_hangul(), test_issue_text_renders_known_codes_and_keeps_unknown_ones_raw(), test_old_free_text_rows_and_new_coded_rows_coexist_and_wording_changes_need_no_recollection() (+1 more)

### Community 77 - "Community 77"
Cohesion: 0.19
Nodes (8): candidates(), load(), normalize(), _read(), test_load_picks_the_latest_saved_among_data_folder_and_downloads(), test_normalize_drops_bad_and_duplicate_entries(), test_write_html_embeds_recipe_groups(), _w()

### Community 78 - "Community 78"
Cohesion: 0.13
Nodes (3): _DaysWorker, _HtmlOnlyWorker, _PlanWorker

### Community 79 - "Community 79"
Cohesion: 0.18
Nodes (8): _stage_tree(), _verify_staged(), _write_version(), _write_version_to(), _fake_repo(), test_staging_real_tree_passes_verification_and_top_level_equals_allow_list(), test_staging_top_level_equals_allow_list_even_with_junk_in_source_root(), test_verify_rejects_unexpected_top_level_entry()

### Community 80 - "Community 80"
Cohesion: 0.16
Nodes (12): _build_html(), _embedded(), _fixture_rows(), _meta(), _open_rows_page(), page(), rdl2_page(), rdl_page() (+4 more)

### Community 81 - "Community 81"
Cohesion: 0.19
Nodes (7): _fingerprint(), _load(), test_build_produces_one_closed_file_whose_logic_parses(), test_build_writes_only_where_it_is_told(), test_camel_attrs_are_encoded_only_in_markup_not_in_the_script(), test_offline_variant_waits_for_window_data_instead_of_fetching(), _tracked_design_files_untouched()

### Community 82 - "Community 82"
Cohesion: 0.20
Nodes (10): _make_rdl(), _rows(), test_multi_ignores_the_waferinfo_name_and_report_only_rows_stay_unknown(), test_multi_scan_reads_every_recipe_from_recipesinfo(), test_rdl_patch_reads_only_the_wafer_inis_of_rdl_rows_missing_the_mode(), test_recipesinfo_is_only_opened_at_the_exact_wafer_folder(), test_recipesinfo_is_read_only_for_rdl_jobs(), test_single_scan_takes_the_waferinfo_recipe_over_the_report_column() (+2 more)

### Community 83 - "Community 83"
Cohesion: 0.20
Nodes (8): decode(), decrypt_bytes(), _enc_secret(), encrypt_bytes(), _keystream(), main(), parse_args(), say()

### Community 84 - "Community 84"
Cohesion: 0.22
Nodes (6): build(), bundle_template(), encode_camel_attrs(), main(), offline_variant(), _res()

### Community 85 - "Community 85"
Cohesion: 0.23
Nodes (6): _FakeBuild, _out(), _polluted(), test_no_zip_when_verification_fails(), test_polluted_dist_ships_no_cache_log_or_backup_but_keeps_runtime(), test_zip_layout_and_instructions()

### Community 86 - "Community 86"
Cohesion: 0.22
Nodes (6): app_paths(), _error(), launch_cmd(), Layout, main(), swap_pending()

### Community 87 - "Community 87"
Cohesion: 0.21
Nodes (13): _assertThisInitialized(), bt(), ic(), jt(), ta(), te(), Timeline(), Tween() (+5 more)

### Community 88 - "Community 88"
Cohesion: 0.19
Nodes (6): content_sha(), entries(), test_every_archived_file_matches_its_original_fingerprint(), test_everything_under_archive_is_listed(), test_manifest_has_entries_and_no_duplicates(), test_no_compiled_python_is_tracked()

### Community 89 - "Community 89"
Cohesion: 0.20
Nodes (7): ensure_kla_rows(), read_devices_csv(), write_devices_csv(), test_read_csv_cp949_and_utf8_and_aliases(), test_read_csv_without_header_and_comments(), test_write_then_read_roundtrip(), test_existing_devices_csv_gets_the_eight_kla_rows_once()

### Community 90 - "Community 90"
Cohesion: 0.17
Nodes (7): ctx, fs, html, input, path, stub(), vm

### Community 91 - "Community 91"
Cohesion: 0.30
Nodes (8): collect_files(), instructions_text(), _load_build_module(), main(), make_zip(), read_version(), should_include(), zip_basename()

### Community 92 - "Community 92"
Cohesion: 0.27
Nodes (9): pick(), run(), collect_one(), done_ok(), limit_reached(), run_all(), run_wide(), take() (+1 more)

### Community 93 - "Community 93"
Cohesion: 0.33
Nodes (11): navBox(), navCancel(), navGo(), navInd(), navNow(), navParts(), navRest(), navSet() (+3 more)

### Community 94 - "Community 94"
Cohesion: 0.18
Nodes (7): _gate_info(), manual_check(), test_check_and_manual_hold_when_ci_not_passed(), test_manual_check_reports_tls_failure(), test_manual_check_statuses(), test_ssl_verify_failure_stops_check_with_reason_and_no_retry(), _VerifyFailOpener

### Community 95 - "Community 95"
Cohesion: 0.22
Nodes (9): analyze(), _diff(), dist(), _dt_of(), med_ci(), parse_ini_bytes(), pct(), stage_times() (+1 more)

### Community 96 - "Community 96"
Cohesion: 0.24
Nodes (5): _collect_log(), _version_info(), version_text(), test_collect_writes_a_detailed_log_to_app_log_and_not_into_the_html(), test_version_text_reads_sha_and_branch()

### Community 97 - "Community 97"
Cohesion: 0.29
Nodes (5): ensure_html(), exists(), html_path(), last_collect_time(), test_ensure_html_creates_openable_file_without_collecting()

### Community 99 - "Community 99"
Cohesion: 0.36
Nodes (6): _cfg(), _embedded(), _model(), test_a_chosen_period_draws_only_its_days_and_matches_the_whole_file(), test_default_html_is_the_last_html_days_of_the_data_in_one_file(), test_html_from_cache_needs_no_nas_and_keeps_report_paths()

### Community 100 - "Community 100"
Cohesion: 0.22
Nodes (7): file_times(), _ft(), op_find_exact(), op_getattr(), op_win_createfile_read(), _win(), win_find()

### Community 101 - "Community 101"
Cohesion: 0.33
Nodes (6): check_rows(), probe(), probe(), _has_report(), _is_kla_root(), _probe_auto()

### Community 102 - "Community 102"
Cohesion: 0.22
Nodes (5): expand_roots(), normalize(), _share_root(), _unc_for_drive(), test_expand_roots_adds_share_root_for_unc()

### Community 105 - "Community 105"
Cohesion: 0.22
Nodes (5): _open_recipe(), test_recipe_close_point_labels_do_not_overlap(), test_recipe_device_row_opens_popup_with_keyboard_and_row_stays_same_node(), test_recipe_how_summary_and_details_are_accessible(), test_recipe_no_match_clearly_identifies_retained_or_empty_detail()

### Community 107 - "Community 107"
Cohesion: 0.25
Nodes (3): find_pattern(), FoundEntry, _Stat

### Community 109 - "Community 109"
Cohesion: 0.54
Nodes (6): _example(), _public(), test_every_default_config_key_is_in_the_example_or_explicitly_excused(), test_example_loads_through_the_cli_loader(), test_example_public_keys_are_a_subset_of_default_config_with_the_same_types(), test_example_scope_and_workers_show_the_real_defaults()

### Community 115 - "Community 115"
Cohesion: 0.29
Nodes (4): job_folder_variants(), lot_dir_of(), read_lot_all(), submit()

### Community 119 - "Community 119"
Cohesion: 0.50
Nodes (5): Context(), Db(), Eb(), Et(), fb()

## Knowledge Gaps
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `collect()` connect `Community 9` to `Community 2`, `Community 4`, `Community 5`, `Community 7`, `Community 14`, `Community 26`, `Community 27`, `Community 28`, `Community 37`, `Community 38`, `Community 39`, `Community 41`, `Community 46`, `Community 50`, `Community 52`, `Community 57`, `Community 58`, `Community 59`, `Community 72`, `Community 76`, `Community 82`, `Community 96`, `Community 99`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `collect()` (e.g. with `read_one()` and `test_zero_new_rows_but_state_change_still_saves()`) actually correct?**
  _`collect()` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.0180857310628303 - nodes in this community are weakly interconnected._
- **Why does `make_cfg()` connect `Community 2` to `Community 96`, `Community 26`, `Community 5`, `Community 38`, `Community 7`, `Community 72`, `Community 9`, `Community 41`, `Community 39`, `Community 76`, `Community 46`, `Community 14`, `Community 48`, `Community 82`, `Community 53`, `Community 58`, `Community 27`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.0612859097127223 - nodes in this community are weakly interconnected._
- **Why does `CollectPage` connect `Community 32` to `Community 35`, `Community 68`, `Community 103`, `Community 13`, `Community 78`, `Community 120`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.05266106442577031 - nodes in this community are weakly interconnected._