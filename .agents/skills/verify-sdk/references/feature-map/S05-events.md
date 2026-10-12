# Events and the event log

Everything a conversation does is an immutable `Event` (a frozen, `extra="forbid"` pydantic model with `id`, `timestamp`, `source` in `agent`/`user`/`environment`/`hook`, and `parent_id`) appended to `conversation.state.events`, an `EventLog` that writes each event as its own JSON file when persistence is on. Events serialize with a `kind` discriminator, so `Event.model_validate_json(text)` turns any saved event file back into the right subclass. The subset that the LLM sees (`SystemPromptEvent`, `MessageEvent`, `ActionEvent`, `ObservationEvent`, `UserRejectObservation`, `AgentErrorEvent`, `CondensationSummaryEvent`) are `LLMConvertibleEvent`s with `to_llm_message()`; `LLMConvertibleEvent.events_to_messages(events)` folds them into a `Message` list, merging parallel tool calls of one LLM response into one assistant message and adjacent user messages into one. An SDK user can then hand that list to `llm.format_messages_for_llm(...)` (Chat Completions) or `llm.format_messages_for_responses(...)` (Responses API) to get the exact OpenAI-shaped payload. The other events record control flow and telemetry: `PauseEvent`, `InterruptEvent`, `ConversationStateUpdateEvent`, `ConversationErrorEvent`, `Condensation`/`CondensationRequest`, `SecurityAnalysisEvent`, `HookExecutionEvent`, `StreamingDeltaEvent`, `TokenEvent`, `LLMCompletionLogEvent`, `ACPToolCallEvent`.

Source: `openhands-sdk/openhands/sdk/event/`, `openhands-sdk/openhands/sdk/conversation/event_store.py`, `openhands-sdk/openhands/sdk/conversation/events_list_base.py`, `openhands-sdk/openhands/sdk/conversation/persistence_const.py`, `openhands-sdk/openhands/sdk/conversation/state.py`, `openhands-sdk/openhands/sdk/utils/models.py`

Needs: `llm`, `tmux`

Examples: `examples/01_standalone_sdk/36_event_json_to_openai_messages.py`

## Sub-features

- `S05.event-base`: every event gets a fresh id and ISO timestamp, is frozen (assignment raises), rejects unknown fields, and rejects the reserved id `__root__`. Unit: `tests/sdk/event/test_event_immutability.py`, `tests/sdk/event/test_event_serialization.py::test_extra_fields_forbidden`, `tests/sdk/conversation/test_event_tree.py::test_event_id_cannot_equal_reserved_root_sentinel`. Example: none. Real-LLM: none.
- `S05.json-roundtrip`: each event type dumps to JSON with its `kind` and `Event.model_validate_json` restores the same subclass and fields (system prompt, action, observation, message, agent error, condensation in both the current and the legacy list format, condensation request). Unit: `tests/sdk/event/test_event_serialization.py`, `tests/sdk/utils/test_discriminated_union.py`. Example: `examples/01_standalone_sdk/36_event_json_to_openai_messages.py`. Real-LLM: none.
- `S05.to-llm-message`: each `LLMConvertibleEvent` turns into one `Message` with the right role; an `ActionEvent` whose `action` is `None` (non-executable) still round-trips and matches its observation. Unit: `tests/sdk/event/test_events_to_messages.py`, `tests/sdk/event/test_non_executable_action_event.py`. Example: `examples/01_standalone_sdk/06_interactive_terminal_w_reasoning.py`. Real-LLM: none.
- `S05.events-to-messages`: `events_to_messages` merges `ActionEvent`s sharing an `llm_response_id` into one assistant message (keeping the first event's reasoning and Responses reasoning item), merges consecutive plain user messages (not ones with tool calls, a tool call id or a name), and merges a condensation summary into the adjacent user message. Unit: `tests/sdk/event/test_events_to_messages.py`. Example: `examples/01_standalone_sdk/36_event_json_to_openai_messages.py`. Real-LLM: `tests/integration/tests/a01_unmatched_tool_use.py` through `a08_parallel_wrong_order.py` (API compliance of the produced history).
- `S05.system-prompt-blocks`: a `SystemPromptEvent` with static and dynamic context becomes system content blocks in a fixed order, so the static block stays cacheable. Unit: `tests/sdk/event/test_dynamic_context_message_sequence.py`. Example: none. Real-LLM: none.
- `S05.openai-format`: the `Message` list from saved events formats into Chat Completions messages (`llm.format_messages_for_llm`) or Responses `instructions` plus input items (`llm.format_messages_for_responses`). Unit: `tests/sdk/llm/test_responses_serialization.py`. Example: `examples/01_standalone_sdk/36_event_json_to_openai_messages.py`. Real-LLM: none.
- `S05.unmatched-actions`: `ConversationState.get_unmatched_actions(events)` lists actions with no observation, rejection or matching `AgentErrorEvent`, ignores non-executable actions, and so prevents re-running a finished action after a crash. Unit: `tests/sdk/conversation/test_get_unmatched_actions.py`. Example: none. Real-LLM: none.
- `S05.event-log-append`: `EventLog.append` assigns consecutive indexes, rejects duplicate ids, supports negative indexing and `get_index`/`get_id`, serializes concurrent appends from threads, and does not rescan the directory on every append. Unit: `tests/sdk/conversation/test_event_store.py`. Example: none. Real-LLM: none.
- `S05.event-log-files`: the file name is `event-NNNNN-<event_id>.json` (5-digit minimum, wider past 99999), writer and reader agree on it, and a cold reload of more than 100k events works. Unit: `tests/sdk/conversation/test_event_store.py::test_event_filename_writer_reader_agree`, `::test_event_log_cold_reload_past_100k_events`, `::test_event_log_large_index_formatting`. Example: `examples/01_standalone_sdk/36_event_json_to_openai_messages.py` (reads `events/event-*.json`). Real-LLM: none.
- `S05.event-log-recovery`: missing files, corrupted JSON, index gaps, stale indexes, sidecar files and file-store exceptions are tolerated or reported without losing the rest of the log; another writer's appends are picked up. Unit: `tests/sdk/conversation/test_event_store.py`, `tests/sdk/conversation/local/test_state_serialization.py::test_conversation_state_corrupted_event_handling`. Example: none. Real-LLM: none.
- `S05.event-cache`: deserialized events are cached, so repeated iteration does not re-read and re-parse files. Unit: `tests/sdk/conversation/test_event_store.py::test_event_cache_eliminates_repeated_deserialization`, `::test_event_cache_survives_across_multiple_iterations`. Example: none. Real-LLM: none.
- `S05.event-tree`: events carry `parent_id`; `path_to_root` walks a branch, detects cycles, and `append` rejects a parent that does not exist. Unit: `tests/sdk/conversation/test_event_tree.py`. Example: none. Real-LLM: none. (Branch navigation from the conversation API is `S04.fork-branch`.)
- `S05.visualize`: each event has a Rich `visualize` rendering: action summaries, truncated system-prompt tool parameters, without mutating the event. Unit: `tests/sdk/event/test_action_event_summary.py`, `tests/sdk/event/test_system_prompt_event_visualize.py`, `tests/sdk/conversation/test_visualizer.py`. Example: `examples/01_standalone_sdk/26_custom_visualizer.py`. Real-LLM: none.
- `S05.error-classification`: `ConversationErrorEvent` and `AgentErrorEvent` carry a `FailureKind` classification derived from the error code before the detail text; a sensitive detail is classified without being serialized. Unit: `tests/sdk/event/test_error_classification.py`. Example: none. Real-LLM: none.
- `S05.streaming-delta`: `StreamingDeltaEvent` holds a `content` and `reasoning_content` token delta, dumps with its `kind` and round-trips through JSON; it is transient (published by the agent server for WebSocket clients, never appended to the event log). Unit: `tests/sdk/event/test_streaming.py`. Example: none. Real-LLM: none.
- `S05.completion-log-event`: `LLMCompletionLogEvent` carries a completion log (filename, JSON data, model, usage id) as an event; the agent server emits it for remote conversations. Unit: `tests/sdk/event/test_llm_completion_log_event.py`. Example: none. Real-LLM: none.
- `S05.token-event`: with `litellm_extra_body={"return_token_ids": True}` (vLLM), the agent emits a `TokenEvent` with prompt and response token ids. Unit: **none (untested)**. Example: none. Real-LLM: none.
- `S05.resume-transcript`: `render_resume_transcript(events)` renders user and assistant messages, tool uses with status and I/O, and ACP tool calls into one text transcript (for re-bootstrapping an ACP session), or `None` when nothing relevant exists. Unit: `tests/sdk/event/test_resume_transcript.py`. Example: none. Real-LLM: none.

## How to get to it (agent POV)

- `from openhands.sdk.event import Event, LLMConvertibleEvent, MessageEvent, ActionEvent, ObservationEvent, SystemPromptEvent, ...`; `Event.model_validate_json(path.read_text())`: `S05.event-base`, `S05.json-roundtrip`.
- `event.to_llm_message()` and `LLMConvertibleEvent.events_to_messages([...])`: `S05.to-llm-message`, `S05.events-to-messages`, `S05.system-prompt-blocks`.
- `llm.format_messages_for_llm(messages)`, `llm.format_messages_for_responses(messages)`, `llm.uses_responses_api()`: `S05.openai-format`.
- `conversation.state.events` (an `EventLog`, a `Sequence[Event]`), `Conversation(callbacks=[fn])` receiving each event, and the files `<persistence_dir>/<id.hex>/events/event-NNNNN-<event_id>.json`: `S05.event-log-*`, `S05.event-cache`, `S05.event-tree`.
- `ConversationState.get_unmatched_actions(events)`: `S05.unmatched-actions`.
- `event.visualize` (a Rich `Text`), `str(event)`: `S05.visualize`.
- `openhands.sdk.event.resume_transcript.render_resume_transcript`: `S05.resume-transcript`. `openhands.sdk.event.error_classification.classify_error`: `S05.error-classification`.
- `LLM(litellm_extra_body={"return_token_ids": True})` against vLLM: `S05.token-event`.
- Env read by example 36 before importing the SDK: `LOG_JSON`, `LOG_TO_FILE`, `LOG_DIR`, `LOG_LEVEL` (set by `os.environ.setdefault`), plus `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`.

## Driving it

Preconditions:
- `uv sync --dev` has run.
- For the example: `LLM_API_KEY` and `LLM_MODEL` exported; `tmux` on `PATH` (the example uses `TerminalTool`).

- **Event model and JSON round trip (`S05.event-base`, `S05.json-roundtrip`, `S05.error-classification`, `S05.streaming-delta`, `S05.completion-log-event`).**
  ```sh
  uv run pytest tests/sdk/event/test_event_immutability.py tests/sdk/event/test_event_serialization.py tests/sdk/utils/test_discriminated_union.py -q
  uv run pytest tests/sdk/event/test_error_classification.py tests/sdk/event/test_streaming.py tests/sdk/event/test_llm_completion_log_event.py -q
  ```
  All pass.
- **Events to LLM messages and OpenAI payloads (`S05.to-llm-message`, `S05.events-to-messages`, `S05.system-prompt-blocks`, `S05.openai-format`).** Unit proof, then the example with a real model.
  ```sh
  uv run pytest tests/sdk/event/test_events_to_messages.py tests/sdk/event/test_non_executable_action_event.py tests/sdk/event/test_dynamic_context_message_sequence.py tests/sdk/llm/test_responses_serialization.py -q
  uv run python examples/01_standalone_sdk/36_event_json_to_openai_messages.py
  ```
  The example runs two turns with persistence, reloads every `events/event-*.json`, and logs either `Chat Completions messages:` or `Responses input:` with the formatted JSON.
- **API compliance of produced histories (`S05.events-to-messages`).** **Blocked** without a model key.
  ```sh
  uv run python tests/integration/run_infer.py --llm-config '{"model": "'"$LLM_MODEL"'"}' --eval-ids a01_unmatched_tool_use
  ```
- **Event log, files, recovery, cache and tree (`S05.event-log-*`, `S05.event-cache`, `S05.event-tree`, `S05.unmatched-actions`).**
  ```sh
  uv run pytest tests/sdk/conversation/test_event_store.py tests/sdk/conversation/test_event_tree.py tests/sdk/conversation/test_get_unmatched_actions.py -q
  uv run pytest tests/sdk/conversation/local/test_state_serialization.py -q
  ```
  All pass; the 100k-event reload test takes a few seconds.
- **Visualization and resume transcript (`S05.visualize`, `S05.resume-transcript`).**
  ```sh
  uv run pytest tests/sdk/event/test_action_event_summary.py tests/sdk/event/test_system_prompt_event_visualize.py tests/sdk/event/test_resume_transcript.py -q
  ```
- **TokenEvent (`S05.token-event`), untested.** Needs a vLLM endpoint that returns `prompt_token_ids`; no test or example exercises it.

## Gotchas

- Example 36 sets `LOG_JSON`, `LOG_TO_FILE`, `LOG_DIR` and `LOG_LEVEL` with `setdefault` before importing the SDK; values already in your environment win, so a stale `LOG_DIR` sends the logs elsewhere.
- The formatted payload is logged, not printed: with `LOG_JSON=true` it lands in the JSON log under the example's log dir, so look there rather than at stdout.
- Which branch example 36 takes depends on `llm.uses_responses_api()`: `LLM(api_mode=...)` when set, otherwise whether the model's feature table lists Responses support. Run it with two models to cover both formatters.
- Events are frozen: code that tries to edit an event in a callback raises a pydantic validation error. Build a new event instead.
- `events_to_messages` asserts that parallel `ActionEvent`s after the first in a batch have empty `thought`; hand-built event lists that break this raise `AssertionError` (`test_assertion_error_for_non_empty_thought_in_parallel_calls`).
- Unknown `kind` values (an event class from a module that is not imported) fail deserialization; import custom event or tool modules before loading old event files.
- No failing tests were found in this family's commands at 4cc0582.
