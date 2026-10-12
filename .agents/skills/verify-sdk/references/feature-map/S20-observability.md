# Observability, tracing and logging

A Python program gets OpenTelemetry traces of its conversations by setting environment variables before it imports the SDK: `LMNR_PROJECT_API_KEY` sends them to Laminar, and `OTEL_ENDPOINT`, `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` or `OTEL_EXPORTER_OTLP_ENDPOINT` send them to any OTLP collector through Laminar's exporter. With none of these set (and no user-side `Laminar.initialize()`), every `@observe` decorator is a pass-through and `lmnr` is not even imported. When enabled, each `Conversation` owns a long-lived root span named `conversation` whose trace session id is the conversation id, with `user_id`, `observability_metadata` (also as span attributes), `observability_tags`, `conversation.tags.*` attributes and an optional named child span; `conversation.send_message` / `run` / `arun`, `agent.step`, tool calls (one TOOL span per call with `tool_call_id` metadata), MCP calls, condenser and hook calls, and LLM calls (an `LLM` span carrying cost and cache buckets) nest under it, across threads and parallel tool workers. Sub-agent conversations start their own trace linked back to the parent. The `openhands.sdk.automation` helpers turn the generic `OPENHANDS_OBSERVABILITY_*` env vars an automation runner sets into `Conversation(...)` kwargs and HTTP headers. Separately, `get_logger(__name__)` returns standard loggers under a root configured on import from `LOG_*` env vars (Rich console, or JSON in CI or with `LOG_JSON`, optional rotating file), with LiteLLM, OpenAI, httpx and libtmux loggers quieted.

Source: `openhands-sdk/openhands/sdk/observability/`, `openhands-sdk/openhands/sdk/automation/`, `openhands-sdk/openhands/sdk/logger/`, `openhands-sdk/openhands/sdk/conversation/base.py`, `openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py`, `openhands-sdk/openhands/sdk/agent/agent.py`, `openhands-sdk/openhands/sdk/agent/parallel_executor.py`, `openhands-sdk/openhands/sdk/llm/`

Needs: `llm`, `network`

Examples: `examples/01_standalone_sdk/27_observability_laminar.py`

## Sub-features

- `S20.enable-gate`: `should_enable_observability()` is true when any of `LMNR_PROJECT_API_KEY`, `OTEL_ENDPOINT`, `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, `OTEL_EXPORTER_OTLP_ENDPOINT` is set, or when the user already imported and initialized `lmnr`; the positive result is cached for the process. Unit: `tests/sdk/observability/test_laminar.py::test_should_enable_observability_returns_true_when_env_set`, `::test_should_enable_observability_returns_false_when_no_env`. Example: none. Real-LLM: none.
- `S20.lazy-import`: with observability off, decorated calls run unwrapped without importing `lmnr`; async functions keep their coroutine signature; a cold `import openhands.sdk` stays under 10 s (the guard against eager Laminar imports). Unit: `tests/sdk/observability/test_laminar.py::test_observe_preserves_async_signature`, `tests/sdk/test_import_performance.py`. Example: none. Real-LLM: none.
- `S20.laminar-init`: `maybe_init_laminar()` (run when `openhands.sdk.agent` is imported) calls `Laminar.initialize` once, passing `LMNR_BASE_URL` (unless empty), `LMNR_HTTP_PORT`/`LMNR_GRPC_PORT`, `LMNR_FORCE_HTTP` and `LMNR_INSTRUMENTS` (invalid names ignored with a warning), and skips when already initialized. Unit: `tests/sdk/observability/test_laminar.py::test_lmnr_base_url_passed_to_laminar`, `::test_lmnr_base_url_not_passed_when_empty`, `::test_maybe_init_laminar_skips_when_already_initialized`, `::test_lmnr_force_http_passed_to_laminar`, `::test_lmnr_instruments_passed_to_laminar`. Example: `examples/01_standalone_sdk/27_observability_laminar.py`. Real-LLM: none.
- `S20.otel-backend`: without `LMNR_PROJECT_API_KEY` but with an `OTEL_*` endpoint, Laminar initializes against the generic OTLP backend with browser-session, Patchright and Playwright instruments disabled. Unit: **none (untested)**. Example: none. Real-LLM: none.
- `S20.root-span`: each conversation starts a `conversation` root span (session id = conversation id, `user_id`, metadata, tags, attributes) that `@observe` methods re-attach in any thread or task, ends exactly once on `close()`, and does nothing when disabled; two concurrent conversations keep separate traces. Unit: `tests/sdk/observability/test_laminar.py` (`test_root_span_*`, `test_observe_calls_use_span_with_owner_root_span_*`, `test_two_concurrent_conversations_do_not_collide`), `tests/sdk/conversation/test_base_span_management.py`, `tests/sdk/conversation/local/test_span_double_ending.py`. Example: `examples/01_standalone_sdk/27_observability_laminar.py`. Real-LLM: none.
- `S20.conversation-args`: `Conversation(user_id=..., observability_metadata=..., observability_tags=..., observability_span_name=..., observability_parent_span_context=..., tags=...)` reach the root span: metadata and `conversation.tags.<key>` become attributes, a non-default span name becomes a child span, a parent context makes the trace a child of the caller's. Unit: `tests/sdk/conversation/test_base_span_management.py::test_base_conversation_passes_observability_metadata_and_tag_attributes`, `::test_base_conversation_uses_custom_observability_span_name_as_child_span`, `tests/sdk/conversation/test_conversation_factory.py::test_conversation_factory_forwards_local_observability_span_name`. Example: none. Real-LLM: none.
- `S20.env-conversation-defaults`: a local conversation also merges `OPENHANDS_OBSERVABILITY_METADATA` (JSON), uses `OPENHANDS_OBSERVABILITY_SPAN_NAME` when no span name is passed, and `OPENHANDS_OBSERVABILITY_PARENT_SPAN_CONTEXT` or `LMNR_SPAN_CONTEXT` as parent. Unit: **none (untested)** at the conversation level (the env readers are tested through `tests/sdk/test_automation_observability.py`). Example: none. Real-LLM: none.
- `S20.step-and-tool-spans`: `agent.step`/`agent.astep` spans contain one TOOL span per declared tool call, including rejected and cancelled calls, whose input is the action only and whose metadata carries `tool_call_id`. Unit: `tests/sdk/agent/test_tool_span_input.py`, `tests/sdk/agent/test_tool_span_tool_call_id_metadata.py`, `tests/sdk/observability/test_laminar.py::test_async_agent_and_conversation_paths_are_observed`. Example: none. Real-LLM: none.
- `S20.parallel-span-context`: parallel tool workers copy the context so their spans nest under the dispatcher, with and without `lmnr`, and overlapping tasks get fresh contexts. Unit: `tests/sdk/agent/test_parallel_tool_span_context.py`. Example: none. Real-LLM: none.
- `S20.llm-span`: each LLM call opens a current `LLM` span that records the authoritative proxy cost (matching `Metrics`), cache read and write buckets, closes on error and does not leak across retries. Unit: `tests/sdk/llm/test_llm_span_cost.py`. Example: none. Real-LLM: none.
- `S20.utility-operation-metadata`: side utilities (title generation and similar) mark their LLM spans with `openhands.operation` metadata (`OPERATION_METADATA_KEY`). Unit: `tests/sdk/conversation/test_utility_llm_span_metadata.py`. Example: none. Real-LLM: none.
- `S20.delegate-trace`: `detached_delegate_context()` makes a sub-agent conversation start a new trace instead of joining the parent's `task` span, yields `delegate.parent_trace_id`, `delegate.parent_span_id` and `tool_call_id`, restores the ambient span afterwards, and is a no-op when disabled. Unit: `tests/sdk/observability/test_laminar.py` (`test_detached_delegate_context_*`), `tests/tools/task/test_task_manager.py::TestTaskManager::test_delegate_metadata_includes_parent_span_link`. Example: none. Real-LLM: none.
- `S20.external-entry`: `init_laminar_for_external()` initializes Laminar and returns the current span context for a webhook-style caller to pass on. Unit: **none (untested)**. Example: none. Real-LLM: none.
- `S20.automation-context`: `automation_observability_context()` collects `OPENHANDS_OBSERVABILITY_METADATA`, `_TAGS` (comma list, deduplicated), `_SPAN_NAME` and `_PARENT_SPAN_CONTEXT` and merges caller additions. Unit: `tests/sdk/test_automation_observability.py::test_automation_observability_context_collects_generic_env`. Example: none. Real-LLM: none.
- `S20.automation-kwargs`: `automation_conversation_kwargs()` returns `Conversation(...)` kwargs with product `tags` built from `automation.*` metadata and the observability fields; an explicit span name overrides the env one. Unit: `tests/sdk/test_automation_observability.py::test_automation_conversation_tags_from_metadata`, `::test_automation_conversation_kwargs_include_product_and_observability_tags`, `::test_automation_conversation_kwargs_uses_env_span_name`, `::test_automation_conversation_kwargs_explicit_span_name_overrides_env`. Example: none. Real-LLM: none.
- `S20.automation-headers`: `automation_observability_headers()` / `observability_headers_from_env()` build `X-OpenHands-Observability-Metadata`, `-Tags`, `-Span-Name`, `-Parent-Span-Context` plus OTel propagation headers for direct agent-server calls; remote workspaces and remote conversations send them. Unit: `tests/sdk/test_automation_observability.py::test_automation_observability_headers_for_direct_api_calls`, `tests/sdk/workspace/remote/test_remote_workspace_mixin.py::test_headers_property_includes_observability_context`, `tests/sdk/workspace/remote/test_remote_workspace.py::test_send_completion_callback_includes_observability_headers`, `tests/sdk/conversation/remote/test_remote_conversation.py` (`-k observability`). Example: none. Real-LLM: none.
- `S20.get-env`: observability reads env vars straight from `os.environ`, never through python-dotenv's `find_dotenv()`. Unit: `tests/sdk/observability/test_utils.py`. Example: none. Real-LLM: none.
- `S20.logger-quiet-thirdparty`: importing the SDK sets LiteLLM and OpenAI loggers to ERROR (DEBUG only after a confirmed `DEBUG_LLM`), and httpx, httpcore and libtmux to WARNING, so LiteLLM INFO lines do not show. Unit: `tests/sdk/logger/test_litellm_log_suppression.py`. Example: none. Real-LLM: none.
- `S20.logger-config`: `get_logger(name)` returns a propagating stdlib logger; `setup_logging(...)` (auto-run on import unless `LOG_AUTO_CONFIG=false`) honors `LOG_LEVEL`, `DEBUG`, `LOG_JSON`, `CI`/`GITHUB_ACTIONS` (JSON console), `LOG_RICH_TRACEBACKS`, and `LOG_TO_FILE` with `LOG_DIR`, `LOG_ROTATE_WHEN`, `LOG_BACKUP_COUNT` (`<LOG_DIR>/app.log`), and does not add a second stream handler. Unit: **none (untested)**. Example: none. Real-LLM: none.
- `S20.rolling-log-view`: `rolling_log_view(logger, max_lines=...)` shows a live last-N-lines panel on a TTY, plain lines in CI, and one buffered JSON record on exit in JSON mode. Unit: **none (untested)**. Example: none. Real-LLM: none.

## How to get to it (agent POV)

- Env vars, set before `import openhands.sdk`: `LMNR_PROJECT_API_KEY`, `LMNR_BASE_URL`, `LMNR_HTTP_PORT`, `LMNR_GRPC_PORT`, `LMNR_FORCE_HTTP`, `LMNR_INSTRUMENTS`, `LMNR_SPAN_CONTEXT`; `OTEL_ENDPOINT`, `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_TRACES_HEADERS`, `OTEL_EXPORTER_OTLP_TRACES_PROTOCOL`, `OTEL_EXPORTER`. Covers `S20.enable-gate`, `S20.laminar-init`, `S20.otel-backend`.
- `Conversation(..., user_id=..., tags={...}, observability_metadata={...}, observability_tags=[...], observability_span_name="...", observability_parent_span_context="...")` (`S20.root-span`, `S20.conversation-args`).
- `openhands.sdk.observability`: `observe(name=..., span_type="TOOL", ...)` to trace a user function, `maybe_init_laminar()`, `init_laminar_for_external()`, `OPERATION_METADATA_KEY`.
- `OPENHANDS_OBSERVABILITY_METADATA` (JSON object), `OPENHANDS_OBSERVABILITY_TAGS`, `OPENHANDS_OBSERVABILITY_SPAN_NAME`, `OPENHANDS_OBSERVABILITY_PARENT_SPAN_CONTEXT`, and `openhands.sdk.automation`: `automation_observability_context`, `automation_conversation_kwargs`, `automation_conversation_tags`, `automation_observability_headers` (`S20.automation-*`, `S20.env-conversation-defaults`).
- `openhands.sdk.logger` (also `openhands.sdk.get_logger`): `get_logger`, `setup_logging`, `rolling_log_view`; env `LOG_LEVEL`, `DEBUG`, `LOG_JSON`, `LOG_TO_FILE`, `LOG_DIR`, `LOG_ROTATE_WHEN`, `LOG_BACKUP_COUNT`, `LOG_RICH_TRACEBACKS`, `LOG_AUTO_CONFIG`, `DEBUG_LLM` (`S20.logger-*`, `S20.rolling-log-view`).

## Driving it

Preconditions:
- `uv sync --dev` has run (`lmnr` is a core dependency of `openhands-sdk`).
- For the example: `LLM_API_KEY`, `LLM_MODEL`, and `LMNR_PROJECT_API_KEY` (or an `OTEL_*` endpoint) exported, and network to the trace backend.

- **Enablement, init, root spans, delegate traces (`S20.enable-gate`, `S20.lazy-import`, `S20.laminar-init`, `S20.root-span`, `S20.delegate-trace`, `S20.get-env`).** Laminar is mocked.
  ```sh
  uv run pytest tests/sdk/observability -q
  uv run pytest tests/sdk/test_import_performance.py -q
  ```
  All tests pass.
- **Conversation span arguments (`S20.root-span`, `S20.conversation-args`).**
  ```sh
  uv run pytest tests/sdk/conversation/test_base_span_management.py tests/sdk/conversation/local/test_span_double_ending.py tests/sdk/conversation/test_conversation_factory.py -q
  ```
  All tests pass.
- **Step, tool, parallel, LLM and utility spans (`S20.step-and-tool-spans`, `S20.parallel-span-context`, `S20.llm-span`, `S20.utility-operation-metadata`).** Most of these export to an in-memory OTel exporter (`InMemorySpanExporter`).
  ```sh
  uv run pytest tests/sdk/agent/test_tool_span_input.py tests/sdk/agent/test_tool_span_tool_call_id_metadata.py tests/sdk/agent/test_parallel_tool_span_context.py tests/sdk/llm/test_llm_span_cost.py tests/sdk/conversation/test_utility_llm_span_metadata.py -q
  ```
  All tests pass.
- **Automation helpers and headers (`S20.automation-context`, `S20.automation-kwargs`, `S20.automation-headers`, `S20.env-conversation-defaults`).** The env readers are covered here; the conversation-level merge is not.
  ```sh
  uv run pytest tests/sdk/test_automation_observability.py tests/sdk/workspace/remote/test_remote_workspace_mixin.py -q
  uv run pytest tests/sdk/workspace/remote/test_remote_workspace.py::test_send_completion_callback_includes_observability_headers -q
  uv run pytest tests/sdk/conversation/remote/test_remote_conversation.py -q -k observability
  ```
  All tests pass.
- **Third-party log suppression (`S20.logger-quiet-thirdparty`).**
  ```sh
  uv run pytest tests/sdk/logger -q
  ```
  3 tests pass.
- **Live Laminar trace (`S20.laminar-init`, `S20.root-span`), blocked without a Laminar key.**
  ```sh
  LMNR_PROJECT_API_KEY=... uv run python examples/01_standalone_sdk/27_observability_laminar.py
  ```
  The script prints `All done!`; the Laminar dashboard shows one trace whose session is the conversation id, with `conversation.send_message`, `conversation.run`, `agent.step`, a terminal TOOL span and LLM spans.
- **External entry (`S20.external-entry`), untested.** Nothing calls `init_laminar_for_external()` in tests or examples, so there is no recipe yet.
- **Generic OTLP backend (`S20.otel-backend`), untested.** Point `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` at a collector (with `OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf` for HTTP) and run example 27 without `LMNR_PROJECT_API_KEY`; spans should reach the collector. No test covers this branch.
- **Logging configuration (`S20.logger-config`, `S20.rolling-log-view`), untested.** For example `LOG_JSON=1 LOG_TO_FILE=1 LOG_DIR=/tmp/ohlogs uv run python -c "from openhands.sdk import get_logger; get_logger('x').info('hi')"` should print one JSON line and write `/tmp/ohlogs/app.log`. No test covers it.

## Gotchas

- Enablement is decided from env vars at import and at each decorated call, and `maybe_init_laminar()` runs when `openhands.sdk.agent` is imported: set `LMNR_PROJECT_API_KEY` / `OTEL_*` before importing the SDK, or call `Laminar.initialize()` yourself first.
- Once enabled, the process stays enabled (cached); tests that toggle it reset the module global.
- `27_observability_laminar.py` is in `_EXCLUDED_EXAMPLES`; it never runs in CI and does not print `EXAMPLE_COST`. Without a key it still runs the conversation, just without traces.
- `LOG_*` and `DEBUG_LLM` are read once at import. `DEBUG_LLM=true` calls `input()` at import to confirm, which blocks or raises `EOFError` in a non-interactive run.
- `setup_logging` never removes handlers and skips adding a stream handler if one exists (Uvicorn or a test runner may already have one), so `LOG_JSON` can appear to do nothing.
- `CI=true` or `GITHUB_ACTIONS` switches console logs to JSON.
- `tests/sdk/test_import_performance.py` measures import time and can be slow or flaky on a loaded machine; the S20 batch took about 50 s here.
- Agent-server telemetry (`tests/agent_server/telemetry/`) and server-side span routes belong to the server map, not here.
