# Agent context, system prompt, condensers and memory

An SDK user shapes what the model sees in three places. `Agent(agent_context=AgentContext(...))` adds skills (triggered knowledge appended to a user message, or always-on repo skills in the system prompt), a `system_message_suffix` and `user_message_suffix`, the names and descriptions of available secrets, the current date and time, and, with `load_memory=True`, the agent-maintained `MEMORY.md` indexes from `~/.openhands/memory/` and `<workspace>/.openhands/memory/`. The system prompt itself comes from a registry of prompt sections (default or planning preset, model-specific sections for GPT-5 and Codex, vendor files for Claude and Gemini, an identity line from `~/.openhands/SOUL.md`) or from `Agent(system_prompt=...)` / `system_prompt_filename=...` / `system_prompt_kwargs=...`, and is emitted once as a `SystemPromptEvent` split into a static, cacheable block and a dynamic block. `Agent(condenser=...)` keeps long conversations within limits: before each LLM call the condenser looks at the current `View` of events and either passes it through or emits a `Condensation` event that forgets a range of events and inserts a summary. `LLMSummarizingCondenser(llm=..., max_size=240, max_tokens=None, keep_first=2)` summarizes with a separate LLM when the event count, the token count or an explicit `CondensationRequest` (from `conversation.condense()` or a context-window error) calls for it, and falls back to a hard context reset if summarizing fails; `NoOpCondenser` never condenses; `PipelineCondenser` chains condensers. Condensation never splits an action from its observation, a parallel batch, or an Anthropic thinking tool loop.

Source: `openhands-sdk/openhands/sdk/context/agent_context.py`, `openhands-sdk/openhands/sdk/context/memory.py`, `openhands-sdk/openhands/sdk/context/prompts/`, `openhands-sdk/openhands/sdk/context/condenser/`, `openhands-sdk/openhands/sdk/context/view/`, `openhands-sdk/openhands/sdk/event/condenser.py`, `openhands-sdk/openhands/sdk/agent/base.py`, `openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py`

Needs: `llm`, `tmux`

Examples: `examples/01_standalone_sdk/14_context_condenser.py`, `examples/01_standalone_sdk/55_persistent_memory.py`, `examples/01_standalone_sdk/03_activate_skill.py`

## Sub-features

- `S06.context-suffixes`: `AgentContext(system_message_suffix=..., user_message_suffix=...)` appends text to the system prompt and to user messages; empty values add nothing. Unit: `tests/sdk/context/test_agent_context.py`. Example: `examples/01_standalone_sdk/03_activate_skill.py`. Real-LLM: none.
- `S06.context-skills`: repo skills (no triggers) go into the system prompt and triggered skills into the user message whose text matches a trigger (case-insensitive), with already-activated skills skipped; `disabled_skills` drops named skills and duplicate names are rejected. Skill loading and discovery are family S07. Unit: `tests/sdk/context/test_agent_context.py`. Example: `examples/01_standalone_sdk/03_activate_skill.py`. Real-LLM: `tests/integration/tests/t09_invoke_skill.py`.
- `S06.context-secrets`: secret names and descriptions (never values) from `AgentContext(secrets=...)` and the conversation's secret registry are listed in the system prompt; raw string secrets are redacted on serialization and round-trip through a cipher. Unit: `tests/sdk/context/test_agent_context.py::test_get_system_message_suffix_with_secrets_only`, `tests/sdk/context/test_agent_context_serialization.py`, `tests/sdk/context/prompts/test_prompt_snapshot.py::test_dynamic_context_with_secret_registry`. Example: none. Real-LLM: none.
- `S06.context-datetime`: `current_datetime` (a `datetime` or a string; defaults to now) is rendered in the dynamic part of the system prompt. Unit: `tests/sdk/context/test_agent_context.py::test_get_system_message_suffix_with_datetime_only`, `::test_agent_context_default_datetime`. Example: none. Real-LLM: none.
- `S06.system-prompt-registry`: the built-in prompt is assembled from registered sections (default and planning presets), its rendering for fixed inputs matches checked-in snapshots, and the static block has no dynamic content. Unit: `tests/sdk/context/prompts/test_prompt_snapshot.py`, `tests/sdk/context/prompts/test_registry.py`, `tests/sdk/context/prompts/test_default_registry.py`, `tests/sdk/context/prompts/test_planning_registry.py`, `tests/sdk/context/prompts/test_section.py`. Example: none. Real-LLM: none.
- `S06.system-prompt-model-specific`: GPT-5 and GPT-5 Codex models get their own prompt section (detected from the canonical model name or a variant override); Claude and Gemini vendor files are included only for their models. Unit: `tests/sdk/context/test_prompt_model_spec.py`, `tests/sdk/context/test_agent_context_model_specific.py`. Example: none. Real-LLM: none.
- `S06.system-prompt-custom`: `Agent(system_prompt=...)` replaces the built-in prompt; `system_prompt_filename` accepts a relative or absolute template path (missing files raise); `system_prompt_kwargs` feed the template. Unit: `tests/sdk/context/test_prompt_absolute_path.py`, `tests/sdk/context/prompts/test_persona.py::test_inline_system_prompt_wins_over_persona`. Example: none. Real-LLM: none.
- `S06.persona-soul`: a persona replaces the persona sections and keeps capability and dynamic sections; the identity line comes from `~/.openhands/SOUL.md` when present, else a built-in default. Unit: `tests/sdk/context/prompts/test_persona.py`, `tests/sdk/context/prompts/test_prompt_snapshot.py::test_soul_default_snapshot`, `::test_soul_custom_snapshot`. Example: none. Real-LLM: none.
- `S06.memory-load`: with `AgentContext(load_memory=True)` the first `send_message()`/`run()` reads the user and project `MEMORY.md` indexes (user tier first) into the system prompt, truncating whole lines from the top past 6000 characters; empty, unreadable or missing files are treated as absent and never block startup; daily logs are not loaded. Unit: `tests/sdk/context/test_memory.py`, `tests/sdk/conversation/test_local_conversation_memory.py`. Example: `examples/01_standalone_sdk/55_persistent_memory.py`. Real-LLM: none.
- `S06.memory-write-path`: the prompt tells the agent where to write memory, and that path is the same one the loader reads (honoring `OH_PERSISTENCE_DIR`); the resolved memory text is not serialized with the `AgentContext`. Unit: `tests/sdk/context/test_memory.py::test_instructed_write_path_matches_loader_read_path_with_persistence_dir`, `tests/sdk/context/test_agent_context_serialization.py::test_memory_context_excluded_from_serialization`. Example: `examples/01_standalone_sdk/55_persistent_memory.py`. Real-LLM: none.
- `S06.view`: the `View` the condenser sees hides forgotten events, inserts the summary at `summary_offset`, keeps several summaries in order, and always drops `CondensationRequest` events. Unit: `tests/sdk/context/view/test_view.py`, `tests/sdk/context/view/test_view_multi_summary.py`, `tests/sdk/context/view/test_view_append_event.py`. Example: none. Real-LLM: none.
- `S06.view-atomicity`: forgetting never splits an action from its observation, a parallel tool batch, or a tool loop (needed for Anthropic thinking blocks), and observations stay unique. Unit: `tests/sdk/context/view/properties/`, `tests/sdk/context/view/test_view_batch_atomicity.py`, `tests/sdk/context/view/test_view_condensation_batch_atomicity.py`, `tests/sdk/context/view/test_view_tool_loop_boundaries.py`, `tests/sdk/context/view/test_manipulation_indices.py`. Example: none. Real-LLM: `tests/integration/tests/c01_thinking_block_condenser.py`.
- `S06.summarizing-size`: `LLMSummarizingCondenser(max_size=N, keep_first=K)` condenses once the view exceeds N events, keeping the first K events and a tail, and summarizes the forgotten middle (building on the previous summary); `keep_first` must be below `max_size // 2`. Unit: `tests/sdk/context/condenser/test_llm_summarizing_condenser.py`. Example: `examples/01_standalone_sdk/14_context_condenser.py`. Real-LLM: `tests/integration/tests/c05_size_condenser.py`.
- `S06.summarizing-tokens`: with `max_tokens` (or the agent LLM's effective input limit, whichever is smaller) the condenser triggers on token count and forgets enough events to get under it. Unit: `tests/sdk/context/condenser/test_llm_summarizing_condenser.py::test_condense_with_token_limit_exceeded`, `::test_token_limit_uses_stricter_configured_or_agent_limit`, `tests/sdk/context/condenser/test_utils.py`. Example: none. Real-LLM: `tests/integration/tests/c04_token_condenser.py`.
- `S06.summarizing-reasons`: request, event-count and token reasons combine and the most aggressive condensation wins; `minimum_progress` (default 0.1) rejects condensations that forget too little. Unit: `tests/sdk/context/condenser/test_llm_summarizing_condenser.py::test_most_aggressive_condensation_chosen`, `::test_minimum_progress_threshold_not_met`. Example: none. Real-LLM: none.
- `S06.soft-vs-hard`: a soft requirement (size) with no valid range to forget leaves the view unchanged and the run continues; a hard requirement (explicit request, token pressure) with no valid range triggers a hard context reset. Unit: `tests/sdk/context/condenser/test_llm_summarizing_condenser.py::test_condense_with_soft_requirement_and_no_condensation_available`, `::test_condense_with_hard_requirement_and_no_condensation_available`, `tests/sdk/context/condenser/test_rolling_condenser.py`. Example: none. Real-LLM: `tests/integration/tests/c03_delayed_condensation.py`.
- `S06.hard-reset`: when summarizing fails (LLM error or invalid range) the condenser retries a hard context reset up to `hard_context_reset_max_retries` (5), shrinking event text by `hard_context_reset_context_scaling` (0.8) each time, and keeps the leading system prompt. Unit: `tests/sdk/context/condenser/test_llm_summarizing_condenser.py::test_llm_error_triggers_hard_context_reset`, `::test_hard_context_reset_preserves_leading_system_prompt`, `tests/sdk/context/condenser/test_rolling_condenser.py::test_hard_context_reset_condensation_is_returned`. Example: none. Real-LLM: `tests/integration/tests/c02_hard_context_reset.py`.
- `S06.summary-llm-streaming`: the summarizing LLM is a separate `LLM` (own `usage_id` for cost tracking); streaming is switched off for summaries unless the provider requires it, and `extra_body` is not passed. Unit: `tests/sdk/context/condenser/test_llm_summarizing_condenser.py::test_summarization_disables_streaming_when_llm_streams`, `::test_get_condensation_does_not_pass_extra_body`. Example: `examples/01_standalone_sdk/14_context_condenser.py`. Real-LLM: none.
- `S06.manual-condense`: `conversation.condense()` adds a `CondensationRequest` and runs one step to process it; it raises `ValueError` with setup instructions when there is no condenser or the condenser does not handle requests. Unit: `tests/sdk/conversation/test_condense.py`. Example: none. Real-LLM: none.
- `S06.context-overflow-request`: a context-window or malformed-history error from the LLM becomes a `CondensationRequest` when the condenser handles requests, and is raised (with a warning) otherwise. Unit: `tests/sdk/agent/test_agent_context_window_condensation.py`. Example: none. Real-LLM: `tests/integration/tests/c02_hard_context_reset.py`. (Also listed as `S01.context-overflow`.)
- `S06.condenser-resume`: the state's cached `View` applies condensations incrementally and matches a full rebuild, and the resume path rebuilds it from the reloaded `Condensation` events. Unit: `tests/sdk/conversation/test_state_view_cache.py`. Example: `examples/01_standalone_sdk/14_context_condenser.py`. Real-LLM: none.
- `S06.noop-condenser`: `NoOpCondenser` returns the view unchanged, with or without an agent LLM. Unit: `tests/sdk/context/condenser/test_no_op_condenser.py`. Example: none. Real-LLM: none.
- `S06.pipeline-condenser`: `PipelineCondenser(condensers=[...])` runs condensers in order, stops at the first `Condensation`, and handles requests if any member does. Unit: **none (untested)**. Example: none. Real-LLM: none.

## How to get to it (agent POV)

- `Agent(llm=..., tools=..., agent_context=AgentContext(...))` with `skills`, `system_message_suffix`, `user_message_suffix`, `secrets`, `current_datetime`, `disabled_skills`, `load_user_skills`, `load_public_skills`, `load_project_skills`, `load_memory`: `S06.context-*`, `S06.memory-*`.
- `Agent(system_prompt=..., system_prompt_filename="system_prompt.j2" | "system_prompt_planning.j2" | path, system_prompt_kwargs={...})`: `S06.system-prompt-*`. Files: `~/.openhands/SOUL.md` (`S06.persona-soul`), `~/.openhands/memory/MEMORY.md` and `<workspace>/.openhands/memory/MEMORY.md` (`S06.memory-load`). `OH_PERSISTENCE_DIR` replaces `~/.openhands`.
- `Agent(condenser=LLMSummarizingCondenser(llm=llm.model_copy(update={"usage_id": "condenser"}), max_size=..., max_tokens=..., keep_first=..., minimum_progress=..., hard_context_reset_max_retries=..., hard_context_reset_context_scaling=...))`: `S06.summarizing-*`, `S06.soft-vs-hard`, `S06.hard-reset`, `S06.summary-llm-streaming`.
- `from openhands.sdk.context.condenser import NoOpCondenser, PipelineCondenser, LLMSummarizingCondenser, CondenserBase, RollingCondenser`: `S06.noop-condenser`, `S06.pipeline-condenser`; subclass `RollingCondenser` for a custom condenser.
- `conversation.condense()`: `S06.manual-condense`. Events: `Condensation(forgotten_event_ids, summary, summary_offset)`, `CondensationRequest`, `CondensationSummaryEvent` in `openhands.sdk.event`: `S06.view`.
- Settings path: `OpenHandsAgentSettings(condenser=LLMSummarizingCondenserSettings(enabled=True, max_size=...))` builds the same condenser (family S19).

## Driving it

Preconditions:
- `uv sync --dev` has run.
- For examples and integration tests: `LLM_API_KEY` and `LLM_MODEL` exported; `tmux` on `PATH` (the examples use `TerminalTool`).

- **AgentContext and system prompt (`S06.context-*`, `S06.system-prompt-*`, `S06.persona-soul`).**
  ```sh
  uv run pytest tests/sdk/context/test_agent_context.py tests/sdk/context/test_agent_context_serialization.py tests/sdk/context/test_agent_context_model_specific.py tests/sdk/context/test_prompt_model_spec.py tests/sdk/context/test_prompt_absolute_path.py -q
  uv run pytest tests/sdk/context/prompts -q
  uv run python examples/01_standalone_sdk/03_activate_skill.py
  ```
  The tests pass; the example's reply reflects the triggered skill's content.
- **Persistent memory (`S06.memory-load`, `S06.memory-write-path`).**
  ```sh
  uv run pytest tests/sdk/context/test_memory.py tests/sdk/conversation/test_local_conversation_memory.py -q
  uv run python examples/01_standalone_sdk/55_persistent_memory.py
  ```
  In the example, session 1 writes `<tmp>/.openhands/memory/MEMORY.md` and the last lines print `<MEMORY_CONTEXT> injected into session 2's system prompt: True`.
- **View and atomicity (`S06.view`, `S06.view-atomicity`).**
  ```sh
  uv run pytest tests/sdk/context/view -q
  uv run python tests/integration/run_infer.py --llm-config '{"model": "'"$LLM_MODEL"'", "extended_thinking": true}' --eval-ids c01_thinking_block_condenser
  ```
  The unit tests pass; c01 only runs on models with extended thinking (Anthropic) and reports a skip otherwise.
- **Summarizing condenser, soft and hard paths (`S06.summarizing-*`, `S06.soft-vs-hard`, `S06.hard-reset`, `S06.summary-llm-streaming`, `S06.noop-condenser`).**
  ```sh
  uv run pytest tests/sdk/context/condenser -q
  uv run python examples/01_standalone_sdk/14_context_condenser.py
  uv run python tests/integration/run_infer.py --llm-config '{"model": "'"$LLM_MODEL"'"}' --test-type condenser
  ```
  The example's later turns show `Condensation` events in the event log and a resumed conversation that still answers from the summary; `--test-type condenser` runs c01 to c05.
- **Manual condense and overflow requests (`S06.manual-condense`, `S06.context-overflow-request`, `S06.condenser-resume`).**
  ```sh
  uv run pytest tests/sdk/conversation/test_condense.py tests/sdk/agent/test_agent_context_window_condensation.py tests/sdk/conversation/test_state_view_cache.py -q
  ```
- **Pipeline condenser (`S06.pipeline-condenser`), untested.** No test, example or integration test constructs `PipelineCondenser`.

## Gotchas

- `LLMSummarizingCondenser` raises at construction when `keep_first >= max_size // 2 - 1` leaves no tail; small `max_size` values in experiments hit this.
- Give the condenser LLM its own `usage_id` (`llm.model_copy(update={"usage_id": "condenser"})`), otherwise its cost is merged into the agent's in `conversation_stats`.
- A size trigger (soft requirement) that finds nothing safe to forget silently does nothing; do not expect a `Condensation` exactly at `max_size` events (see c03).
- Example 14 writes `./.conversations` in the current directory and resumes from it.
- Example 55 runs in a temporary workspace, but the user tier is read from `~/.openhands/memory/MEMORY.md` (or `$OH_PERSISTENCE_DIR/memory/`); an existing file there changes what session 1 sees. Set `OH_PERSISTENCE_DIR` to a temp dir for a clean run.
- `~/.openhands/SOUL.md` changes the identity line of every built-in prompt; prompt snapshot tests guard against that, but ad-hoc prompt comparisons do not. Regenerate snapshots with `REGEN_PROMPT_SNAPSHOTS=1 uv run pytest tests/sdk/context/prompts/test_prompt_snapshot.py`.
- `memory_context` is resolved at the first `send_message()`/`run()` (the workspace is not known when `AgentContext` validates), so inspecting `agent.agent_context` before that shows no memory.
- `c01_thinking_block_condenser.py` skips models without `extended_thinking`; models with `reasoning_effort` (OpenAI o-series, GPT-5) produce reasoning items, not thinking blocks.
- No failing tests were found in this family's commands at 4cc0582.
