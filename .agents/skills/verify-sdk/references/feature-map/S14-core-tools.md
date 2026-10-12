# Core tools and tool presets

A Python program gives an agent its working tools by name: `Agent(llm=..., tools=[Tool(name="terminal"), Tool(name="file_editor"), Tool(name="task_tracker")])`, or through a preset (`get_default_agent(llm)`, `get_gpt5_agent(llm)`, `get_gemini_agent(llm)`, `get_default_tools()`, `get_gemini_tools()`). Importing a tool module registers it, and the conversation resolves each `Tool` spec into a live tool bound to `conversation.state.workspace.working_dir`. The terminal tool runs shell commands in a persistent session (tmux when available, else a plain subprocess shell, PowerShell on Windows), keeps `cd` and exported variables between calls, reports exit code and cwd in metadata, accepts `is_input=True` to type into a running process, `timeout` for a hard limit and `reset=True` for a fresh shell, and truncates long output while saving the full text. With tmux it keeps a pane pool so parallel terminal calls run side by side. The file editor (`view`, `create`, `str_replace`, `insert`, `undo_edit`) is the claude-style editor; `view` also returns images and PDFs. `apply_patch` (GPT-5 preset) applies an OpenAI-style `*** Begin Patch` envelope. The Gemini set (`read_file`, `write_file`, `edit`, `list_directory`) replaces the file editor in the Gemini preset. `glob` and `grep` are read-only search tools that use ripgrep and fall back to Python. Tool output passes through the conversation's secret masking.

Source: `openhands-tools/openhands/tools/terminal/`, `openhands-tools/openhands/tools/file_editor/`, `openhands-tools/openhands/tools/apply_patch/`, `openhands-tools/openhands/tools/gemini/`, `openhands-tools/openhands/tools/glob/`, `openhands-tools/openhands/tools/grep/`, `openhands-tools/openhands/tools/preset/`, `openhands-sdk/openhands/sdk/tool/defaults.py`

Needs: `llm` (examples and real-LLM tests), `tmux` (tmux backend and pane pool; without it the subprocess backend is used), `git` (t04), `network` (t08 downloads an image)

Examples: `examples/04_llm_specific_tools/01_gpt5_apply_patch_preset.py`, `examples/04_llm_specific_tools/02_gemini_file_tools.py` (most `examples/01_standalone_sdk/*` scripts also use `TerminalTool` and `FileEditorTool`)

## Sub-features

- `S14.terminal-exec`: a `TerminalAction(command=...)` runs in the workspace directory and returns a `TerminalObservation` with output, `exit_code` (also at top level), and `is_error` for a failing command; chained and multi-line commands, background servers and `cd` persist across calls. Unit: `tests/tools/terminal/test_terminal_tool.py`, `tests/tools/terminal/test_terminal_exit_code_top_level.py`, `tests/tools/terminal/test_terminal_session.py`. Example: `examples/04_llm_specific_tools/02_gemini_file_tools.py`. Real-LLM: `tests/integration/tests/t02_add_bash_hello.py`, `tests/integration/tests/t03_jupyter_write_file.py`, `tests/integration/tests/t04_git_staging.py`.
- `S14.terminal-backend-select`: `TerminalTool.create(conv_state, terminal_type=None|"tmux"|"subprocess"|"powershell", shell_path=...)` picks tmux when installed, else subprocess, and PowerShell on Windows; `shell_path` picks the shell binary for the subprocess backend; an invalid working directory raises `ValueError`. Unit: `tests/tools/terminal/test_terminal_tool_auto_detection.py`, `tests/tools/terminal/test_session_factory.py`, `tests/tools/terminal/test_shell_path_configuration.py`. Example: none. Real-LLM: none.
- `S14.terminal-interactive`: `is_input=True` sends text or control keys (`C-c`, `C-d`, arrows) to a running process; a command that is still running reports that it is waiting and the next call continues it. Unit: `tests/tools/terminal/test_send_keys.py`, `tests/tools/terminal/test_terminal_session.py::test_interactive_command`, `::test_ctrl_c`, `::test_python_interactive_input`. Example: `examples/01_standalone_sdk/06_interactive_terminal_w_reasoning.py` (excluded from CI). Real-LLM: `tests/integration/tests/t07_interactive_commands.py`.
- `S14.terminal-timeout`: a command that produces no new output for `no_change_timeout_seconds` returns control with a "still running" note; an explicit `timeout` is a hard limit and is rejected above 90% of `OH_RUNTIME_IDLE_TIMEOUT_SECONDS` when that variable is set. Unit: `tests/tools/terminal/test_timeout_policy.py`, `tests/tools/terminal/test_terminal_session.py::test_long_running_command_follow_by_execute`, `::test_no_change_timeout_strips_heredoc_wrapper`. Example: none. Real-LLM: none.
- `S14.terminal-reset`: `reset=True` kills the session and starts a fresh shell in the working directory; a reset combined with `is_input` is rejected. Unit: `tests/tools/terminal/test_terminal_reset.py`. Example: none. Real-LLM: none.
- `S14.terminal-pane-pool`: with tmux the executor runs a pane pool (`is_pooled`), declares no shared resource key so parallel terminal calls run concurrently, and rebuilds a broken pool; `terminal_type="subprocess"` turns pool mode off. Unit: `tests/tools/terminal/test_tmux_pane_pool.py`, `tests/tools/terminal/test_pool_integration.py`. Example: `examples/01_standalone_sdk/45_parallel_tool_execution.py`. Real-LLM: none.
- `S14.terminal-env`: exported variables persist in the session, the parent environment is inherited, `TerminalTool.create(..., env={...})` adds client-controlled variables, and a very large environment does not break startup. Unit: `tests/tools/terminal/test_terminal_session.py::test_environment_variable_persistence`, `::test_environment_variable_inheritance_from_parent`, `tests/tools/terminal/test_large_environment.py`. Example: none. Real-LLM: none.
- `S14.terminal-output-truncation`: long output is truncated for the LLM with metadata kept, and the full output is written under the conversation's observation persistence directory (`full_output_save_dir`). Unit: `tests/tools/terminal/test_observation_truncation.py`, `tests/tools/terminal/test_terminal_session.py::test_session_truncates_large_command_output`, `::test_truncation_preserves_metadata_in_llm_content`. Example: none. Real-LLM: none.
- `S14.terminal-metadata`: the PS1 marker carries cwd, exit code, username and Python interpreter into `CmdOutputMetadata`, and survives corrupted or interleaved prompts. Unit: `tests/tools/terminal/test_terminal_ps1_metadata.py`, `tests/tools/terminal/test_ps1_corruption.py`, `tests/tools/terminal/test_terminal_parsing.py`. Example: none. Real-LLM: none.
- `S14.terminal-input-encoding`: heredocs are sent in chunks and complete correctly, terminal escape sequences are filtered from output, and literal arguments that would be mangled by the shell are guarded. Unit: `tests/tools/terminal/test_heredoc_chunked_send.py`, `tests/tools/terminal/test_escape_filter.py`, `tests/tools/terminal/test_literal_arg_guard.py`. Example: none. Real-LLM: none.
- `S14.terminal-secret-masking`: secret values registered on the conversation are masked in terminal output and in tmux debug logs. Unit: `tests/tools/terminal/test_secrets_masking.py`, `tests/tools/terminal/test_tmux_log_redaction.py`. Example: `examples/01_standalone_sdk/12_custom_secrets.py`. Real-LLM: none.
- `S14.terminal-cleanup`: closing the conversation closes the terminal session (and tmux panes), and executor shutdown tolerates interpreter teardown. Unit: `tests/tools/terminal/test_conversation_cleanup.py`, `tests/tools/terminal/test_shutdown_handling.py`. Example: none. Real-LLM: none.
- `S14.terminal-windows`: the PowerShell backend runs commands, sends keys and handles Ctrl+C on Windows. Unit: `tests/tools/terminal/test_windows_terminal.py`, `tests/tools/terminal/test_windows_ctrl_c.py` (both skip off Windows), `tests/tools/terminal/test_windows_terminal_send_keys.py` (runs anywhere). Example: none. Real-LLM: none.
- `S14.file-editor-view`: `view` lists a directory (two levels, hidden files, symlinks, truncated when large), shows a file with line numbers or a `view_range`, and returns image and PDF content for supported binary files. Unit: `tests/tools/file_editor/test_basic_operations.py`, `tests/tools/file_editor/test_view_supported_binary_files.py`. Example: none. Real-LLM: `tests/integration/tests/t08_image_file_viewing.py` (needs a vision model).
- `S14.file-editor-edit`: `create` (fails on an existing file), `str_replace` (must match exactly once), `insert` at a line, and `undo_edit` (per-file history) change files and return a diff snippet. Unit: `tests/tools/file_editor/test_basic_operations.py`, `tests/tools/file_editor/test_file_editor_tool.py`, `tests/tools/file_editor/utils/test_history.py`, `tests/tools/file_editor/test_visualize_diff.py`. Example: `examples/01_standalone_sdk/01_hello_world.py`. Real-LLM: `tests/integration/tests/t01_fix_simple_typo.py`.
- `S14.file-editor-validation`: relative paths, missing files, binary files, oversized files and invalid parameters return error observations; paths resolve against the workspace root; non-UTF-8 files keep their encoding; memory use stays bounded on large files. Unit: `tests/tools/file_editor/test_file_validation.py`, `tests/tools/file_editor/test_error_handling.py`, `tests/tools/file_editor/test_exceptions.py`, `tests/tools/file_editor/test_workspace_root.py`, `tests/tools/file_editor/utils/test_encoding.py`, `tests/tools/file_editor/utils/test_file_cache.py`, `tests/tools/file_editor/test_memory_usage.py`. Example: none. Real-LLM: none.
- `S14.apply-patch`: `ApplyPatchAction(patch="*** Begin Patch ... *** End Patch")` adds, updates (context-matched hunks) and deletes files relative to the workspace and reports a `DiffError` for a bad patch. Unit: `tests/tools/apply_patch/test_apply_patch_executor.py`. Example: `examples/04_llm_specific_tools/01_gpt5_apply_patch_preset.py`. Real-LLM: `tests/integration/run_infer.py --tool-preset gpt5` (t01 to t08).
- `S14.gemini-file-tools`: `read_file` (offset and limit), `write_file`, `edit` (replace with expected occurrence count) and `list_directory` work on workspace paths, and concurrent calls on the same file are serialized by a shared file lock. Unit: `tests/tools/gemini/read_file/test_read_file.py`, `tests/tools/gemini/write_file/test_write_file.py`, `tests/tools/gemini/edit/test_edit.py`, `tests/tools/gemini/list_directory/test_list_directory.py`, `tests/tools/gemini/test_cross_tool_locking.py`. Example: `examples/04_llm_specific_tools/02_gemini_file_tools.py`. Real-LLM: `tests/integration/run_infer.py --tool-preset gemini`.
- `S14.glob`: `glob` matches a pattern under an optional path, returns paths sorted by modification time (capped), uses `rg --files` and falls back to Python `glob` with the same results. Unit: `tests/tools/glob/test_glob_tool.py`, `tests/tools/glob/test_glob_executor.py`, `tests/tools/glob/test_consistency.py`. Example: `examples/01_standalone_sdk/24_planning_agent_workflow.py` (planning preset). Real-LLM: none.
- `S14.grep`: `grep` searches file contents by regex with an `include` filter, returns matching files (capped), uses ripgrep and falls back to Python with the same results. Unit: `tests/tools/grep/test_grep_tool.py`, `tests/tools/grep/test_grep_executor.py`, `tests/tools/grep/test_consistency.py`. Example: `examples/01_standalone_sdk/24_planning_agent_workflow.py`. Real-LLM: none.
- `S14.tool-output-masking`: file editor views, the grep pattern, glob paths and apply_patch commit content are masked through one chokepoint when the conversation has secrets; without a conversation nothing is masked. Unit: `tests/tools/test_tool_output_secret_masking.py`. Example: none. Real-LLM: none.
- `S14.shared-working-dir`: terminal, file editor and other tools take their working directory from the conversation workspace and need no `params` for it. Unit: `tests/tools/test_working_dir_standardization.py`, `tests/cross/test_registry_directories.py`. Example: none. Real-LLM: none.
- `S14.preset-default`: `get_default_tools(enable_browser=..., enable_sub_agents=...)` returns `terminal`, `file_editor`, `task_tracker` (plus `browser_tool_set` and `task_tool_set` when asked); `get_default_agent(llm, cli_mode=...)` adds the default condenser, drops the browser in CLI mode and, with `finish_tool_response_schema`, registers a structured finish tool; the SDK's `default_tool_specs()` matches it. Unit: `tests/tools/test_preset_default.py`, `tests/sdk/tool/test_defaults.py`, `tests/cross/test_default_tool_names.py`, `tests/integration/test_tool_presets.py::test_get_tools_for_preset_default`. Example: `examples/01_standalone_sdk/24_planning_agent_workflow.py`. Real-LLM: every `tests/integration/tests/t*.py` with the default preset.
- `S14.preset-gpt5-gemini`: `get_gpt5_tools()` swaps `file_editor` for `apply_patch`, `get_gemini_tools()` swaps it for the four Gemini tools; `get_gpt5_agent(llm)` and `get_gemini_agent(llm)` wrap them with a condenser. Unit: `tests/integration/test_tool_presets.py` (tool lists only; the `get_*_agent` builders are not unit-tested). Example: `examples/04_llm_specific_tools/01_gpt5_apply_patch_preset.py`, `examples/04_llm_specific_tools/02_gemini_file_tools.py`. Real-LLM: `tests/integration/run_infer.py --tool-preset gpt5` / `--tool-preset gemini`.

## How to get to it (agent POV)

- Tool specs: `from openhands.sdk import Tool`; `Tool(name="terminal")`, `Tool(name="file_editor")`, `Tool(name="apply_patch")`, `Tool(name="read_file")` etc., `Tool(name="glob")`, `Tool(name="grep")`. Import the tool module first (`from openhands.tools.terminal import TerminalTool`) so it registers; use `TerminalTool.name` rather than a string. `Tool(name=..., params={...})` forwards keyword arguments to the tool's `create()` (for the terminal: `terminal_type`, `shell_path`, `no_change_timeout_seconds`, `username`, `env`). All sub-features.
- `from openhands.tools.gemini import GEMINI_FILE_TOOLS` is the list of four Gemini specs (`S14.gemini-file-tools`).
- Presets: `openhands.tools.preset.default` (`get_default_tools`, `get_default_agent`, `register_default_tools`), `openhands.tools.preset.gpt5` (`get_gpt5_tools`, `get_gpt5_agent`), `openhands.tools.preset.gemini` (`get_gemini_tools`, `get_gemini_agent`). `openhands.sdk.tool.default_tool_specs()` is the SDK-side default list. `S14.preset-*`.
- Direct use without an LLM: `TerminalExecutor(working_dir=..., terminal_type=...)` with `TerminalAction`, `FileEditorExecutor(workspace_root=...)` with `FileEditorAction`, or `conversation.execute_tool("terminal", TerminalAction(command="ls"))` on a live conversation.
- Environment: `OH_RUNTIME_IDLE_TIMEOUT_SECONDS` caps the terminal `timeout` (`S14.terminal-timeout`). The full output of truncated observations goes under the conversation's persistence directory (`Conversation(persistence_dir=...)`).
- Integration runner: `tests/integration/run_infer.py --tool-preset default|gemini|gpt5|planning --eval-ids t01_fix_simple_typo,...` builds the agent from `tests/integration/base.py::get_tools_for_preset`.

## Driving it

Preconditions:

- `uv sync --dev` has run.
- `tmux` and `rg` on `PATH` for the tmux and ripgrep paths (both present here); without them the subprocess and Python fallbacks are exercised instead.
- For real-LLM bullets: `LLM_API_KEY` and `LLM_BASE_URL` exported (the integration base class skips without both), and a model name for `--llm-config`.

- **Terminal execution, backends, interactive input, reset (`S14.terminal-exec`, `S14.terminal-backend-select`, `S14.terminal-interactive`, `S14.terminal-reset`, `S14.terminal-env`).** Real shells, no LLM.
  ```sh
  uv run pytest tests/tools/terminal/test_terminal_tool.py tests/tools/terminal/test_terminal_exit_code_top_level.py tests/tools/terminal/test_terminal_tool_auto_detection.py tests/tools/terminal/test_session_factory.py tests/tools/terminal/test_shell_path_configuration.py -q
  uv run pytest tests/tools/terminal/test_send_keys.py tests/tools/terminal/test_terminal_reset.py tests/tools/terminal/test_large_environment.py -q
  uv run pytest tests/tools/terminal/test_terminal_session.py -q --timeout 600
  ```
  36 and 33 pass; `test_terminal_session.py` runs 91 tmux and subprocess cases and takes about six minutes (91 passed in 358 s here).
- **Timeouts, pool, truncation, metadata, encoding, masking, cleanup (`S14.terminal-timeout`, `S14.terminal-pane-pool`, `S14.terminal-output-truncation`, `S14.terminal-metadata`, `S14.terminal-input-encoding`, `S14.terminal-secret-masking`, `S14.terminal-cleanup`).**
  ```sh
  uv run pytest tests/tools/terminal/test_timeout_policy.py tests/tools/terminal/test_observation_truncation.py tests/tools/terminal/test_terminal_ps1_metadata.py tests/tools/terminal/test_ps1_corruption.py tests/tools/terminal/test_terminal_parsing.py -q
  uv run pytest tests/tools/terminal/test_tmux_pane_pool.py tests/tools/terminal/test_pool_integration.py -q
  uv run pytest tests/tools/terminal/test_heredoc_chunked_send.py tests/tools/terminal/test_escape_filter.py tests/tools/terminal/test_literal_arg_guard.py tests/tools/terminal/test_secrets_masking.py tests/tools/terminal/test_tmux_log_redaction.py tests/tools/terminal/test_conversation_cleanup.py tests/tools/terminal/test_shutdown_handling.py -q
  ```
  87, 34 and 84 pass (the pane-pool files take about a minute).
- **Windows terminal (`S14.terminal-windows`), blocked on Linux (needs a Windows host).** Only the send-keys mapping runs here.
  ```sh
  uv run pytest tests/tools/terminal/test_windows_terminal_send_keys.py tests/tools/terminal/test_windows_terminal.py tests/tools/terminal/test_windows_ctrl_c.py -q
  ```
  27 pass and 15 are skipped (the two Windows-only files).
- **File editor (`S14.file-editor-view`, `S14.file-editor-edit`, `S14.file-editor-validation`).**
  ```sh
  uv run pytest tests/tools/file_editor -q
  ```
  168 pass.
- **apply_patch, Gemini tools, glob, grep (`S14.apply-patch`, `S14.gemini-file-tools`, `S14.glob`, `S14.grep`).**
  ```sh
  uv run pytest tests/tools/apply_patch tests/tools/gemini tests/tools/glob tests/tools/grep -q
  ```
  159 pass.
- **Masking, working dir, presets (`S14.tool-output-masking`, `S14.shared-working-dir`, `S14.preset-default`, `S14.preset-gpt5-gemini`).**
  ```sh
  uv run pytest tests/tools/test_tool_output_secret_masking.py tests/tools/test_working_dir_standardization.py tests/tools/test_preset_default.py tests/sdk/tool/test_defaults.py tests/cross/test_default_tool_names.py tests/cross/test_registry_directories.py tests/integration/test_tool_presets.py -q
  ```
  30 pass and 1 is skipped (`test_get_tools_for_preset_default_with_browser`, by design).
- **Presets with a real model (`S14.preset-gpt5-gemini`, `S14.apply-patch`, `S14.gemini-file-tools`).**
  ```sh
  uv run python examples/04_llm_specific_tools/01_gpt5_apply_patch_preset.py
  uv run python examples/04_llm_specific_tools/02_gemini_file_tools.py
  ```
  The first writes `GPT5_DEMO.txt` in the current directory; the second writes and then deletes `FACTS.txt` and logs completions under `logs/gemini`.
- **Real-LLM task tests (`S14.terminal-exec`, `S14.terminal-interactive`, `S14.file-editor-view`, `S14.file-editor-edit`).**
  ```sh
  uv run python tests/integration/run_infer.py --llm-config "{\"model\": \"$LLM_MODEL\"}" --eval-ids t01_fix_simple_typo,t02_add_bash_hello,t03_jupyter_write_file,t04_git_staging,t07_interactive_commands,t08_image_file_viewing
  uv run python tests/integration/run_infer.py --llm-config "{\"model\": \"$LLM_MODEL\"}" --tool-preset gpt5 --eval-ids t01_fix_simple_typo,t02_add_bash_hello
  uv run python tests/integration/run_infer.py --llm-config "{\"model\": \"$LLM_MODEL\"}" --tool-preset gemini --eval-ids t01_fix_simple_typo,t02_add_bash_hello
  ```
  Results and logs land under `tests/integration/outputs/`; each test reports success or a reason.

## Gotchas

- `tests/tools/terminal` as a whole runs well past 300 s; run it file by file or give `test_terminal_session.py` a longer timeout. Under heavy parallel load `tests/tools/terminal/test_terminal_session.py::test_session_truncates_multiline_output[subprocess]` failed once and passed on its own rerun (2 passed in 3.96 s), so treat it as timing-sensitive.
- The auto-detected backend depends on the host: with tmux installed every default `TerminalTool` uses the pane pool, and `TerminalExecutor.session` raises in pool mode. Force `terminal_type="subprocess"` to test the single-session path.
- Examples read `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`; the GPT-5 example also accepts `OPENAI_API_KEY` and defaults to `openai/gpt-5.1`, the Gemini example defaults to `gemini/gemini-3.1-pro-preview`. `tests/examples/test_examples.py` pins them to `openhands/gpt-5.1` and `openhands/gemini-3.1-pro-preview` (`_LLM_SPECIFIC_EXAMPLES`). Both examples write into the current directory.
- `examples/01_standalone_sdk/06_interactive_terminal_w_reasoning.py` and `01_hello_world.py` are in `_EXCLUDED_EXAMPLES`, so CI never runs them.
- Integration tests need both `LLM_API_KEY` and `LLM_BASE_URL`; `--llm-config` must be JSON. t08 skips unless the model supports vision and downloads an image from python.org; t04 needs `git`; t03 asks for "Jupyter IPython" but there is no Jupyter tool, so the agent uses the terminal.
- The integration runner never enables the browser for the default preset (`test_get_tools_for_preset_default_with_browser` is skipped, issue #2124 in the skip message), so presets there run without browser tools.
- Truncated terminal output and browser screenshots are saved only when the conversation has a `persistence_dir`; `env_observation_persistence_dir` is `None` otherwise and the full text is dropped.
- `glob` with the Python fallback uses a process-wide `os.chdir`, so it declares itself not parallel-safe; with ripgrep it is.
