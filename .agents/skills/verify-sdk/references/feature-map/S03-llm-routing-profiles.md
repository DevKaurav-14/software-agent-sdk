# LLM registry, routing, fallback, profiles and model switching

A Python program that uses more than one model meets this family. `LLMRegistry` holds `LLM`s by `usage_id`, gives each one independent metrics, and notifies subscribers; every `LocalConversation` has its own `conversation.llm_registry`, into which it registers every LLM the agent reaches (the agent's, the condenser's, router children), and `conversation_stats` tracks them all. A `RouterLLM` (`MultimodalRouter`, `RandomRouter`) is itself an `LLM` that picks one of `llms_for_routing` per call; `MultimodalRouter` sends a request with images, or one too large for the secondary model, to `primary` and everything else to `secondary`. `LLM(fallback_strategy=FallbackStrategy(fallback_llms=[...]))` retries a call that failed with a transient error on saved profiles, in order, and merges their cost into the primary's metrics. `LLMProfileStore` saves and loads named `LLM` configurations as JSON (default `~/.openhands/profiles`, secrets masked unless asked for). A running conversation can change model with `conversation.switch_profile(name)` or `conversation.switch_llm(llm)`, the agent can do it itself with the `switch_llm` tool, or a classifier LLM can pick a profile through the `route_task_to_model` tool configured by a meta-profile. `LLM.subscription_login(vendor="openai", model=...)` returns an `LLM` backed by a ChatGPT Plus/Pro subscription through OAuth instead of an API key.

Source: `openhands-sdk/openhands/sdk/llm/llm_registry.py`, `openhands-sdk/openhands/sdk/llm/router/`, `openhands-sdk/openhands/sdk/llm/fallback_strategy.py`, `openhands-sdk/openhands/sdk/llm/llm_profile_store.py`, `openhands-sdk/openhands/sdk/llm/meta_profile_store.py`, `openhands-sdk/openhands/sdk/llm/provider_connection_store.py`, `openhands-sdk/openhands/sdk/llm/auth/`, `openhands-sdk/openhands/sdk/llm/llm.py`, `openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py`, `openhands-sdk/openhands/sdk/conversation/conversation_stats.py`, `openhands-sdk/openhands/sdk/tool/builtins/switch_llm.py`, `openhands-sdk/openhands/sdk/tool/builtins/classify_and_switch_llm.py`, `openhands-sdk/openhands/sdk/settings/model.py`

Needs: `llm`, `network`

Examples: `examples/01_standalone_sdk/05_use_llm_registry.py`, `examples/01_standalone_sdk/19_llm_routing.py`, `examples/01_standalone_sdk/35_subscription_login.py`, `examples/01_standalone_sdk/37_llm_profile_store/main.py`, `examples/01_standalone_sdk/39_llm_fallback.py`, `examples/01_standalone_sdk/44_model_switching_in_convo.py`, `examples/01_standalone_sdk/49_switch_llm_tool.py`, `examples/01_standalone_sdk/59_route_task_to_model.py`

## Sub-features

- `S03.registry-crud`: `LLMRegistry.add(llm)` keys by `usage_id` and refuses a duplicate, `get(usage_id)` returns the same instance or raises `KeyError`, `remove` and `list_usage_ids` work, and each registry has a unique id. Unit: `tests/sdk/llm/test_llm_registry.py`. Example: `examples/01_standalone_sdk/05_use_llm_registry.py`. Real-LLM: none.
- `S03.registry-independent-metrics`: an `LLM` copied from another and added to a registry gets its own `Metrics` and telemetry, so costs do not double-count; independent LLMs keep their metrics. Unit: `tests/sdk/llm/test_llm_registry.py::test_llm_registry_ensures_independent_metrics_for_copied_llms`, `::test_llm_registry_ensures_independent_telemetry_for_copied_llms`, `::test_llm_registry_does_not_reset_metrics_for_independent_llms`. Example: none. Real-LLM: none.
- `S03.registry-stats-wiring`: the conversation subscribes `conversation_stats` to its registry, so any LLM added later (e.g. `conversation.llm_registry.add(LLM(usage_id="x"))`) shows up in `usage_to_metrics`; a failing subscriber does not break `add`. Unit: `tests/sdk/conversation/test_conversation_stats.py::test_llm_registry_notifications`, `tests/sdk/llm/test_llm_registry.py::test_llm_registry_notify_exception_handling`. Example: `examples/01_standalone_sdk/21_generate_extraneous_conversation_costs.py`. Real-LLM: none.
- `S03.agent-llm-discovery`: the conversation finds every `LLM` field reachable from the agent (condenser, custom fields, router children), registers each `usage_id` once and dedupes duplicates. Unit: `tests/sdk/agent/test_agent_llms_are_discoverable.py`, `tests/sdk/conversation/test_switch_model.py::test_duplicate_usage_ids_in_registration_loop_are_silently_deduped`. Example: none. Real-LLM: none.
- `S03.multimodal-router-images`: `Agent(llm=MultimodalRouter(llms_for_routing={"primary": ..., "secondary": ...}))` sends a turn with an image to `primary`, and the non-vision guard does not pre-empt the router. Unit: `tests/sdk/agent/test_non_multimodal_image_input.py::test_image_input_guard_does_not_preempt_multimodal_router`. Example: `examples/01_standalone_sdk/19_llm_routing.py`. Real-LLM: none.
- `S03.multimodal-router-text`: text-only turns go to `secondary`, and turns whose token count exceeds the secondary's `effective_max_input_tokens` go to `primary`. Unit: **none (untested)**. Example: `examples/01_standalone_sdk/19_llm_routing.py` (text turns before and after the image turn). Real-LLM: none.
- `S03.router-validation`: `MultimodalRouter` without a `primary` or `secondary` key and any `RouterLLM` with empty `llms_for_routing` fail validation. Unit: **none (untested)**. Example: none. Real-LLM: none.
- `S03.random-router`: `RandomRouter` picks a random entry of `llms_for_routing` per call. Unit: **none (untested)**. Example: none. Real-LLM: none.
- `S03.fallback-transient`: after the primary exhausts its retries on a transient error (rate limit, timeout, connection, service unavailable, transient HTTP status) the fallback profiles are tried in order; the first success is returned; if all fail the primary's error is raised; each new call starts on the primary again. Chat and Responses, sync and async. Unit: `tests/sdk/llm/test_llm_fallback.py`. Example: `examples/01_standalone_sdk/39_llm_fallback.py`. Real-LLM: none.
- `S03.fallback-skip`: non-transient errors (bad request, auth, context window) and budget denials do not fall back; quota exhaustion fails over without retrying the primary. Unit: `tests/sdk/llm/test_llm_fallback.py::test_non_transient_error_skips_fallback`, `::test_budget_denial_stops_retries_and_fallbacks`, `::test_quota_exhaustion_fails_over_without_retries`. Example: none. Real-LLM: none.
- `S03.fallback-metrics`: cost and token usage of a fallback call are merged into the primary LLM's metrics; caller kwargs and the conversation call context are forwarded to the fallback. Unit: `tests/sdk/llm/test_llm_fallback.py::test_metrics_merged_from_fallback`, `::test_fallback_forwards_caller_kwargs`, `::test_completion_fallback_receives_call_context`. Example: `examples/01_standalone_sdk/39_llm_fallback.py`. Real-LLM: none.
- `S03.fallback-profile-resolution`: `fallback_llms` names are loaded from `LLMProfileStore(profile_store_dir)` lazily on first fallback. Unit: `tests/sdk/llm/test_llm_fallback.py::test_fallback_profiles_resolved_via_store`. Example: `examples/01_standalone_sdk/39_llm_fallback.py`. Real-LLM: none.
- `S03.profile-save-load`: `LLMProfileStore(base_dir).save(name, llm)` writes `<name>.json` atomically with a schema version, `load(name)` returns the `LLM`, `list()`, `list_summaries()`, `delete()`, `rename()` work; invalid names, missing and corrupted profiles raise with the available names listed. Unit: `tests/sdk/llm/test_llm_profile_store.py`. Example: `examples/01_standalone_sdk/37_llm_profile_store/main.py`. Real-LLM: none.
- `S03.profile-secrets`: `save` masks the API key unless `include_secrets=True`; with a `cipher` secrets are encrypted at rest and decrypted on `load`; `list_summaries` reports whether a key is set without exposing it. Unit: `tests/sdk/llm/test_llm_profile_store.py::test_save_without_secrets`, `::test_save_with_secrets`, `tests/sdk/conversation/test_switch_model.py::test_switch_profile_decrypts_with_cipher`. Example: `examples/01_standalone_sdk/37_llm_profile_store/main.py`. Real-LLM: none.
- `S03.profile-concurrency-limits`: concurrent saves and reads are serialized by a file lock, and `max_profiles` blocks new names over the limit but allows overwrites. Unit: `tests/sdk/llm/test_llm_profile_store.py::test_concurrent_saves`, `::test_concurrent_reads_and_writes`, `::test_save_with_max_profiles_blocks_over_limit`. Example: none. Real-LLM: none.
- `S03.profile-migration`: legacy OpenHands-proxy profiles are migrated on load, third-party LiteLLM-proxy profiles are kept, and a profile with a newer schema version is rejected. Unit: `tests/sdk/llm/test_llm_profile_store.py::test_load_migrates_legacy_openhands_proxy_profile`, `::test_load_rejects_newer_profile_schema_version`. Example: none. Real-LLM: none.
- `S03.provider-connections`: a profile can reference a saved provider connection (`provider_connection_id`) whose credentials are resolved at load time from a sibling `provider-connections` store. Unit: `tests/sdk/llm/test_provider_connection_store.py`, `tests/sdk/llm/test_llm_profile_store.py::test_default_provider_store_is_sibling_of_base_dir`. Example: none. Real-LLM: none.
- `S03.switch-profile`: `conversation.switch_profile(name)` loads the profile (cached in the registry as `profile:<name>`), swaps the agent's LLM, updates persisted state, keeps the prompt cache key, and raises for a missing profile; later messages use the new model and both models' costs appear in the stats. Unit: `tests/sdk/conversation/test_switch_model.py`. Example: `examples/01_standalone_sdk/44_model_switching_in_convo.py`. Real-LLM: none.
- `S03.switch-llm-object`: `conversation.switch_llm(llm)` swaps to an `LLM` object without touching the profile store, reuses a registry entry with the same `usage_id`, refreshes an LLM condenser that shared the agent's credentials while leaving an independently configured one alone, and `ask_agent` follows the switch. Unit: `tests/sdk/conversation/test_switch_model.py::test_switch_llm_swaps_when_store_empty`, `::test_switch_llm_refreshes_llm_condenser_credentials`, `::test_switch_llm_preserves_independent_condenser_profile`, `tests/sdk/conversation/test_ask_agent.py::test_ask_agent_llm_refreshes_after_switch_llm`. Example: none. Real-LLM: none.
- `S03.switch-llm-tool`: with `SwitchLLMTool` among the agent's tools (`include_default_tools=["FinishTool", "SwitchLLMTool"]`, or `OpenHandsAgentSettings.create_agent()`, which adds it when `tools` is left unset), the model calls `switch_llm(profile_name=...)`; the tool description lists saved profiles, the conversation switches, and a missing profile or load error comes back as an error observation. The tool is exempt from `filter_tools_regex` and does not deadlock under `arun()`. Unit: `tests/sdk/tool/test_switch_llm.py`, `tests/sdk/conversation/test_switch_model.py::test_switch_llm_tool_during_arun_does_not_deadlock`. Example: `examples/01_standalone_sdk/49_switch_llm_tool.py`. Real-LLM: none.
- `S03.route-task-to-model`: with `OpenHandsAgentSettings(enable_classify_and_switch_llm_tool=True, meta_profile=..., active_meta_profile=...)` the agent gets `route_task_to_model`; calling it sends recent conversation text to the classifier profile, which returns a class index (structured `classes`) or a model name (`prompt_template` with `{{ instance_text }}` and `{{ model_table }}`), and the conversation switches to that profile. Classifier cost lands in the conversation stats under one usage bucket; unknown classes, missing classifier or target profiles produce error observations. Unit: `tests/sdk/tool/test_classify_and_switch_llm.py`. Example: `examples/01_standalone_sdk/59_route_task_to_model.py`. Real-LLM: none.
- `S03.meta-profile-store`: `MetaProfileStore` saves, lists, loads and deletes meta-profiles under `OH_PERSISTENCE_DIR` (or `~/.openhands`), validates direct-prompt templates (requires `{{ instance_text }}`, no `classes`), and enforces `max_profiles`. Unit: `tests/sdk/llm/test_meta_profile_store.py`. Example: none. Real-LLM: none.
- `S03.subscription-login`: `LLM.subscription_login(vendor="openai", model=..., auth_method="browser"|"device_code", force_login=False, open_browser=True)` runs an OAuth PKCE browser flow or a device-code flow, caches credentials under `~/.openhands/auth/`, refreshes expired tokens, asks for consent once, and returns an `LLM` pointed at the Codex Responses endpoint; models outside the supported set are rejected. Unit: `tests/sdk/llm/auth/test_openai.py`, `tests/sdk/llm/auth/test_credentials.py`. Example: `examples/01_standalone_sdk/35_subscription_login.py`. Real-LLM: none.
- `S03.subscription-requests`: a subscription `LLM` omits parameters the Codex endpoint rejects or mishandles (`prompt_cache_retention`, `include`, `reasoning`, `temperature`, `max_output_tokens`), adds no temperature on retry, keeps `is_subscription` across serialization, and rehydrates from `LLM.load_from_env`. Unit: `tests/sdk/llm/test_subscription_mode.py`, `tests/sdk/test_settings.py::test_llm_load_from_env_rehydrates_subscription_runtime`. Example: none. Real-LLM: none.

## How to get to it (agent POV)

- `LLMRegistry()` from `openhands.sdk`: `add`, `get`, `remove`, `list_usage_ids`, `subscribe`; `conversation.llm_registry` is the conversation's own instance. Covers `S03.registry-*`, `S03.agent-llm-discovery`.
- `MultimodalRouter(usage_id=..., llms_for_routing={"primary": llm_a, "secondary": llm_b})` from `openhands.sdk.llm.router`, passed as `Agent(llm=router)`; `RandomRouter` from `openhands.sdk.llm.router.impl.random`; subclass `RouterLLM` and implement `select_llm(messages) -> key` for a custom router. Covers `S03.*router*`.
- `LLM(..., fallback_strategy=FallbackStrategy(fallback_llms=["p1", "p2"], profile_store_dir=...))` with `FallbackStrategy` from `openhands.sdk.llm`. Covers `S03.fallback-*`.
- `LLMProfileStore(base_dir=None)` from `openhands.sdk`: `save(name, llm, include_secrets=False, cipher=None)`, `load(name, cipher=None)`, `list()`, `list_summaries()`, `delete()`, `rename()`; default directory `$OH_PERSISTENCE_DIR/profiles` or `~/.openhands/profiles`. Covers `S03.profile-*`, `S03.provider-connections`.
- `conversation.switch_profile(name)`, `conversation.switch_llm(llm)` on `LocalConversation`; `conversation.switch_acp_model(model)` is the ACP-agent counterpart (ACP family). Covers `S03.switch-profile`, `S03.switch-llm-object`.
- Tools: `Agent(include_default_tools=["FinishTool", "SwitchLLMTool"])`; `OpenHandsAgentSettings(tools=..., enable_classify_and_switch_llm_tool=True, active_meta_profile=..., meta_profile=MetaProfile(...), meta_profile_llms={...}).create_agent()` (the switch tool is included when `tools` is None or selects `switch_llm`; the old `enable_switch_llm_tool` is a read-only, deprecated property); `MetaProfile`, `MetaProfileClass`, `MetaProfileStore` from `openhands.sdk.llm.meta_profile_store`. Covers `S03.switch-llm-tool`, `S03.route-task-to-model`, `S03.meta-profile-store`.
- `LLM.subscription_login(...)`; files in `~/.openhands/auth/` (credentials, consent marker). Covers `S03.subscription-*`.
- Env vars: `OH_PERSISTENCE_DIR` (moves profiles, meta-profiles and auth; must be set before importing `openhands.sdk`), example-only `LLM_ROUTING_SECONDARY_MODEL`, `LLM_FALLBACK_MODEL_1/2`, `LLM_FALLBACK_API_KEY_1/2`, `LLM_FALLBACK_BASE_URL_1/2`, `OPENHANDS_SUBSCRIPTION_MODEL`, `OPENHANDS_SUBSCRIPTION_AUTH_METHOD`, `OPENHANDS_SUBSCRIPTION_FORCE_LOGIN`, `SUBSCRIPTION_LOGIN_ONLY`.

## Driving it

Preconditions:
- `uv sync --dev` has run.
- For example bullets: `LLM_API_KEY` exported, optionally `LLM_MODEL` and `LLM_BASE_URL`; examples 49 and 59 default `LLM_BASE_URL` to `https://llm-proxy.app.all-hands.dev` and need a key valid there; `tmux` installed; network access.

- **Registry and stats wiring (`S03.registry-crud`, `S03.registry-independent-metrics`, `S03.registry-stats-wiring`, `S03.agent-llm-discovery`).**
  ```sh
  uv run pytest tests/sdk/llm/test_llm_registry.py tests/sdk/conversation/test_conversation_stats.py tests/sdk/agent/test_agent_llms_are_discoverable.py -q
  uv run python examples/01_standalone_sdk/05_use_llm_registry.py
  ```
  The tests pass; the example prints `LLM Registry usage IDs: ['agent']` and `Same LLM instance: True`.
- **Multimodal routing (`S03.multimodal-router-images`).**
  ```sh
  uv run pytest tests/sdk/agent/test_non_multimodal_image_input.py::test_image_input_guard_does_not_preempt_multimodal_router -q
  LLM_ROUTING_SECONDARY_MODEL=<text-only model> uv run python examples/01_standalone_sdk/19_llm_routing.py
  ```
  The test passes; the example's log shows `Routing to the secondary model...` for the text turns and `Routing to the primary model...` for the image turn.
- **Router text and token-limit routing, validation, random router, untested (`S03.multimodal-router-text`, `S03.router-validation`, `S03.random-router`).** Only example 19 touches the text path; nothing exercises validation or `RandomRouter`.
- **Fallback (`S03.fallback-*`).**
  ```sh
  uv run pytest tests/sdk/llm/test_llm_fallback.py -q
  uv run python examples/01_standalone_sdk/39_llm_fallback.py
  ```
  49 tests pass; the example writes `HAIKU.txt` and prints the total cost and one token-usage line per LLM call with its model (all on the primary unless it failed over).
- **Profile store (`S03.profile-*`, `S03.provider-connections`).** The example makes no model call.
  ```sh
  uv run pytest tests/sdk/llm/test_llm_profile_store.py tests/sdk/llm/test_provider_connection_store.py -q
  uv run python examples/01_standalone_sdk/37_llm_profile_store/main.py
  ```
  The tests pass; the example prints `Seeded profiles: ['fast.json']`, then both profiles, the loaded `fast` and `creative` settings, and `EXAMPLE_COST: 0`.
- **Switching in a conversation (`S03.switch-profile`, `S03.switch-llm-object`).**
  ```sh
  uv run pytest tests/sdk/conversation/test_switch_model.py tests/sdk/conversation/test_ask_agent.py::test_ask_agent_llm_refreshes_after_switch_llm -q
  uv run python examples/01_standalone_sdk/44_model_switching_in_convo.py
  ```
  The tests pass; the example prints `Switched to: openhands/gpt-5.2` and one cost line per usage id.
- **switch_llm tool (`S03.switch-llm-tool`).**
  ```sh
  uv run pytest tests/sdk/tool/test_switch_llm.py -q
  uv run python examples/01_standalone_sdk/49_switch_llm_tool.py
  ```
  The tests pass; the example prints `Active model after tool switch: openai/prod/claude-sonnet-4-5-20250929` and asserts it.
- **route_task_to_model and meta-profiles (`S03.route-task-to-model`, `S03.meta-profile-store`).**
  ```sh
  uv run pytest tests/sdk/tool/test_classify_and_switch_llm.py tests/sdk/llm/test_meta_profile_store.py -q
  uv run python examples/01_standalone_sdk/59_route_task_to_model.py
  ```
  The tests pass; the example prints the starting model, the model after routing, and per-usage costs including the classifier's.
- **Subscription login, blocked for the example (`S03.subscription-login`, `S03.subscription-requests`).** The unit tests run offline; the example needs a ChatGPT Plus/Pro account and an interactive browser or device-code login.
  ```sh
  uv run pytest tests/sdk/llm/auth/ tests/sdk/llm/test_subscription_mode.py tests/sdk/test_settings.py::test_llm_load_from_env_rehydrates_subscription_runtime -q
  OPENHANDS_SUBSCRIPTION_MODEL=gpt-5.5 OPENHANDS_SUBSCRIPTION_AUTH_METHOD=device_code SUBSCRIPTION_LOGIN_ONLY=1 uv run python examples/01_standalone_sdk/35_subscription_login.py
  ```
  The tests pass; the example prints a verification URL and code, and after login prints `Using subscription mode: True`, the model, and `Login verified; skipping agent run because SUBSCRIPTION_LOGIN_ONLY=1.`

## Gotchas

- `35_subscription_login.py` is in `_EXCLUDED_EXAMPLES` and never runs on the `test-examples` label. Its default model `gpt-5.2-codex` is not in `OPENAI_CODEX_MODELS` (`gpt-6-astra`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5` in `openhands-sdk/openhands/sdk/llm/auth/openai.py`), so without `OPENHANDS_SUBSCRIPTION_MODEL` the example fails with an unsupported-model error after login. The `LLM.subscription_login` docstring lists yet another set (`gpt-5.6`, `gpt-5.4`, `gpt-5.4-mini`, ...).
- Examples 44, 49 and 59 use `LLMProfileStore()` with the default directory, so they write into the real `~/.openhands/profiles` (or `$OH_PERSISTENCE_DIR/profiles`); 44 and 49 delete their profiles at the end, but an interrupted run leaves them behind with secrets (`include_secrets=True`). Set `OH_PERSISTENCE_DIR` to a temp dir to isolate a run. Examples 37 and 39 use a temp dir.
- Example 44 saves the `gpt` profile with model `openhands/gpt-5.2` and no `base_url`, so the `LLM_API_KEY` must be valid for the OpenHands provider; example 49 hardcodes `openai/gpt-5.5` and `openai/prod/claude-sonnet-4-5-20250929` behind the All-Hands proxy, and 59 the same pair.
- The registry in `05_use_llm_registry.py` is a standalone object; the conversation builds its own `conversation.llm_registry`, and costs only show in `conversation_stats` for LLMs in that one.
- `19_llm_routing.py` defaults `LLM_ROUTING_SECONDARY_MODEL` to `LLM_MODEL`, so by default both routes hit the same model and the routing is visible only in logs.
- Fallback only triggers after the primary's own retries are exhausted (`num_retries=5`, backoff up to 64 s), so forcing a fallback by pointing the primary at a dead endpoint is slow; lower `num_retries` and `retry_*_wait` on the primary.
- `OH_PERSISTENCE_DIR` is read into module-level constants at import time; setting it after `import openhands.sdk` has no effect on the default profile directory.
- All pytest commands above passed on 4cc0582 (318 tests in the combined set; a `RuntimeWarning: coroutine '_apply_acp_model' was never awaited` is printed by the switch-model tests and is harmless).
