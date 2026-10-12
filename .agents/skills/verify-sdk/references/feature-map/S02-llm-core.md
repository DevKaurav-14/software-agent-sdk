# LLM core: completion, streaming, reasoning, metrics, retries

A Python program creates `LLM(model=..., api_key=..., base_url=..., usage_id=...)` and either hands it to an `Agent` or calls it directly. `llm.completion(messages=[Message(...)], tools=[...])` goes through LiteLLM's Chat Completions path and `llm.responses(...)` through the OpenAI Responses path; `llm.generate(...)`, which the agent uses, picks one from `api_mode` (`auto` resolves from model features). Either returns an `LLMResponse` whose `.message` is an SDK `Message` (text, tool calls, `reasoning_content`, Anthropic `thinking_blocks`, Responses reasoning items). With `stream=True` chunks reach an `on_token` callback (`Conversation(token_callbacks=[...])` in an agent run). Every call adds cost, token usage (prompt, completion, cache read and write, reasoning) and latency to `llm.metrics`; a conversation aggregates all its LLMs by `usage_id` in `conversation.conversation_stats`. Transient failures (rate limit, connection, timeout, empty response) are retried with exponential backoff, and provider errors are mapped to typed `LLMError` subclasses. Models without native tool calling (or with `native_tool_calling=False`) get tools described in the prompt and their text reply parsed back into tool calls. Per-model capability tables decide reasoning effort, thinking mode, sampling parameters, prompt caching, vision and the string serializer.

Source: `openhands-sdk/openhands/sdk/llm/llm.py`, `openhands-sdk/openhands/sdk/llm/llm_response.py`, `openhands-sdk/openhands/sdk/llm/message.py`, `openhands-sdk/openhands/sdk/llm/streaming.py`, `openhands-sdk/openhands/sdk/llm/_response_stream.py`, `openhands-sdk/openhands/sdk/llm/options/`, `openhands-sdk/openhands/sdk/llm/mixins/`, `openhands-sdk/openhands/sdk/llm/exceptions/`, `openhands-sdk/openhands/sdk/llm/utils/`, `openhands-sdk/openhands/sdk/conversation/conversation_stats.py`, `openhands-sdk/openhands/sdk/event/llm_convertible/`

Needs: `llm`, `network`

Examples: `examples/01_standalone_sdk/13_get_llm_metrics.py`, `examples/01_standalone_sdk/21_generate_extraneous_conversation_costs.py`, `examples/01_standalone_sdk/22_anthropic_thinking.py`, `examples/01_standalone_sdk/23_responses_reasoning.py`, `examples/01_standalone_sdk/29_llm_streaming.py`, `examples/01_standalone_sdk/36_event_json_to_openai_messages.py`

## Sub-features

- `S02.completion`: `llm.completion(messages, tools)` calls LiteLLM and returns an `LLMResponse` with the converted `Message`, tool calls and a metrics snapshot; custom params (temperature, top_p, max_output_tokens, seed, extra headers, `litellm_extra_body`) are forwarded. Unit: `tests/sdk/llm/test_llm_completion.py`, `tests/sdk/llm/test_llm_litellm_extra_body.py`. Example: `examples/01_standalone_sdk/13_get_llm_metrics.py`. Real-LLM: `tests/integration/tests/t01_fix_simple_typo.py`.
- `S02.api-mode`: `generate()` / `agenerate()` dispatch to Chat Completions or Responses by `api_mode` (`auto`, `chat`, `responses`); `uses_responses_api()` reports the choice. Unit: `tests/sdk/llm/test_llm.py::test_generate_dispatches_to_configured_api`, `::test_agenerate_dispatches_to_configured_api`. Example: `examples/01_standalone_sdk/36_event_json_to_openai_messages.py`. Real-LLM: none.
- `S02.streaming`: with `stream=True` and an `on_token` callback, content, reasoning and tool-call chunks arrive as `ModelResponseStream` deltas and the final message (tool calls and cache-read tokens included) is reassembled; sync and async generators are accepted. Unit: `tests/sdk/llm/test_llm_completion.py::test_llm_completion_streaming_with_callback`, `::test_llm_completion_streaming_with_tools`, `::test_llm_streaming_preserves_cache_read_tokens`, `tests/sdk/event/test_streaming.py`, `tests/sdk/agent/test_stream_context.py`. Example: `examples/01_standalone_sdk/29_llm_streaming.py`. Real-LLM: none.
- `S02.stream-no-callback`: `stream=True` without a callback degrades to a normal, non-streaming result instead of failing. Unit: `tests/sdk/llm/test_llm_completion.py::test_llm_streaming_without_callback_degrades`. Example: none. Real-LLM: none.
- `S02.timeouts`: `timeout` (default 300 s, `None` disables) is passed to LiteLLM and enforced per attempt; `stream_idle_timeout` (default 300 s) aborts and retries a stalled async stream, and an exhausted stream timeout puts the conversation in ERROR. Unit: `tests/sdk/llm/test_llm_timeout.py`. Example: none. Real-LLM: none.
- `S02.responses-reasoning`: on the Responses path `reasoning_effort`, `reasoning_summary` and `enable_encrypted_reasoning` (default on) are sent only to reasoning models; output items, reasoning summaries and encrypted reasoning are parsed into the `Message` and replayed on the next turn; streamed Responses events are reconstructed with or without a callback. Unit: `tests/sdk/llm/test_responses_parsing_and_kwargs.py`, `tests/sdk/llm/test_responses_serialization.py`, `tests/sdk/llm/test_llm.py::test_enable_encrypted_reasoning_respects_flag_and_defaults_true`. Example: `examples/01_standalone_sdk/23_responses_reasoning.py`. Real-LLM: none.
- `S02.anthropic-thinking`: Anthropic thinking and redacted-thinking blocks (with or without signature) are kept on assistant messages, shown on `MessageEvent`/`ActionEvent`, and sent back unchanged; `extended_thinking_budget` is clamped below `max_tokens`. Unit: `tests/sdk/llm/test_thinking_blocks.py`, `tests/sdk/llm/test_chat_options.py::test_extended_thinking_budget_clamped_below_max_tokens`, `tests/sdk/llm/test_joint_budget_clamp.py`. Example: `examples/01_standalone_sdk/22_anthropic_thinking.py`. Real-LLM: `tests/integration/tests/c01_thinking_block_condenser.py`.
- `S02.reasoning-content`: chat-path `reasoning_content` (DeepSeek-style) is captured on the `Message` and carried on the `ActionEvent`. Unit: `tests/sdk/llm/test_reasoning_content.py`. Example: `examples/01_standalone_sdk/29_llm_streaming.py` (prints streamed reasoning). Real-LLM: none.
- `S02.reasoning-options`: per model family the chat options send `reasoning_effort` or adaptive thinking and strip `temperature`/`top_p` where the model rejects them (GPT-5, Claude Opus 4.5 and Sonnet 4.6+, Kimi), keep them for non-reasoning models, rename Azure `max_completion_tokens`, and add `prompt_cache_key` and OpenRouter headers where supported. Unit: `tests/sdk/llm/test_chat_options.py`. Example: none. Real-LLM: none.
- `S02.model-features`: the feature table answers per model whether it supports reasoning effort, extended or adaptive thinking, sampling params, prompt cache (and key, retention), stop words, Responses API, vision and inline images, and whether to force string content; proxy prefixes are stripped before lookup. Unit: `tests/sdk/llm/test_model_features.py`, `tests/sdk/llm/test_model_info_proxy_lookup.py`, `tests/sdk/llm/test_model_canonical_name_resolution.py`. Example: none. Real-LLM: none.
- `S02.native-tool-calling`: `native_tool_calling` defaults to true and tools are sent as provider tool definitions; setting it false switches to the prompted path. Unit: `tests/sdk/llm/test_llm.py::test_llm_function_calling_enabled_by_default`, `::test_llm_function_calling_can_be_disabled`, `tests/sdk/llm/test_llm_completion.py::test_llm_completion_with_tools`. Example: none. Real-LLM: none.
- `S02.prompted-tool-calling`: on the prompted path tools are described in the system prompt with in-context examples, the model's text is parsed back into `MessageToolCall`s, and conversion errors raise `FunctionCallConversionError` / `FunctionCallValidationError`. Unit: `tests/sdk/llm/test_llm_fncall_converter.py`, `tests/sdk/llm/test_llm_completion.py::test_llm_completion_non_function_call_mode`, `::test_llm_completion_function_call_vs_non_function_call_mode`. Example: none. Real-LLM: none.
- `S02.metrics`: `llm.metrics` accumulates `accumulated_cost`, per-call `costs`, `token_usages` (prompt, completion, cache read, cache write, reasoning, context window), `response_latencies` and a cache hit rate; metrics merge, diff, deep-copy, reset and restore. Unit: `tests/sdk/llm/test_llm_metrics.py`, `tests/sdk/llm/test_llm_completion.py::test_llm_cost_tracking`, `::test_llm_token_usage_tracking`, `::test_llm_latency_tracking`, `tests/sdk/llm/test_llm.py::test_llm_reset_metrics`. Example: `examples/01_standalone_sdk/13_get_llm_metrics.py`. Real-LLM: none.
- `S02.conversation-stats`: `conversation.conversation_stats` keeps one `Metrics` per `usage_id` (agent, condenser, any LLM added to `conversation.llm_registry`) and `get_combined_metrics()` sums them; restored metrics keep tracking after a resume. Unit: `tests/sdk/conversation/test_conversation_stats.py`, `tests/sdk/llm/test_llm.py::test_conversation_stats_restore_then_track`. Example: `examples/01_standalone_sdk/21_generate_extraneous_conversation_costs.py`. Real-LLM: none.
- `S02.pricing-override`: `input_cost_per_token` / `output_cost_per_token` override LiteLLM pricing for cost calculation. Unit: `tests/sdk/llm/test_llm_pricing_passthrough.py`, `tests/sdk/llm/test_llm_span_cost.py`. Example: none. Real-LLM: none.
- `S02.retries`: rate-limit, connection and other transient errors are retried up to `num_retries` (default 5) with backoff from `retry_min_wait`/`retry_max_wait`/`retry_multiplier`; non-retryable errors raise at once; a retry listener sees each attempt. Unit: `tests/sdk/llm/test_api_connection_error_retry.py`, `tests/sdk/llm/test_llm.py::test_llm_retry_on_rate_limit`, `tests/sdk/llm/test_llm_retry_telemetry.py`, `tests/sdk/llm/test_auth_refresh_retry.py`. Example: none. Real-LLM: none.
- `S02.no-response-retry`: an empty provider response is retried with a temperature bump and finally raises `LLMNoResponseError`, on both chat and Responses paths, sync and async. Unit: `tests/sdk/llm/test_llm_no_response_retry.py`. Example: none. Real-LLM: none.
- `S02.error-mapping`: LiteLLM and HTTP errors map to `LLMContextWindowExceedError`, `LLMMalformedConversationHistoryError`, `LLMAuthenticationError`, `LLMRateLimitError`, `LLMTimeoutError`, `LLMServiceUnavailableError`, `LLMBadRequestError`, `LLMContentPolicyViolationError` and budget denials. Unit: `tests/sdk/llm/test_exception_mapping.py`, `tests/sdk/llm/test_exception_classifier.py`, `tests/sdk/llm/test_exception.py`, `tests/sdk/llm/test_budget_denial_http.py`. Example: none. Real-LLM: `tests/integration/tests/a01_unmatched_tool_use.py` (provider responses to malformed histories, run through `tests/integration/api_compliance/run_compliance.py`).
- `S02.prompt-caching`: with `caching_prompt=True` (default) cache markers or keys are added for supporting models, and a "prompt too small to cache" rejection is retried without caching. Unit: `tests/sdk/llm/test_prompt_caching_cross_conversation.py`, `tests/sdk/llm/test_llm_completion.py::test_completion_retries_without_caching_on_prompt_cache_too_small`. Example: none. Real-LLM: none.
- `S02.token-count`: `llm.get_token_count(messages)` counts tokens with LiteLLM or a chat-template tokenizer (`custom_tokenizer`), including tool definitions, with fallbacks when the tokenizer is unavailable. Unit: `tests/sdk/llm/test_llm.py::test_llm_token_counting`, `::test_llm_token_counting_includes_tools`. Example: none. Real-LLM: none.
- `S02.context-window-guard`: a model whose context window is below the SDK minimum raises `LLMContextWindowTooSmallError` unless `ALLOW_SHORT_CONTEXT_WINDOWS` is set; `max_output_tokens` is capped when model info is only a fallback. Unit: `tests/sdk/llm/test_llm.py::test_llm_raises_error_on_small_context_window`, `::test_llm_respects_allow_short_context_windows_env_var`, `::test_max_output_tokens_capped_when_using_max_tokens_fallback`. Example: none. Real-LLM: none.
- `S02.message-formatting`: persisted events reload with `Event.model_validate_json`, `LLMConvertibleEvent.events_to_messages` merges them into `Message`s, and `llm.format_messages_for_llm` / `format_messages_for_responses` produce the provider payload (string serializer, vision, cache markers). Unit: `tests/sdk/event/test_events_to_messages.py`, `tests/sdk/llm/test_message.py`, `tests/sdk/llm/test_message_serialization.py`. Example: `examples/01_standalone_sdk/36_event_json_to_openai_messages.py`. Real-LLM: none.
- `S02.image-inline`: with `inline_image_urls` (auto for providers that reject URLs, such as Moonshot Kimi) http image URLs are fetched and sent as base64 `data:` URLs, bounded by `OH_INLINE_IMAGE_MAX_MB`, `OH_INLINE_IMAGE_FETCH_TIMEOUT_S`, `OH_INLINE_IMAGE_CACHE_BYTES`. Unit: `tests/sdk/llm/test_image_inline.py`. Example: none. Real-LLM: none.
- `S02.log-completions`: `log_completions=True` writes each request and response as JSON under `log_completions_folder`. Unit: `tests/sdk/llm/test_llm_log_completions_integration.py`. Example: none. Real-LLM: none.
- `S02.serialization`: an `LLM` dumps with `api_key` and other secrets masked, round-trips through JSON, `model_copy` keeps configuration while refreshing provider info, and `LLM.load_from_env(prefix="LLM_")` builds an `LLM` from `LLM_*` variables, casting types. Unit: `tests/sdk/llm/test_llm_serialization.py`, `tests/sdk/llm/test_llm.py::test_llm_model_copy_preserves_configuration`, `tests/sdk/test_settings.py::test_llm_load_from_env_rehydrates_subscription_runtime` (the only `load_from_env` test; subscription case). Example: none. Real-LLM: none.

## How to get to it (agent POV)

- `LLM(model=..., api_key=SecretStr(...), base_url=..., usage_id="agent")` from `openhands.sdk`; most behavior is constructor fields: `api_mode`, `stream`, `timeout`, `stream_idle_timeout`, `num_retries`, `retry_min_wait`, `retry_max_wait`, `retry_multiplier`, `reasoning_effort` (default `high`), `reasoning_summary`, `enable_encrypted_reasoning`, `extended_thinking_budget`, `native_tool_calling`, `caching_prompt`, `prompt_cache_retention`, `disable_vision`, `inline_image_urls`, `force_string_serializer`, `input_cost_per_token`, `output_cost_per_token`, `max_input_tokens`, `max_output_tokens`, `log_completions`, `log_completions_folder`, `custom_tokenizer`, `extra_headers`, `litellm_extra_body`, `capability_overrides`.
- `llm.completion(...)`, `llm.responses(...)`, `llm.generate(...)` and their async forms; `on_token=` per call. Covers `S02.completion`, `S02.api-mode`, `S02.streaming`, `S02.responses-reasoning`.
- `Conversation(agent=..., token_callbacks=[on_token])` streams an agent run. Covers `S02.streaming` inside the loop.
- `llm.metrics` (`accumulated_cost`, `accumulated_token_usage`, `token_usages`, `costs`, `response_latencies`), `llm.reset_metrics()`, `llm.restore_metrics(...)`; `conversation.conversation_stats.get_combined_metrics()`, `.usage_to_metrics`. Covers `S02.metrics`, `S02.conversation-stats`.
- `llm.vision_is_active()`, `llm.is_caching_prompt_active()`, `llm.uses_responses_api()`, `llm.effective_max_input_tokens`, `llm.get_token_count(messages)`, `llm.format_messages_for_llm(...)`, `llm.format_messages_for_responses(...)`.
- `LLMConvertibleEvent.events_to_messages(events)` and `Message`, `TextContent`, `ImageContent`, `ThinkingBlock`, `RedactedThinkingBlock`, `ReasoningItemModel` from `openhands.sdk.llm`.
- Exceptions from `openhands.sdk.llm.exceptions` (`LLMContextWindowExceedError`, `LLMNoResponseError`, ...). Covers `S02.error-mapping`.
- Env vars: `ALLOW_SHORT_CONTEXT_WINDOWS`, `OH_INLINE_IMAGE_MAX_MB`, `OH_INLINE_IMAGE_FETCH_TIMEOUT_S`, `OH_INLINE_IMAGE_CACHE_BYTES`, `LOG_DIR` (default completions folder), and the `LLM_*` set read by `LLM.load_from_env`.

## Driving it

Preconditions:
- `uv sync --dev` has run.
- For example bullets: `LLM_API_KEY` exported, optionally `LLM_MODEL` and `LLM_BASE_URL`; `tmux` installed (examples use the terminal tool); network access.

- **Completion and API mode (`S02.completion`, `S02.api-mode`, `S02.native-tool-calling`).** Mocked LiteLLM proof, then a real call.
  ```sh
  uv run pytest tests/sdk/llm/test_llm_completion.py tests/sdk/llm/test_llm.py tests/sdk/llm/test_llm_litellm_extra_body.py -q
  uv run python examples/01_standalone_sdk/13_get_llm_metrics.py
  ```
  The tests pass; the example runs a short task and prints `llm.metrics` and `EXAMPLE_COST: <float>`.
- **Streaming and timeouts (`S02.streaming`, `S02.stream-no-callback`, `S02.timeouts`).**
  ```sh
  uv run pytest tests/sdk/llm/test_llm_completion.py::test_llm_completion_streaming_with_callback tests/sdk/llm/test_llm_completion.py::test_llm_streaming_without_callback_degrades tests/sdk/event/test_streaming.py tests/sdk/agent/test_stream_context.py tests/sdk/llm/test_llm_timeout.py -q
  uv run python examples/01_standalone_sdk/29_llm_streaming.py
  ```
  The tests pass; the example prints the story token by token with `THINKING:`, `CONTENT:`, `TOOL NAME:` and `TOOL ARGS:` prefixes as the stream switches kind.
- **Responses reasoning (`S02.responses-reasoning`).**
  ```sh
  uv run pytest tests/sdk/llm/test_responses_parsing_and_kwargs.py tests/sdk/llm/test_responses_serialization.py -q
  uv run python examples/01_standalone_sdk/23_responses_reasoning.py
  ```
  The tests pass; the example runs a conversation on `openhands/gpt-5-mini-2025-08-07` with `reasoning_effort="high"` and prints the LLM messages including reasoning.
- **Anthropic thinking and reasoning content (`S02.anthropic-thinking`, `S02.reasoning-content`, `S02.reasoning-options`).**
  ```sh
  uv run pytest tests/sdk/llm/test_thinking_blocks.py tests/sdk/llm/test_reasoning_content.py tests/sdk/llm/test_chat_options.py tests/sdk/llm/test_joint_budget_clamp.py -q
  LLM_MODEL=anthropic/claude-sonnet-4-5-20250929 uv run python examples/01_standalone_sdk/22_anthropic_thinking.py
  ```
  The tests pass; the example prints `Found N thinking blocks` with their text for each assistant turn.
- **Model features (`S02.model-features`).**
  ```sh
  uv run pytest tests/sdk/llm/test_model_features.py tests/sdk/llm/test_model_info_proxy_lookup.py tests/sdk/llm/test_model_canonical_name_resolution.py -q
  ```
  The tests pass.
- **Prompted tool calling (`S02.prompted-tool-calling`).**
  ```sh
  uv run pytest tests/sdk/llm/test_llm_fncall_converter.py tests/sdk/llm/test_llm_completion.py::test_llm_completion_non_function_call_mode -q
  ```
  The tests pass: tool schemas go into the prompt and text replies come back as tool calls.
- **Metrics and costs (`S02.metrics`, `S02.conversation-stats`, `S02.pricing-override`).**
  ```sh
  uv run pytest tests/sdk/llm/test_llm_metrics.py tests/sdk/conversation/test_conversation_stats.py tests/sdk/llm/test_llm_pricing_passthrough.py tests/sdk/llm/test_llm_span_cost.py -q
  uv run python examples/01_standalone_sdk/21_generate_extraneous_conversation_costs.py
  ```
  The tests pass; the example prints combined cost and tokens and a table with separate rows for `agent`, `condenser` (if it ran) and `demo-secondary`.
- **Retries and error mapping (`S02.retries`, `S02.no-response-retry`, `S02.error-mapping`).**
  ```sh
  uv run pytest tests/sdk/llm/test_api_connection_error_retry.py tests/sdk/llm/test_llm_no_response_retry.py tests/sdk/llm/test_llm_retry_telemetry.py tests/sdk/llm/test_auth_refresh_retry.py tests/sdk/llm/test_exception_mapping.py tests/sdk/llm/test_exception_classifier.py tests/sdk/llm/test_exception.py tests/sdk/llm/test_budget_denial_http.py -q
  ```
  The tests pass.
- **Caching, tokens, context guard (`S02.prompt-caching`, `S02.token-count`, `S02.context-window-guard`).**
  ```sh
  uv run pytest tests/sdk/llm/test_prompt_caching_cross_conversation.py tests/sdk/llm/test_llm.py::test_llm_token_counting tests/sdk/llm/test_llm.py::test_llm_raises_error_on_small_context_window tests/sdk/llm/test_llm.py::test_llm_respects_allow_short_context_windows_env_var -q
  ```
  The tests pass.
- **Message formatting from persisted events (`S02.message-formatting`).**
  ```sh
  uv run pytest tests/sdk/event/test_events_to_messages.py tests/sdk/llm/test_message.py tests/sdk/llm/test_message_serialization.py -q
  uv run python examples/01_standalone_sdk/36_event_json_to_openai_messages.py
  ```
  The tests pass; the example reloads `.conversations/<id>/events/event-*.json` and prints the Chat Completions (or Responses) payload built from them.
- **Image inlining, completion logs, serialization, env loading (`S02.image-inline`, `S02.log-completions`, `S02.serialization`).**
  ```sh
  uv run pytest tests/sdk/llm/test_image_inline.py tests/sdk/llm/test_llm_log_completions_integration.py tests/sdk/llm/test_llm_serialization.py tests/sdk/test_settings.py::test_llm_load_from_env_rehydrates_subscription_runtime -q
  ```
  The tests pass.
- **Provider compliance and thinking with a real model (`S02.error-mapping`, `S02.anthropic-thinking`).** Needs a model key.
  ```sh
  uv run python tests/integration/run_infer.py --llm-config '{"model": "litellm_proxy/anthropic/claude-opus-4-5", "extended_thinking": true}' --test-type condenser --eval-ids c01_thinking_block_condenser
  ```
  The task reports pass/fail in `tests/integration/outputs/`.

## Gotchas

- `22_anthropic_thinking.py` asserts `LLM_MODEL` is set and only shows thinking blocks on an Anthropic model; `23_responses_reasoning.py` ignores `LLM_MODEL` and hardcodes `openhands/gpt-5-mini-2025-08-07`, so it needs a key valid for the OpenHands provider (it also accepts `OPENAI_API_KEY`).
- `36_event_json_to_openai_messages.py` sets `LOG_JSON`, `LOG_TO_FILE`, `LOG_DIR`, `LOG_LEVEL` via `os.environ.setdefault` and writes `.conversations/` and a log dir in the repo root.
- `reasoning_effort` defaults to `high`, which costs extra tokens on reasoning models; set `"none"` or `None` to avoid it.
- `stream=True` without any `on_token` callback silently falls back to a non-streamed result; streaming does not show until a callback is wired (per call or `Conversation(token_callbacks=...)`).
- `ALLOW_SHORT_CONTEXT_WINDOWS` must be set for small local models or `LLM` construction fails with `LLMContextWindowTooSmallError`.
- `num_retries=5` with `retry_min_wait=8` and `retry_max_wait=64` means a dead endpoint can block for minutes before raising; lower them in tests.
- `LLM.load_from_env` has no general unit test; the only test covers the subscription rehydration case.
- Cost is 0 and LiteLLM warns `Cost calculation failed` for models it has no pricing for (seen in test output); set `input_cost_per_token`/`output_cost_per_token` for proxies.
- All pytest commands above passed on 4cc0582 (781 tests in the combined LLM set).
