# Browser tools and session recording

A Python program adds `Tool(name="browser_tool_set")` (or `Tool(name=BrowserToolSet.name)`, or `get_default_tools(enable_browser=True)`) to its agent. When the conversation resolves it, `BrowserToolSet.create()` starts one `BrowserToolExecutor` (a `browser-use` server driving a local Chromium over CDP) and returns 14 tools that share it: `browser_navigate`, `browser_click`, `browser_type`, `browser_get_state`, `browser_get_content`, `browser_scroll`, `browser_go_back`, `browser_list_tabs`, `browser_switch_tab`, `browser_close_tab`, `browser_get_storage`, `browser_set_storage`, `browser_start_recording` and `browser_stop_recording`. The executor is a class-level singleton, so sub-agents reuse the parent's browser. Chromium is found on `PATH`, in standard install locations or in the Playwright cache; if it cannot start, the conversation goes on without browser tools and without the browser prompt guidance. Each action has a timeout, repeated infrastructure failures restart the browser session, and observations carry page text plus an optional screenshot that is sent to the LLM as an image and saved to disk. Recording injects rrweb into every page, flushes captured events every 5 seconds to numbered JSON files under `.agent_tmp/browser_observations/recording-<timestamp>/`, and returns event and file counts on stop. `conversation.close()` closes the browser.

Source: `openhands-tools/openhands/tools/browser_use/`, `openhands-tools/openhands/tools/preset/default.py`, `openhands-sdk/openhands/sdk/tool/defaults.py`

Needs: `chromium` (every real browser action), `llm` (examples, t05, t06), `network` (example 15, example 38, t06; recording loads rrweb from unpkg.com)

Examples: `examples/01_standalone_sdk/15_browser_use.py`, `examples/01_standalone_sdk/38_browser_session_recording.py`

## Sub-features

- `S15.toolset-create`: `BrowserToolSet.create(conv_state)` returns the 14 browser tools, all bound to one executor, each with the browser prompt guidance and an MCP-convertible schema; the set takes no LLM-facing parameters and is registered on import. Unit: `tests/tools/browser_use/test_browser_toolset.py` (`test_browser_toolset_create_includes_all_browser_tools`, `test_browser_toolset_create_tools_have_shared_executor`, `test_browser_toolset_create_tools_can_generate_mcp_schema`), `tests/cross/test_automatic_registration.py::test_browser_tool_automatic_registration`. Example: `examples/01_standalone_sdk/15_browser_use.py`. Real-LLM: `tests/integration/tests/t05_simple_browsing.py`.
- `S15.shared-executor`: repeated `create()` calls (parent and sub-agents) reuse one executor; construction is serialized without holding the shared lock; a second call's executor config is ignored with a warning; a closing executor is waited for before a new one is built. Unit: `tests/tools/browser_use/test_browser_toolset.py` (`test_browser_toolset_create_multiple_calls_share_executor`, `test_browser_toolset_shared_executor_survives_multiple_subagents`, `test_browser_toolset_warns_when_config_ignored`, `test_browser_toolset_create_waits_for_shared_executor_close`). Example: none. Real-LLM: none.
- `S15.degrade-on-failure`: when the executor fails to start, `create()` logs a warning and returns no tools, tool resolution for the rest of the agent succeeds, and the system prompt drops the browser guidance; a profile pinned to the browser still resolves on a browserless runtime. Unit: `tests/tools/browser_use/test_browser_toolset.py` (`test_browser_toolset_create_degrades_when_executor_fails`, `test_resolve_tool_survives_browser_executor_failure`, `test_no_browser_guidance_when_browser_fails_to_start`, `test_migrated_profile_with_pinned_browser_resolves_on_browserless_runtime`). Example: none. Real-LLM: none.
- `S15.chromium-detection`: `BrowserToolExecutor.check_chromium_available()` (cached) finds `google-chrome`, `chrome`, `chromium`, `chromium-browser` or `microsoft-edge` on `PATH`, standard Linux, macOS and Windows install paths (Edge on Windows), or Playwright's cache, and returns `None` otherwise; `BrowserToolSet.is_usable()` and `list_usable_tools()` follow it; a missing binary raises with install instructions (`uvx playwright install chromium`). Unit: `tests/tools/browser_use/test_chromium_detection.py`, `tests/cross/test_automatic_registration.py::test_browser_tool_usable_listing_respects_chromium_availability`. Example: none. Real-LLM: none.
- `S15.executor-config`: `headless`, `allowed_domains`, `session_timeout_minutes`, `init_timeout_seconds`, `action_timeout_seconds` (must be positive), `inject_scripts` and extra keyword arguments reach the browser-use server; each executor gets its own profile directory unless `user_data_dir` is given; initialization is lazy and idempotent and times out cleanly. Unit: `tests/tools/browser_use/test_browser_executor.py` (`test_browser_executor_config_passing`, `test_browser_executor_rejects_non_positive_action_timeout`, `test_browser_executor_initialization_lazy`, `test_browser_executor_initialization_idempotent`), `tests/tools/browser_use/test_browser_initialization.py`. Example: none. Real-LLM: none.
- `S15.action-routing`: each action type is routed to its server method, an unsupported action and a raised exception come back as error observations, and a slow action is cut off at `action_timeout_seconds`. Unit: `tests/tools/browser_use/test_browser_executor.py` (`test_browser_executor_action_routing_*`, `test_browser_executor_unsupported_action_handling`, `test_browser_executor_error_wrapping`, `test_browser_executor_timeout_wrapping_live_service`). Example: none. Real-LLM: none.
- `S15.session-recovery`: consecutive infrastructure failures reset the browser session and shorten the timeout until a success resets the counter; ordinary action errors do not count. Unit: `tests/tools/browser_use/test_browser_executor.py` (`test_issue_2412_consecutive_failures_reset_session`, `test_issue_2412_success_resets_failure_counter`, `test_issue_2412_action_errors_do_not_trigger_reset`, `test_issue_2412_degraded_timeout_after_failures`). Example: none. Real-LLM: none.
- `S15.navigate-and-read`: `browser_navigate` (optionally in a new tab), `browser_get_state` (indexed interactive elements, optional screenshot), `browser_get_content` (markdown, `extract_links`, `start_from_char` paging), `browser_scroll` and `browser_go_back` work on a real page. Unit: `tests/tools/browser_use/test_browser_executor_e2e.py` (`test_navigate_action`, `test_get_state_action`, `test_get_state_with_screenshot`, `test_get_content_action`, `test_scroll_action`, `test_go_back_action`; skipped without Chromium). Example: `examples/01_standalone_sdk/15_browser_use.py`. Real-LLM: `tests/integration/tests/t05_simple_browsing.py`, `tests/integration/tests/t06_github_pr_browsing.py`.
- `S15.interact`: `browser_click` (by element index, optionally into a new tab) and `browser_type` change a real page, and concurrent actions on one executor stay consistent. Unit: `tests/tools/browser_use/test_browser_executor_e2e.py` (`test_click_action`, `test_type_action`, `test_concurrent_actions`; skipped without Chromium). Example: none. Real-LLM: `tests/integration/tests/t05_simple_browsing.py`.
- `S15.tabs`: `browser_list_tabs`, `browser_switch_tab` and `browser_close_tab` manage tabs by id. Unit: `tests/tools/browser_use/test_browser_executor_e2e.py` (`test_navigate_new_tab`, `test_list_tabs_action`, `test_switch_tab_action`, `test_close_tab_action`; skipped without Chromium). Example: none. Real-LLM: none.
- `S15.storage`: `browser_get_storage` returns cookies and local/session storage and `browser_set_storage` restores a saved `storage_state`. Unit: `tests/tools/browser_use/test_browser_executor_e2e.py` (`test_get_storage_action`, `test_set_storage_action`; skipped without Chromium). Example: none. Real-LLM: none.
- `S15.observation`: `BrowserObservation` renders text or error, turns `screenshot_data` into an image content item with the detected MIME type, truncates long text, handles an empty screenshot, and writes the screenshot as `browser_screenshot_<hash>.<ext>` to the conversation's observation directory. Unit: `tests/tools/browser_use/test_browser_observation.py`, `tests/tools/browser_use/test_browser_executor_e2e.py::TestBrowserExecutorE2E::test_save_screenshot` (skipped without Chromium). Example: none. Real-LLM: none.
- `S15.recording-start-stop`: `browser_start_recording` initializes the browser and injects rrweb; `browser_stop_recording` returns a summary with event and file counts; stopping without a recording is an error. Unit: `tests/tools/browser_use/test_browser_executor.py` (`test_start_recording_initializes_session`, `test_stop_recording_returns_summary_with_event_counts`, `test_stop_recording_without_active_session_returns_error`), `tests/tools/browser_use/test_browser_executor_e2e.py` (`test_start_recording`, `test_stop_recording_without_start`, `test_recording_captures_events`, `test_recording_save_to_file`; skipped without Chromium). Example: `examples/01_standalone_sdk/38_browser_session_recording.py`. Real-LLM: none.
- `S15.recording-storage`: events flush periodically (`flush_interval_seconds`, default 5) into numbered, timestamped JSON chunks; each recording gets its own `recording-<timestamp>` subfolder; concurrent flushes do not corrupt the buffer; the reported file count matches the files on disk. Unit: `tests/tools/browser_use/test_recording_flush.py`. Example: `examples/01_standalone_sdk/38_browser_session_recording.py`. Real-LLM: none.
- `S15.cleanup`: `executor.close()` (and `__del__`) closes all browser sessions, falls back to `close_browser`, always stops the async executor, releases the shared executor, and serializes concurrent closes; `conversation.close()` triggers it. Unit: `tests/tools/browser_use/test_browser_cleanup.py`, `tests/tools/browser_use/test_browser_executor_e2e.py::TestBrowserExecutorE2E::test_executor_initialization_and_cleanup` (skipped without Chromium). Example: `examples/01_standalone_sdk/38_browser_session_recording.py`. Real-LLM: none.
- `S15.prompt-guidance`: the browser guidance renders once in the system prompt, before external-service guidance, and survives a custom system prompt and a persona. Unit: `tests/tools/browser_use/test_browser_toolset.py` (`test_browser_guidance_renders_once_before_external_services`, `test_custom_system_prompt_keeps_browser_guidance`, `test_persona_keeps_browser_guidance`). Example: none. Real-LLM: none.
- `S15.preset-browser`: `get_default_tools(enable_browser=True)` appends `browser_tool_set` before the sub-agent tool, `get_default_agent(llm, cli_mode=True)` leaves it out, and `register_builtins_agents(enable_browser=False)` skips the browser-only `web-researcher` sub-agent. Unit: `tests/sdk/tool/test_defaults.py::test_explicit_browser_appends_before_sub_agents`, `tests/cross/test_default_tool_names.py::test_browser_name_matches_browser_tool_set`, `tests/tools/test_builtin_agents.py::test_register_builtins_agents_skips_web_researcher_without_browser`. Example: `examples/01_standalone_sdk/15_browser_use.py`. Real-LLM: none.

## How to get to it (agent POV)

- `from openhands.tools.browser_use import BrowserToolSet`; `Agent(llm=..., tools=[Tool(name=BrowserToolSet.name)])`. Executor options go in `params`: `Tool(name=BrowserToolSet.name, params={"headless": False, "allowed_domains": ["example.com"], "action_timeout_seconds": 60})`. Covers every sub-feature.
- Presets: `get_default_tools(enable_browser=True)` and `get_default_agent(llm)` (browser on unless `cli_mode=True`). `S15.preset-browser`.
- Without the LLM: `conversation.execute_tool("browser_navigate", BrowserNavigateAction(url="about:blank"))` warms the browser before `run()` (example 38). Action classes import from `openhands.tools.browser_use.definition` (`BrowserNavigateAction`, `BrowserClickAction`, `BrowserGetStateAction`, `BrowserStartRecordingAction`, ...).
- Directly: `BrowserToolExecutor(headless=True, ...)` from `openhands.tools.browser_use.impl`, called with an action; `BrowserToolExecutor.check_chromium_available()` to probe.
- Files: screenshots under the conversation's observation persistence directory; recordings under `BROWSER_RECORDING_OUTPUT_DIR` (`.agent_tmp/browser_observations`, relative to the process working directory).
- Real-LLM runner: `tests/integration/run_infer.py --eval-ids t05_simple_browsing,t06_github_pr_browsing` (those tests set `enable_browser = True`).

## Driving it

Preconditions:

- `uv sync --dev` has run.
- For e2e and real-LLM bullets: a Chromium the detector finds, for example `uvx playwright install chromium` (needs `network`), or a system `chromium`. None is installed here.
- For real-LLM bullets: `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` exported.

- **Tool set, sharing, degradation, guidance, presets (`S15.toolset-create`, `S15.shared-executor`, `S15.degrade-on-failure`, `S15.prompt-guidance`, `S15.preset-browser`).** The executor is mocked.
  ```sh
  uv run pytest tests/tools/browser_use/test_browser_toolset.py tests/cross/test_automatic_registration.py tests/sdk/tool/test_defaults.py tests/cross/test_default_tool_names.py tests/tools/test_builtin_agents.py -q
  ```
  54 pass.
- **Detection, config, routing, recovery, observation, recording, cleanup (`S15.chromium-detection`, `S15.executor-config`, `S15.action-routing`, `S15.session-recovery`, `S15.observation`, `S15.recording-start-stop`, `S15.recording-storage`, `S15.cleanup`).** No browser needed.
  ```sh
  uv run pytest tests/tools/browser_use/test_chromium_detection.py tests/tools/browser_use/test_browser_initialization.py tests/tools/browser_use/test_browser_executor.py tests/tools/browser_use/test_browser_observation.py tests/tools/browser_use/test_recording_flush.py tests/tools/browser_use/test_browser_cleanup.py -q
  ```
  82 pass.
- **Real browser actions (`S15.navigate-and-read`, `S15.interact`, `S15.tabs`, `S15.storage`, `S15.observation`, `S15.recording-start-stop`, `S15.cleanup`), blocked here (needs `chromium`).** The file starts a local HTTP server and drives a headless browser.
  ```sh
  uvx playwright install chromium
  uv run pytest tests/tools/browser_use/test_browser_executor_e2e.py -q -rs
  ```
  Without Chromium all 22 tests are skipped with "Browser e2e tests require Chrome/Chromium or Playwright Chromium."; with it they pass.
- **Browsing with a real model (`S15.navigate-and-read`, `S15.interact`), blocked here (needs `chromium`, `llm`, `network`).**
  ```sh
  uv run python examples/01_standalone_sdk/15_browser_use.py
  uv run python tests/integration/run_infer.py --llm-config "{\"model\": \"$LLM_MODEL\"}" --eval-ids t05_simple_browsing,t06_github_pr_browsing
  ```
  The example prints a summary of the openhands.dev blog; t05 must answer from a page it serves on `localhost:8000`, t06 must describe a GitHub PR.
- **Recording with a real model (`S15.recording-start-stop`, `S15.recording-storage`), blocked here (needs `chromium`, `llm`, `network`).**
  ```sh
  uv run python examples/01_standalone_sdk/38_browser_session_recording.py
  ls .agent_tmp/browser_observations/
  ```
  The example prints the recording folder, file count, event count and rrweb event types; a `recording-<timestamp>` folder with JSON files appears.

## Gotchas

- `examples/01_standalone_sdk/15_browser_use.py` is in `_EXCLUDED_EXAMPLES` of `tests/examples/test_examples.py`, so CI never runs it; example 38 does run on the `test-examples` label and exits 1 if the browser cannot initialize.
- Recordings are written to `.agent_tmp/browser_observations/` relative to the process working directory, not under `persistence_dir`, although example 38's comments say "persistence directory". Folders from earlier runs stay there; the example reports only the newest `recording-*` folder by name.
- Recording loads rrweb from unpkg.com (`RecordingConfig.cdn_url`, 10 s load timeout); if the CDN is unreachable, `browser_start_recording` fails with an error message instead of recording.
- The executor is a class-level singleton (`BrowserToolSet._shared_executor`): in one process, a second conversation reuses the first browser and ignores new `params`. Tests reset it explicitly.
- A missing Chromium is not an error at agent build time: the tools silently disappear (warning only), and the agent works without them. Check `list_usable_tools()` or the warning before blaming the model.
- The integration runner never enables the browser for the default preset (skip in `tests/integration/test_tool_presets.py`, issue #2124 in its message); only t05 and t06 turn it on themselves. t05 binds port 8000 on 127.0.0.1.
- The `browser-use` dependency logs heavily; `openhands-tools/openhands/tools/browser_use/logging_fix.py` tames it, so expect fewer logs than browser-use's defaults.
