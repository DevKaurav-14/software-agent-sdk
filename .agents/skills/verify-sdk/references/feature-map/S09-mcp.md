# MCP client and tools

A Python program gives an agent Model Context Protocol servers with `Agent(mcp_config={"name": MCPServer(...)})`: a local server started as a subprocess (`command`, `args`, `env`, `cwd`; stdio transport), or a remote one reached over streamable HTTP or SSE (`url`, `transport`, `headers`, `auth`). When the conversation initializes the agent, the SDK opens one FastMCP client for all enabled servers on a background event loop, lists their tools, and turns each MCP tool into an `MCPToolDefinition` whose JSON schema becomes the model-facing tool (with `summary` and, when a security analyzer is set, `security_risk` added). Tool names are the MCP names, prefixed with `<server>_` when there are several servers. A call validates the model's arguments against the schema, expands `$VAR` secret references from the conversation, sends `tools/call` over the same session, and returns an `MCPToolObservation` with text and images (secrets masked, errors as `is_error`). The session survives between calls, is reconnected once if it drops, and follows `notifications/tools/list_changed`. Remote servers can authenticate with a bearer token, API key, basic auth, custom header or OAuth 2 (dynamic client registration and token refresh against the discovered token endpoint). A server that fails to start is logged and skipped; the conversation continues without its tools.

Source: `openhands-sdk/openhands/sdk/mcp/`, `openhands-sdk/openhands/sdk/agent/base.py`, `openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py`, `openhands-sdk/openhands/sdk/skills/utils.py` (MCP variable expansion)

Needs: `llm` (examples), `uvx` and `node` (example 07's `fetch` and `repomix` servers), `network` (example 07 reads GitHub, example 08 reaches Notion)

Examples: `examples/01_standalone_sdk/07_mcp_integration.py`, `examples/01_standalone_sdk/08_mcp_with_oauth.py`

## Sub-features

- `S09.config-model`: `MCPServer` forbids unknown fields, requires `command` for stdio and `url` for remote transports, refuses `auth` together with an explicit `Authorization` header, and `coerce_mcp_config` also accepts the external `{"mcpServers": {...}}` shape while `create_mcp_tools` rejects it. Unit: `tests/sdk/mcp/test_create_mcp_tool.py` (`test_create_mcp_tools_rejects_external_config_shapes`). Example: none. Real-LLM: none.
- `S09.config-secrets`: `env`, `headers` and credential values are `SecretStr`, redacted in dumps unless a cipher is in context, round-trip through encrypted JSON, and never appear in persisted conversation state or state-update events. Unit: `tests/sdk/mcp/test_mcp_config_secrets.py`, `tests/sdk/conversation/test_mcp_secrets_serialization_leak.py`. Example: none. Real-LLM: none.
- `S09.stdio-server`: a `command`/`args` server is started as a subprocess and its tools are listed with their input schemas. Unit: `tests/sdk/mcp/test_create_mcp_tool.py::test_create_mcp_tools_stdio_server` (spawns `tests/sdk/mcp/stdio_test_server.py`). Example: `examples/01_standalone_sdk/07_mcp_integration.py`. Real-LLM: none.
- `S09.http-sse-server`: `url` servers connect over streamable HTTP or SSE (transport inferred from a `/sse` URL when omitted), tools from several servers carry `<server>_` prefixes, and calls return the server's result. Unit: `tests/sdk/mcp/test_create_mcp_tool.py` (`test_create_mcp_tools_http_server`, `test_create_mcp_tools_sse_server`, `test_create_mcp_tools_mixed_servers`, `test_create_mcp_tools_transport_inferred_from_url`, `test_execute_http_tool`, `test_execute_sse_tool`). Example: none. Real-LLM: none.
- `S09.static-auth`: `auth` strategies `none`, `bearer`, `api_key` (custom `header_name`), `basic` and `header` turn into the right HTTP headers. Unit: `tests/sdk/mcp/test_create_mcp_tool.py::test_mcp_auth_credentials_to_http_headers`. Example: none. Real-LLM: none.
- `S09.oauth`: `auth=MCPOAuthAuthCredential(strategy="oauth2", authentication=MCPOAuthAuthentication(...))` builds a FastMCP OAuth client with the given scopes, client id/secret or metadata URL and an optional token store or factory; an expired token is refreshed against the token endpoint discovered from server metadata, falling back to `<origin>/token`, and a valid token is sent without discovery. Unit: `tests/sdk/mcp/test_oauth.py`, `tests/sdk/mcp/test_create_mcp_tool.py` (`test_prepare_mcp_config_*oauth*`). Example: `examples/01_standalone_sdk/08_mcp_with_oauth.py`. Real-LLM: none.
- `S09.enabled-flag`: `MCPServer(enabled=False)` keeps a server configured but never connects to it; if every server is disabled `create_mcp_tools` raises and the conversation skips MCP entirely. Unit: `tests/sdk/mcp/test_create_mcp_tool.py` (`test_create_mcp_tools_skips_disabled_servers`, `test_create_mcp_tools_all_servers_disabled`), `tests/sdk/conversation/test_local_conversation_mcp.py::test_disabling_every_server_skips_the_mcp_connection`. Example: none. Real-LLM: none.
- `S09.listing-timeout`: tool listing that exceeds `timeout` (30 s in a conversation) raises `MCPTimeoutError` naming the servers and closes the client; an unreachable server raises. Unit: `tests/sdk/mcp/test_create_mcp_tool.py` (`test_create_mcp_tools_timeout_error_message`, `test_create_mcp_tools_connection_to_nonexistent_server`). Example: none. Real-LLM: none.
- `S09.startup-failure-tolerated`: when MCP startup fails inside a `LocalConversation`, a warning is logged and the conversation runs with its other tools. Unit: `tests/sdk/conversation/test_local_conversation_mcp.py::test_mcp_startup_failure_does_not_abort_conversation`. Example: none. Real-LLM: none.
- `S09.schema-conversion`: an MCP `inputSchema` becomes the tool's OpenAI and Responses parameters with nested objects, arrays, required lists and descriptions preserved, plus `summary` and (with a security analyzer) `security_risk`; MCP annotations are kept. Unit: `tests/sdk/mcp/test_mcp_nested_schema.py`, `tests/sdk/mcp/test_mcp_security_risk.py`, `tests/sdk/mcp/test_mcp_tool.py`. Example: none. Real-LLM: none.
- `S09.argument-validation`: `action_from_arguments` validates the model's arguments against the schema, removes OpenHands-only fields (`security_risk`, `summary`, `kind`) and `None` values before the call, keeps a schema property literally named `kind`, and raises on invalid input. Unit: `tests/sdk/mcp/test_mcp_tool_validation.py`, `tests/sdk/mcp/test_mcp_tool_kind_field.py`, `tests/sdk/mcp/test_mcp_action_serialization.py`. Example: none. Real-LLM: none.
- `S09.observation`: a `CallToolResult` becomes an `MCPToolObservation` with text and image content, `isError` mapped to `is_error`, structured JSON rendered as text; an exception or timeout (300 s per call) becomes an error observation. Unit: `tests/sdk/mcp/test_mcp_tool.py`, `tests/sdk/mcp/test_mcp_observation.py`. Example: none. Real-LLM: none.
- `S09.secret-refs-in-calls`: `$VAR`, `${VAR}` and `${VAR:-default}` in a call's arguments are expanded from the conversation's secret registry (never from the host environment), and secret values in the result text are masked. Unit: `tests/sdk/mcp/test_mcp_secret_expansion.py`. Example: none. Real-LLM: none.
- `S09.session-reuse`: all calls share one connected session, so server-side session state (counters, auth tokens) persists across calls and tools, and closing the client releases the connection. Unit: `tests/sdk/mcp/test_mcp_session_persistence.py`, `tests/sdk/mcp/test_stateful_mcp.py`. Example: none. Real-LLM: none.
- `S09.session-recovery`: if the session was lost (for example after an HTTP 503), the next call reconnects once and retries; a closed client or a failed reconnect returns an error observation instead of raising. Unit: `tests/sdk/mcp/test_mcp_tool.py` (`test_call_tool_reconnects_when_session_lost`, `test_call_tool_fails_when_client_closed`, `test_call_tool_fails_when_reconnect_fails`), `tests/sdk/mcp/test_create_mcp_tool.py::test_mcp_tool_reconnects_after_http_error`. Example: none. Real-LLM: none.
- `S09.tools-list-changed`: on `notifications/tools/list_changed` the client re-lists tools, reports only new ones to `on_tools_changed`, sends the full snapshot (additions, updates, removals) to `on_tools_reconciled`, and the agent registers them on its current instance; a custom `MCPToolProvider` without `on_tools_reconciled` still works. Unit: `tests/sdk/mcp/test_mcp_tool_list_changed.py`, `tests/sdk/conversation/test_local_conversation_mcp.py` (`test_reconciliation_targets_replaced_agent`, `test_legacy_provider_without_on_tools_reconciled_still_works`). Example: none. Real-LLM: none.
- `S09.filter-tools-regex`: `Agent(filter_tools_regex=...)` filters MCP and static tools by name while built-in tools stay. Unit: `tests/sdk/agent/test_filter_tools_regex.py`. Example: `examples/01_standalone_sdk/07_mcp_integration.py` (keeps only `repomix` `pack_codebase`). Real-LLM: none.
- `S09.config-var-expansion`: `${VAR}` and `${VAR:-default}` placeholders in `Agent.mcp_config` (and Claude Code plugin `.mcp.json`) are expanded from conversation secrets before servers start. Unit: `tests/sdk/skills/test_mcp_config_expansion.py`, `tests/sdk/conversation/test_local_conversation_plugins.py::TestPluginMcpSecretsExpansion`. Example: none. Real-LLM: none.
- `S09.tool-serialization`: `MCPToolDefinition` is frozen, serializes polymorphically with `kind`, is written in the MCP wire spelling (`inputSchema`) and loads either spelling, so conversations persisted under older `mcp` majors resume. Unit: `tests/sdk/mcp/test_mcp_tool_serialization.py`, `tests/sdk/mcp/test_mcp_tool_immutability.py`, `tests/sdk/mcp/test_mcp_wire_compat.py`. Example: none. Real-LLM: none.

## How to get to it (agent POV)

- `Agent(llm=..., tools=[...], mcp_config={"fetch": MCPServer(command="uvx", args=[...]), "remote": MCPServer(url="https://.../mcp", transport="http", headers={...}, auth=...)}, filter_tools_regex=...)`. `MCPServer`, `MCPOAuthAuthCredential`, `MCPOAuthAuthentication` import from `openhands.sdk.mcp`; the static credential classes (`MCPBearerAuthCredential`, `MCPApiKeyAuthCredential`, `MCPBasicAuthCredential`, `MCPHeaderAuthCredential`, `MCPNoneAuthCredential`) from `openhands.sdk.mcp.config`. Covers every sub-feature through a conversation.
- `LocalConversation(agent=..., mcp_tool_provider=MyProvider())` (not accepted by the `Conversation` factory) replaces how MCP clients are created; `DefaultMCPToolProvider` is the default. `S09.tools-list-changed`.
- Direct use without an agent: `with create_mcp_tools(mcp_config, timeout=30.0, on_tools_changed=..., on_tools_reconciled=..., mcp_oauth_token_storage=..., mcp_oauth_factory=...) as client: for tool in client.tools: ...`; `tool(action)` or `tool.action_from_arguments({...})`. Covers `S09.stdio-server`, `S09.http-sse-server`, `S09.listing-timeout`, `S09.argument-validation`.
- `conversation.update_secrets({...})` / `Conversation(secrets=...)` feed `S09.secret-refs-in-calls` and `S09.config-var-expansion`.
- Plugins add servers through `.mcp.json` or `mcp.json` (S08); sub-agents can carry their own `mcp_config` (S11).
- Env vars: none of its own; examples read `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`.

## Driving it

Preconditions:

- `uv sync --dev` has run (provides `fastmcp`, `uvicorn` for the in-test HTTP and SSE servers).
- `LLM_API_KEY` and `LLM_MODEL` exported for the example bullets; `uvx` and `npx` on `PATH` for example 07.

- **Config model, secrets, auth, OAuth (`S09.config-model`, `S09.config-secrets`, `S09.static-auth`, `S09.oauth`, `S09.enabled-flag`).**
  ```sh
  uv run pytest tests/sdk/mcp/test_create_mcp_tool.py tests/sdk/mcp/test_mcp_config_secrets.py tests/sdk/mcp/test_oauth.py tests/sdk/conversation/test_mcp_secrets_serialization_leak.py -q
  ```
  All pass; HTTP and SSE servers run in-process on local ports, the stdio server is `python -m tests.sdk.mcp.stdio_test_server`.
- **Transports, sessions, recovery and dynamic tool lists (`S09.stdio-server`, `S09.http-sse-server`, `S09.listing-timeout`, `S09.session-reuse`, `S09.session-recovery`, `S09.tools-list-changed`).**
  ```sh
  uv run pytest tests/sdk/mcp/test_mcp_session_persistence.py tests/sdk/mcp/test_stateful_mcp.py tests/sdk/mcp/test_mcp_tool.py tests/sdk/mcp/test_mcp_tool_list_changed.py -q
  ```
  All pass.
- **Schemas, arguments, observations, serialization (`S09.schema-conversion`, `S09.argument-validation`, `S09.observation`, `S09.secret-refs-in-calls`, `S09.tool-serialization`).**
  ```sh
  uv run pytest tests/sdk/mcp/test_mcp_nested_schema.py tests/sdk/mcp/test_mcp_security_risk.py tests/sdk/mcp/test_mcp_tool_validation.py tests/sdk/mcp/test_mcp_tool_kind_field.py tests/sdk/mcp/test_mcp_action_serialization.py tests/sdk/mcp/test_mcp_observation.py tests/sdk/mcp/test_mcp_secret_expansion.py tests/sdk/mcp/test_mcp_tool_serialization.py tests/sdk/mcp/test_mcp_tool_immutability.py tests/sdk/mcp/test_mcp_wire_compat.py -q
  ```
  All pass.
- **MCP inside a conversation (`S09.startup-failure-tolerated`, `S09.enabled-flag`, `S09.tools-list-changed`, `S09.filter-tools-regex`, `S09.config-var-expansion`).**
  ```sh
  uv run pytest tests/sdk/conversation/test_local_conversation_mcp.py tests/sdk/agent/test_filter_tools_regex.py tests/sdk/skills/test_mcp_config_expansion.py -q
  ```
  All pass.
- **stdio servers with a real model (`S09.stdio-server`, `S09.filter-tools-regex`, `S09.observation`).**
  ```sh
  uv run python examples/01_standalone_sdk/07_mcp_integration.py
  ```
  The agent fetches the OpenHands GitHub page through the `fetch` MCP tool, writes `FACTS.txt` with three facts in the current directory, then deletes it on the second message; only `repomix`'s `pack_codebase` tool is offered. Uses an `LLMSecurityAnalyzer`, so tool schemas carry `security_risk`.
- **OAuth with a real provider (`S09.oauth`), blocked.** Needs an interactive browser login to Notion and a Notion workspace; it cannot run headless or in CI.
  ```sh
  uv run python examples/01_standalone_sdk/08_mcp_with_oauth.py
  ```
  A browser opens for the Notion consent screen; after login the agent searches the workspace for "OpenHands V1".

## Gotchas

- `examples/01_standalone_sdk/08_mcp_with_oauth.py` is in `_EXCLUDED_EXAMPLES` of `tests/examples/test_examples.py`; the OAuth flow has only the mocked tests in `tests/sdk/mcp/test_oauth.py`.
- Example 07 pins `mcp-server-fetch==2026.7.10` through `uvx` and `repomix@1.4.2` through `npx`; the first run downloads both, which can exceed the 30 s listing timeout on a cold cache. The conversation then logs `MCP server startup failed ... continuing without its tools` and the agent has no `fetch` tool instead of failing.
- MCP startup failures inside a conversation are warnings, not errors; check the log or `conversation.agent.tools_map` to confirm the MCP tools exist before judging the model.
- With two or more servers, tool names are prefixed `<server>_<tool>`; with one server they are not. A `filter_tools_regex` written for one case drops tools in the other.
- Remote `http://` URLs are accepted for `Agent.mcp_config`; only Agent Plugins packages (S08) require `https` for non-loopback hosts.
- A bare `MCPOAuthAuthCredential(strategy="oauth2")` without a token store leaves the flow to FastMCP's interactive browser login; in a sandbox without a browser, pass `mcp_oauth_token_storage` or a pre-registered client through `MCPOAuthAuthentication`.
- MCP clients run on a background event loop thread; `on_tools_changed` and `on_tools_reconciled` callbacks run on that thread and must be thread-safe.
