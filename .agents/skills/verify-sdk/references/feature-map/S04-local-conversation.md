# Local conversation lifecycle

A Python program calls `Conversation(agent=..., workspace=...)` with a local workspace (a path string or `LocalWorkspace`) and gets a `LocalConversation` that runs the agent in the same process. Around the step loop (family S01) it owns the conversation's lifecycle: a stable `conversation.id`, optional on-disk persistence under `persistence_dir/<id.hex>/` (`base_state.json` plus one `events/event-NNNNN-<event_id>.json` per event) that a second `Conversation(..., persistence_dir=..., conversation_id=same_id)` reloads and continues, `pause()` from another thread, `arun()` on an asyncio loop with `interrupt()` cancelling mid-LLM-call, `update_secrets(...)` that inject values as environment variables into terminal commands and mask them in output, a pluggable visualizer (Rich console output by default, `visualizer=None` for silence), `fork()` into an independent copy or a branch from a chosen event, and `close()`. Helpers next to it read results out of a finished conversation: `get_agent_final_response(events)`, `conversation.conversation_stats` (per-`usage_id` LLM metrics), `generate_title()`, and `run_goal(...)`, which re-prompts the agent until a second judge LLM agrees an objective is complete.

Source: `openhands-sdk/openhands/sdk/conversation/conversation.py`, `openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py`, `openhands-sdk/openhands/sdk/conversation/base.py`, `openhands-sdk/openhands/sdk/conversation/state.py`, `openhands-sdk/openhands/sdk/conversation/persistence_const.py`, `openhands-sdk/openhands/sdk/conversation/cancellation.py`, `openhands-sdk/openhands/sdk/conversation/secret_registry.py`, `openhands-sdk/openhands/sdk/conversation/visualizer/`, `openhands-sdk/openhands/sdk/conversation/goal/`, `openhands-sdk/openhands/sdk/conversation/response_utils.py`, `openhands-sdk/openhands/sdk/conversation/conversation_stats.py`, `openhands-sdk/openhands/sdk/conversation/title_utils.py`, `openhands-sdk/openhands/sdk/conversation/types.py`, `openhands-sdk/openhands/sdk/secret/`, `openhands-sdk/openhands/sdk/utils/async_utils.py`

Needs: `llm`, `tmux`, `network`, `uvx`

Examples: `examples/01_standalone_sdk/06_interactive_terminal_w_reasoning.py`, `examples/01_standalone_sdk/09_pause_example.py`, `examples/01_standalone_sdk/10_persistence.py`, `examples/01_standalone_sdk/11_async.py`, `examples/01_standalone_sdk/12_custom_secrets.py`, `examples/01_standalone_sdk/26_custom_visualizer.py`, `examples/01_standalone_sdk/48_conversation_fork.py`, `examples/01_standalone_sdk/50_async_cancellation.py`, `examples/01_standalone_sdk/54_goal_completion_loop.py`

## Sub-features

- `S04.factory`: `Conversation(...)` returns a `LocalConversation` for a path or `LocalWorkspace` and a `RemoteConversation` for a `RemoteWorkspace`; `persistence_dir` is only accepted on the local branch. Unit: `tests/sdk/conversation/test_conversation_factory.py`. Example: `examples/01_standalone_sdk/10_persistence.py`. Real-LLM: every `tests/integration/tests/t*.py` builds a `LocalConversation` through `tests/integration/base.py`.
- `S04.conversation-id`: each conversation gets a unique UUID, a passed `conversation_id` is kept and persisted, and the id pins the LLM prompt-cache key. Unit: `tests/sdk/conversation/local/test_conversation_id.py`. Example: `examples/01_standalone_sdk/10_persistence.py`. Real-LLM: none.
- `S04.persist-events`: with `persistence_dir`, every event is written as `events/event-NNNNN-<id>.json` and base state as `base_state.json` under `<persistence_dir>/<id.hex>/`, incrementally, with corrupted or missing files handled on load. Unit: `tests/sdk/conversation/local/test_state_serialization.py`, `tests/sdk/conversation/local/test_conversation_core.py`, `tests/cross/test_persistence_dir_call_sites.py`. Example: `examples/01_standalone_sdk/10_persistence.py`. Real-LLM: none.
- `S04.resume`: a new `Conversation` with the same `persistence_dir` and `conversation_id` reloads the events and state and continues the dialogue with full memory. Unit: `tests/sdk/conversation/local/test_state_serialization.py::test_conversation_state_persistence_save_load`, `tests/cross/test_conversation_restore_behavior.py::test_conversation_restore_lifecycle_happy_path`. Example: `examples/01_standalone_sdk/10_persistence.py`. Real-LLM: none.
- `S04.resume-agent-compat`: on resume, removing tools, removing default tools or changing the agent class fails; adding tools and changing the LLM, condenser or skills succeeds; security risk and summaries survive. Unit: `tests/cross/test_conversation_restore_behavior.py`. Example: none. Real-LLM: none.
- `S04.custom-file-store`: an injected `FileStore` takes precedence over `persistence_dir` for where state is written, while `persistence_dir` is still reported. Unit: `tests/sdk/conversation/local/test_custom_file_store.py`. Example: none. Real-LLM: none.
- `S04.callbacks`: `callbacks=[...]` receive every event after the default callback has persisted it; a persistence failure blocks downstream callbacks; the visualizer runs in a fixed order relative to user callbacks. Unit: `tests/sdk/conversation/local/test_conversation_default_callback.py`, `tests/sdk/conversation/local/test_conversation_visualize_param.py::test_conversation_callback_order`. Example: `examples/01_standalone_sdk/10_persistence.py`. Real-LLM: none.
- `S04.run-error`: an exception inside `run()` surfaces as `ConversationRunError` that names the conversation id, the persistence dir and the issue URL, and emits one `ConversationErrorEvent` (no duplicate when the agent already emitted one). Unit: `tests/sdk/conversation/local/test_run_exception_includes_conversation_id.py`. Example: none. Real-LLM: none.
- `S04.close`: `close()` closes tool executors (terminal sessions), is idempotent, unregisters its atexit hook, and with `delete_on_close=False` keeps executor state; `__del__` also closes. Unit: `tests/sdk/conversation/test_atexit_cleanup.py`, `tests/tools/terminal/test_conversation_cleanup.py`, `tests/sdk/conversation/local/test_conversation_core.py::test_close_propagates_agent_failure_and_allows_retry`. Example: none. Real-LLM: none.
- `S04.pause`: `pause()` from another thread moves RUNNING or IDLE to PAUSED, emits exactly one `PauseEvent`, takes effect between steps (not mid-LLM-call), and a later `run()` resumes. Unit: `tests/sdk/conversation/local/test_conversation_pause_functionality.py`, `tests/sdk/conversation/local/test_agent_status_transition.py::test_execution_status_transitions_to_running_from_paused`. Example: `examples/01_standalone_sdk/09_pause_example.py`. Real-LLM: `tests/integration/tests/c04_token_condenser.py` and `c05_size_condenser.py` call `pause()`.
- `S04.async-callback`: `AsyncCallbackWrapper(coro, loop)` lets a synchronous `run()` in an executor thread deliver events to a coroutine on the main loop. Unit: `tests/sdk/utils/test_async_utils.py`. Example: `examples/01_standalone_sdk/11_async.py`. Real-LLM: none.
- `S04.arun-interrupt`: `await conversation.arun()` uses the async LLM path; `interrupt()` (safe from a signal handler or another thread) cancels it at once, even mid-LLM-call, sets PAUSED, emits an `InterruptEvent`, does not raise `CancelledError`, and the conversation can be resumed; with no `arun()` in flight it falls back to `pause()`. Unit: `tests/sdk/conversation/test_interrupt.py`. Example: `examples/01_standalone_sdk/50_async_cancellation.py`. Real-LLM: none.
- `S04.cancel-token`: each `run()`/`arun()` gets a fresh `CancellationToken` that `interrupt()` sets before cancelling, so pending parallel tool calls are skipped. Unit: `tests/sdk/conversation/test_interrupt.py::test_interrupt_sets_cancel_token`, `::test_execute_batch_skips_all_on_pre_cancelled_token`. Example: `examples/01_standalone_sdk/50_async_cancellation.py`. Real-LLM: none.
- `S04.secrets-update`: `update_secrets({...})` accepts plain strings and `SecretSource` objects (resolved lazily when a command references the key), overwrites existing keys, and exports referenced keys as environment variables for terminal commands. Unit: `tests/sdk/conversation/test_secrets_manager.py`, `tests/sdk/conversation/test_secret_source.py`. Example: `examples/01_standalone_sdk/12_custom_secrets.py`. Real-LLM: none.
- `S04.secrets-constructor`: `Conversation(secrets={...})` seeds the same registry at construction, for static and callable values. Unit: `tests/sdk/conversation/test_conversation_secrets_constructor.py`. Example: none. Real-LLM: none.
- `S04.secrets-masking`: secret values echoed by a command are replaced by `<secret-hidden>` in observations and never reach the persisted events. Unit: `tests/tools/terminal/test_secrets_masking.py`, `tests/cross/test_agent_secrets_integration.py`. Example: `examples/01_standalone_sdk/12_custom_secrets.py`. Real-LLM: none.
- `S04.visualizer-default`: by default a `DefaultConversationVisualizer` prints each event as a Rich panel; `visualizer=None` turns it off; a class or instance can be passed. Unit: `tests/sdk/conversation/local/test_conversation_visualize_param.py`. Example: `examples/01_standalone_sdk/10_persistence.py`. Real-LLM: none.
- `S04.visualizer-custom`: a `ConversationVisualizerBase` subclass passed as `visualizer=` receives every event through `on_event`; each event type has its own `visualize` rendering. Unit: `tests/sdk/conversation/test_visualizer.py`. Example: `examples/01_standalone_sdk/26_custom_visualizer.py`. Real-LLM: none.
- `S04.fork`: `fork()` deep-copies the conversation under a new id (or `conversation_id=`), starts IDLE, leaves the source untouched, resets metrics unless `reset_metrics=False`, accepts `agent=`, `title=` and `tags=`, shares the workspace, and persists so the fork survives a reload. Unit: `tests/sdk/conversation/local/test_fork.py`. Example: `examples/01_standalone_sdk/48_conversation_fork.py`. Real-LLM: none.
- `S04.fork-branch`: events carry parent ids forming a tree; `fork(from_event_id=...)` copies only that branch, and `navigate_to(event_id)` moves HEAD so the next event starts a sibling branch (`None` empties the active branch). Unit: `tests/sdk/conversation/local/test_conversation_tree.py`. Example: `examples/01_standalone_sdk/48_conversation_fork.py`. Real-LLM: none.
- `S04.goal-loop`: `run_goal(conversation, objective, judge_llm, max_iterations=N)` sends the objective, runs, asks the judge LLM for a verdict, re-prompts with the missing items, and returns a `GoalOutcome` with status `"complete"` or `"capped"`, the iteration count and the verdict. Unit: `tests/sdk/conversation/goal/`. Example: `examples/01_standalone_sdk/54_goal_completion_loop.py`. Real-LLM: none.
- `S04.interactive-terminal`: with `Tool(name=TerminalTool.name, params={"no_change_timeout_seconds": 3})` the agent can start `python3`, feed it input and exit; an `LLMConvertibleEvent` callback collects the raw LLM messages. Unit: `tests/tools/terminal/test_terminal_session.py::test_python_interactive_input`, `::test_interactive_command`. Example: `examples/01_standalone_sdk/06_interactive_terminal_w_reasoning.py`. Real-LLM: `tests/integration/tests/t07_interactive_commands.py`.
- `S04.final-response`: `get_agent_final_response(conversation.state.events)` returns the last `finish` message, else the last agent `MessageEvent` text, else `""`. Unit: `tests/sdk/conversation/test_agent_final_response.py`. Example: none. Real-LLM: `tests/integration/tests/t08_image_file_viewing.py`.
- `S04.stats`: `conversation.conversation_stats` keeps `Metrics` per LLM `usage_id`, combines them with `get_combined_metrics()`, restores them on resume, and stats update events carry a snapshot rather than the full history. Unit: `tests/sdk/conversation/test_conversation_stats.py`, `tests/sdk/conversation/test_stats_update_event_snapshot.py`. Example: `examples/01_standalone_sdk/11_async.py` (prints cost). Real-LLM: none.
- `S04.title-and-tags`: `generate_title(llm=None, max_length=50)` asks an LLM (the agent's by default) for a title from the first user message, falls back to truncation on error, and strips reasoning text; `tags={...}` keys must be lowercase alphanumeric. Unit: `tests/sdk/conversation/test_generate_title.py`, `tests/sdk/conversation/test_tags.py`. Example: `examples/01_standalone_sdk/48_conversation_fork.py` (`title=`). Real-LLM: none.

## How to get to it (agent POV)

- `Conversation(agent, workspace=..., persistence_dir=None, conversation_id=None, callbacks=None, visualizer=DefaultConversationVisualizer, secrets=None, delete_on_close=True, tags=None, ...)` in `openhands.sdk`: `S04.factory`, `S04.conversation-id`, `S04.persist-events`, `S04.resume`, `S04.resume-agent-compat`, `S04.callbacks`, `S04.visualizer-*`, `S04.secrets-constructor`, `S04.title-and-tags`. The step-loop arguments (`max_iteration_per_run`, `stuck_detection*`, `max_budget_per_run`) belong to S01.
- On disk: `<persistence_dir>/<conversation_id.hex>/base_state.json` and `.../events/event-NNNNN-<event_id>.json` (`persistence_const.py`): `S04.persist-events`, `S04.resume`. `ConversationState.create(..., file_store=...)` / `LocalConversation(..., file_store=...)`: `S04.custom-file-store`.
- `conversation.run()`, `conversation.pause()`, `await conversation.arun()`, `conversation.interrupt()`, `conversation.cancel_token`: `S04.pause`, `S04.arun-interrupt`, `S04.cancel-token`. `openhands.sdk.utils.async_utils.AsyncCallbackWrapper`: `S04.async-callback`.
- `conversation.update_secrets({...})`, `openhands.sdk.secret.SecretSource` (subclass with `get_value()`), `StaticSecret`, `LookupSecret`: `S04.secrets-*`.
- `openhands.sdk.conversation.visualizer.ConversationVisualizerBase`, `DefaultConversationVisualizer`: `S04.visualizer-*`.
- `conversation.fork(conversation_id=, agent=, title=, tags=, reset_metrics=True, from_event_id=)`, `conversation.navigate_to(event_id)`: `S04.fork`, `S04.fork-branch`.
- `openhands.sdk.conversation.goal.run_goal`, `GoalController`, `judge_goal`: `S04.goal-loop`.
- `openhands.sdk.conversation.response_utils.get_agent_final_response`: `S04.final-response`. `conversation.conversation_stats` / `conversation.state.stats`: `S04.stats`. `conversation.generate_title()`: `S04.title-and-tags`. `conversation.close()`: `S04.close`.
- Env: `LLM_API_KEY` (required), `LLM_MODEL` (default `gpt-5.5`; `anthropic/claude-sonnet-4-5-20250929` in example 50), `LLM_BASE_URL`; example 50 also reads `AUTO_CANCEL_SECONDS` (default 8).

## Driving it

Preconditions:
- `uv sync --dev` has run.
- `tmux` is on `PATH` for the terminal-session tests and for examples that use `TerminalTool`.
- For examples: `LLM_API_KEY` and `LLM_MODEL` exported (and `LLM_BASE_URL` for a proxy). Example 10 also needs `uvx` (it starts `mcp-server-fetch`) and outbound network.

- **Factory, id, persistence and resume (`S04.factory`, `S04.conversation-id`, `S04.persist-events`, `S04.resume`, `S04.resume-agent-compat`, `S04.custom-file-store`).**
  ```sh
  uv run pytest tests/sdk/conversation/test_conversation_factory.py tests/sdk/conversation/local/test_conversation_id.py -q
  uv run pytest tests/sdk/conversation/local/test_state_serialization.py tests/sdk/conversation/local/test_conversation_core.py tests/sdk/conversation/local/test_custom_file_store.py tests/cross/test_persistence_dir_call_sites.py -q
  uv run pytest tests/cross/test_conversation_restore_behavior.py -q
  uv run python examples/01_standalone_sdk/10_persistence.py
  ```
  The tests pass; the example writes `./.conversations/<id>/`, deletes the object, rebuilds it from the same id and answers a question about the earlier turns.
- **Callbacks, run errors and close (`S04.callbacks`, `S04.run-error`, `S04.close`).**
  ```sh
  uv run pytest tests/sdk/conversation/local/test_conversation_default_callback.py tests/sdk/conversation/local/test_run_exception_includes_conversation_id.py tests/sdk/conversation/test_atexit_cleanup.py tests/tools/terminal/test_conversation_cleanup.py -q
  ```
  All pass; no real LLM is involved.
- **Pause (`S04.pause`).**
  ```sh
  uv run pytest tests/sdk/conversation/local/test_conversation_pause_functionality.py tests/sdk/conversation/local/test_agent_status_transition.py -q
  uv run python examples/01_standalone_sdk/09_pause_example.py
  ```
  The example shows status PAUSED after `pause()`, then FINISHED after the second `run()`.
- **Async callback, `arun()` and interrupt (`S04.async-callback`, `S04.arun-interrupt`, `S04.cancel-token`).**
  ```sh
  uv run pytest tests/sdk/utils/test_async_utils.py tests/sdk/conversation/test_interrupt.py -q
  uv run python examples/01_standalone_sdk/11_async.py
  AUTO_CANCEL_SECONDS=5 uv run python examples/01_standalone_sdk/50_async_cancellation.py
  ```
  Example 50 interrupts the run after the given seconds (or on Ctrl+C) and reports status PAUSED.
- **Secrets (`S04.secrets-update`, `S04.secrets-constructor`, `S04.secrets-masking`).**
  ```sh
  uv run pytest tests/sdk/conversation/test_secrets_manager.py tests/sdk/conversation/test_secret_source.py tests/sdk/conversation/test_conversation_secrets_constructor.py -q
  uv run pytest tests/tools/terminal/test_secrets_masking.py tests/cross/test_agent_secrets_integration.py -q
  uv run python examples/01_standalone_sdk/12_custom_secrets.py
  ```
  In the example the agent's `echo $SECRET_TOKEN` observation shows `<secret-hidden>`, not the value.
- **Visualizer (`S04.visualizer-default`, `S04.visualizer-custom`).**
  ```sh
  uv run pytest tests/sdk/conversation/local/test_conversation_visualize_param.py tests/sdk/conversation/test_visualizer.py -q
  uv run python examples/01_standalone_sdk/26_custom_visualizer.py
  ```
  The example prints one raw line per event from `MinimalVisualizer` instead of Rich panels.
- **Fork and branches (`S04.fork`, `S04.fork-branch`).**
  ```sh
  uv run pytest tests/sdk/conversation/local/test_fork.py tests/sdk/conversation/local/test_conversation_tree.py -q
  uv run python examples/01_standalone_sdk/48_conversation_fork.py
  ```
  The example ends with `All done — fork() works end-to-end.` after running a full fork, a fork with another LLM and a slice fork.
- **Goal loop (`S04.goal-loop`).**
  ```sh
  uv run pytest tests/sdk/conversation/goal -q
  uv run python examples/01_standalone_sdk/54_goal_completion_loop.py
  ```
  The example prints `Goal complete after N audit round(s).` (or `capped`) with the judge score.
- **Interactive terminal (`S04.interactive-terminal`).**
  ```sh
  uv run pytest "tests/tools/terminal/test_terminal_session.py::test_python_interactive_input" "tests/tools/terminal/test_terminal_session.py::test_interactive_command" -q
  uv run python examples/01_standalone_sdk/06_interactive_terminal_w_reasoning.py
  uv run python tests/integration/run_infer.py --llm-config '{"model": "'"$LLM_MODEL"'"}' --eval-ids t07_interactive_commands
  ```
  The example prints the collected LLM messages, including the terminal observations from inside `python3`.
- **Final response, stats, title and tags (`S04.final-response`, `S04.stats`, `S04.title-and-tags`).**
  ```sh
  uv run pytest tests/sdk/conversation/test_agent_final_response.py tests/sdk/conversation/test_conversation_stats.py tests/sdk/conversation/test_stats_update_event_snapshot.py tests/sdk/conversation/test_generate_title.py tests/sdk/conversation/test_tags.py -q
  ```
  All pass without a model.

## Gotchas

- `examples/01_standalone_sdk/06_interactive_terminal_w_reasoning.py` is in `_EXCLUDED_EXAMPLES` in `tests/examples/test_examples.py`, so the `test-examples` label never runs it; it also prints no `EXAMPLE_COST:` line, which that harness would require.
- Examples run under the harness with `uv run pytest tests/examples/test_examples.py --run-examples -k <name>`; without `--run-examples` every case is skipped.
- `10_persistence.py` and `14_context_condenser.py` write `./.conversations` relative to the current directory; reruns pile up conversation folders there. Example 10 starts `uvx ... mcp-server-fetch` and fetches github.com, so it needs `uvx` and network.
- `pause()` does not interrupt an LLM call in flight; it takes effect at the next step. Use `arun()` + `interrupt()` for immediate cancellation. `interrupt()` during a synchronous `run()` is only a `pause()`.
- `09_pause_example.py` sleeps a fixed 2 s before pausing; on a slow model the first step may not have started, which still passes but shows less.
- `50_async_cancellation.py` installs a SIGINT handler and defaults `LLM_MODEL` to an Anthropic model, unlike the other examples.
- The default visualizer prints Rich panels to stdout; pass `visualizer=None` when you parse stdout.
- `OH_PERSISTENCE_DIR` relocates `~/.openhands` (user state, not `persistence_dir`); it must be set before `openhands.sdk` is imported.
- The terminal-session tests need `tmux`; they are slow (about 40 s for the two interactive cases).
- No failing tests were found in this family's commands at 4cc0582.
