# Security analyzers, confirmation mode and secrets

A Python program decides, per conversation, whether the agent's tool calls run straight away or stop for approval. Every tool schema the agent sends carries a `security_risk` field (`LOW`, `MEDIUM`, `HIGH`), and the system prompt carries a risk policy (built in, or a custom file through `Agent(security_policy_filename=...)`). `conversation.set_security_analyzer(...)` picks who rates each pending action: the actor LLM's own label (`LLMSecurityAnalyzer`), local deterministic rules (`PatternSecurityAnalyzer`, `PolicyRailSecurityAnalyzer`, composed with `EnsembleSecurityAnalyzer`), a separate guardrail LLM (`ToolShieldLLMSecurityAnalyzer`) or the Gray Swan API (`GraySwanAnalyzer`); each verdict is recorded as a `SecurityAnalysisEvent`. `conversation.set_confirmation_policy(...)` (`NeverConfirm`, `AlwaysConfirm`, `ConfirmRisky(threshold, confirm_unknown)`) then decides: when it says confirm, `run()` returns with `execution_status == WAITING_FOR_CONFIRMATION`, the program reads the pending actions, and either calls `run()` again to execute them or `reject_pending_actions(reason)` to turn them into `UserRejectObservation`s. Secrets given to `Conversation(secrets=...)` or `conversation.update_secrets(...)` (plain strings, `StaticSecret`, `LookupSecret` URLs, or custom `SecretSource`s) are exported as env vars to terminal commands that reference them, listed by name in the system prompt, and replaced with `<secret-hidden>` in every tool observation, agent message, and analysis event before callbacks or persistence see them.

Source: `openhands-sdk/openhands/sdk/security/`, `openhands-sdk/openhands/sdk/secret/`, `openhands-sdk/openhands/sdk/conversation/secret_registry.py`, `openhands-sdk/openhands/sdk/agent/agent.py`, `openhands-sdk/openhands/sdk/agent/base.py`, `openhands-sdk/openhands/sdk/conversation/base.py`, `openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py`, `openhands-sdk/openhands/sdk/tool/tool.py`, `openhands-sdk/openhands/sdk/settings/model.py`

Needs: `llm`, `network`

Examples: `examples/01_standalone_sdk/04_confirmation_mode_example.py`, `examples/01_standalone_sdk/16_llm_security_analyzer.py`, `examples/01_standalone_sdk/32_configurable_security_policy.py`, `examples/01_standalone_sdk/47_defense_in_depth_security.py`, `examples/01_standalone_sdk/12_custom_secrets.py`

## Sub-features

- `S13.risk-levels`: `SecurityRisk` orders `LOW < MEDIUM < HIGH`, `is_riskier` is reflexive, comparing `UNKNOWN` raises, `max` works on concrete risks. Unit: `tests/sdk/security/test_security_risk.py`. Example: none. Real-LLM: none.
- `S13.policies`: `NeverConfirm` never and `AlwaysConfirm` always asks; `ConfirmRisky` asks at or above `threshold` (default `HIGH`, `UNKNOWN` not allowed as threshold) and for `UNKNOWN` when `confirm_unknown=True` (default); policies round-trip polymorphically. Unit: `tests/sdk/security/test_confirmation_policy.py`, `tests/sdk/security/defense_in_depth/test_pattern.py` (`ConfirmRisky().should_confirm`), `tests/sdk/agent/test_security_analysis_event.py`. Example: `examples/01_standalone_sdk/47_defense_in_depth_security.py`. Real-LLM: none.
- `S13.confirm-wait`: with a confirming policy, `run()` stops in `WAITING_FOR_CONFIRMATION` before executing; `ConversationState.get_unmatched_actions(events)` returns the pending actions; a message-only response does not wait; a lone `FinishAction` or `ThinkAction` never waits; pausing keeps the waiting status; `is_confirmation_mode_active` reflects analyzer plus non-Never policy. Unit: `tests/sdk/conversation/local/test_confirmation_mode.py`. Example: `examples/01_standalone_sdk/04_confirmation_mode_example.py`. Real-LLM: none.
- `S13.confirm-approve-reject`: calling `run()` again executes the pending actions; `reject_pending_actions(reason)` emits a `UserRejectObservation` per action and the agent continues. Unit: `tests/sdk/conversation/local/test_confirmation_mode.py::TestConfirmationMode::test_action_then_confirm_or_reject`. Example: `examples/01_standalone_sdk/04_confirmation_mode_example.py`. Real-LLM: none.
- `S13.risk-extraction`: the agent pops `security_risk` from tool arguments; read-only tools and conversations without an analyzer get `UNKNOWN`; an invalid label raises. Unit: `tests/sdk/agent/test_extract_security_risk.py`, `tests/sdk/agent/test_security_policy_integration.py::test_security_risk_param_ignored_when_no_analyzer`. Example: none. Real-LLM: none.
- `S13.llm-analyzer`: `LLMSecurityAnalyzer` returns the risk the actor LLM put on the `ActionEvent`; combined with `ConfirmRisky` only HIGH (and UNKNOWN) actions stop. Unit: `tests/sdk/security/test_llm_security_analyzer.py`. Example: `examples/01_standalone_sdk/16_llm_security_analyzer.py`. Real-LLM: none.
- `S13.analysis-event`: each confirmation check with an analyzer emits one `SecurityAnalysisEvent` (analyzer and policy class names, `risks` and `details` keyed by action id) before the wait, even under `NeverConfirm`; an analyzer exception rates the action `HIGH` with the error as detail; secrets in it are masked for callbacks and persistence. Unit: `tests/sdk/agent/test_security_analysis_event.py`, `tests/sdk/security/test_security_analyzer.py`. Example: none. Real-LLM: none.
- `S13.security-policy-prompt`: the default risk policy is in the system message; `security_policy_filename` swaps in a custom file inserted verbatim (not Jinja-rendered); `None` or an empty file disables it without leaking the default; risk-assessment instructions stay with or without an analyzer. Unit: `tests/sdk/agent/test_security_policy_integration.py`. Example: `examples/01_standalone_sdk/32_configurable_security_policy.py`. Real-LLM: none.
- `S13.pattern-analyzer`: `PatternSecurityAnalyzer` normalizes Unicode evasions (fullwidth, zero-width, bidi, controls), scans tool name and arguments for destructive, code-execution and fetch-to-exec signatures and all fields (including thought and summary) for injection; reasoning alone does not trip exec patterns; input is capped with arguments first. Unit: `tests/sdk/security/defense_in_depth/test_pattern.py`, `tests/sdk/security/defense_in_depth/test_field_cap.py`, `tests/sdk/security/defense_in_depth/test_adversarial.py`. Example: `examples/01_standalone_sdk/47_defense_in_depth_security.py`. Real-LLM: none.
- `S13.policy-rails`: `PolicyRailSecurityAnalyzer` returns HIGH for fetch piped to a shell, raw-disk `dd`/`mkfs`, and catastrophic `rm` of `/` or home, LOW for safe commands, using the tree-sitter shell AST (quoted, path-qualified and `sh -c` nested verbs resolved; depth bound and parse errors map to UNKNOWN). Unit: `tests/sdk/security/defense_in_depth/test_policy_rails.py`, `tests/sdk/security/defense_in_depth/test_shell_semantics.py`, `tests/sdk/security/defense_in_depth/test_shell_parser_bypasses.py`, `tests/sdk/security/test_shell_ast.py`, `tests/sdk/security/test_shell_parser.py`, `tests/sdk/security/test_shell_parser_node_shapes.py`. Example: `examples/01_standalone_sdk/47_defense_in_depth_security.py`. Real-LLM: none.
- `S13.ensemble`: `EnsembleSecurityAnalyzer(analyzers=[...])` takes the maximum concrete risk, fails closed to HIGH on a child exception, ignores UNKNOWN next to a concrete verdict unless `propagate_unknown=True`, rejects an empty list, and serializes with nested children. Unit: `tests/sdk/security/defense_in_depth/test_ensemble.py`, `tests/sdk/security/defense_in_depth/test_serialization.py`. Example: `examples/01_standalone_sdk/47_defense_in_depth_security.py`. Real-LLM: none.
- `S13.toolshield`: `ToolShieldLLMSecurityAnalyzer(llm=..., history_window, safety_experiences)` asks a separate guardrail LLM about the action plus recent history, wraps untrusted fields in escaped XML, accepts only one standalone risk label (smuggled or conflicting labels give UNKNOWN); helpers detect active MCP tools and load ToolShield safety experiences. Unit: `tests/sdk/security/test_toolshield_llm_analyzer.py` (7 tests skip without the `toolshield` extra). Example: none. Real-LLM: none.
- `S13.grayswan`: `GraySwanAnalyzer` reads `GRAYSWAN_API_KEY` / `GRAYSWAN_POLICY_ID`, sends recent events as OpenAI messages to the Gray Swan API, maps the violation score with `low_threshold`/`medium_threshold` (indirect prompt injection escalates to HIGH), and returns UNKNOWN on error, timeout or no key. Unit: `tests/sdk/security/grayswan/test_grayswan_analyzer.py`, `tests/sdk/security/grayswan/test_grayswan_utils.py`. Example: none. Real-LLM: none.
- `S13.settings-security`: `ConversationSettings(confirmation_mode=True, security_analyzer="llm")` builds `ConfirmRisky` plus `LLMSecurityAnalyzer` (no analyzer gives `AlwaysConfirm`; off gives `NeverConfirm`). Unit: `tests/sdk/test_settings.py::test_conversation_settings_create_request`. Example: none. Real-LLM: none.
- `S13.secret-sources`: `StaticSecret` and `LookupSecret` (URL plus headers, relative URLs resolved against the current server, `register_local_secret_resolver` short-circuits HTTP and falls back when it declines or raises) redact values and sensitive headers on dump unless exposed or encrypted with a cipher. Unit: `tests/sdk/conversation/test_secret_source.py`. Example: `examples/01_standalone_sdk/12_custom_secrets.py`. Real-LLM: none.
- `S13.secret-registry`: `SecretRegistry.update_secrets` adds or overwrites; `find_secrets_in_text` matches names case-insensitively; `get_secrets_as_env_vars(command)` resolves only referenced names (a failing source is skipped); resolved values are tracked for masking. Unit: `tests/sdk/conversation/test_secrets_manager.py`. Example: `examples/01_standalone_sdk/12_custom_secrets.py`. Real-LLM: none.
- `S13.secret-injection`: secrets from `Conversation(secrets=...)`, `update_secrets(...)` and `AgentContext.secrets` (request wins on collision) reach the terminal as env vars and appear by name in the dynamic system context. Unit: `tests/sdk/conversation/test_conversation_secrets_constructor.py`, `tests/cross/test_agent_secrets_integration.py`. Example: `examples/01_standalone_sdk/12_custom_secrets.py`. Real-LLM: none.
- `S13.mask-output`: `mask_secrets_in_output` replaces every tracked value with `<secret-hidden>`, survives a serialization round trip, tolerates and backs off failing sources; the streaming mask catches a value split across chunks. Unit: `tests/sdk/conversation/test_secrets_manager.py` (`test_mask_secrets_*`, `test_compile_stream_mask_*`), `tests/cross/test_agent_secrets_integration.py::test_mask_secrets`, `::test_masking_persists`. Example: `examples/01_standalone_sdk/12_custom_secrets.py`. Real-LLM: none.
- `S13.mask-tool-output`: every tool observation goes through `ToolDefinition.__call__`, which masks it with `mask_secrets_in_model`: file editor views, grep's echoed pattern, glob paths and nested apply-patch content are masked; no tool bypasses it; without a conversation nothing is masked. Unit: `tests/tools/test_tool_output_secret_masking.py`. Example: none. Real-LLM: none.
- `S13.mask-models`: `mask_secrets_in_model` walks nested models, lists, sets, dicts and namedtuples, leaves non-strings, `SecretStr` and enum members alone, and keeps base64 image data (data URLs, browser screenshots) intact while masking regular URLs. Unit: `tests/sdk/conversation/test_secret_registry_model_masking.py`, `tests/cross/test_secret_masking_tool_payloads.py`. Example: none. Real-LLM: none.
- `S13.mask-async`: in `arun()`, agent messages and tool thoughts are masked the same as in sync, including `LookupSecret`s resolved over loopback and secrets registered during a lookup, without blocking the loop. Unit: `tests/sdk/agent/test_async_secret_masking.py`. Example: none. Real-LLM: none.

## How to get to it (agent POV)

- `conversation.set_confirmation_policy(AlwaysConfirm() | NeverConfirm() | ConfirmRisky(threshold=SecurityRisk.MEDIUM, confirm_unknown=False))`, `conversation.set_security_analyzer(analyzer | None)`; then poll `conversation.state.execution_status`, `ConversationState.get_unmatched_actions(conversation.state.events)`, `conversation.reject_pending_actions(reason)`, `conversation.confirmation_policy_active` / `is_confirmation_mode_active`. Covers `S13.policies`, `S13.confirm-*`, `S13.analysis-event`.
- `openhands.sdk.security`: `LLMSecurityAnalyzer`, `PatternSecurityAnalyzer`, `PolicyRailSecurityAnalyzer`, `EnsembleSecurityAnalyzer(analyzers=[...], propagate_unknown=False)`, `ToolShieldLLMSecurityAnalyzer(llm=...)`, `GraySwanAnalyzer(api_key=..., policy_id=...)`, `SecurityRisk`, `SecurityAnalyzerBase` (subclass with `security_risk(action)` or `analyze_action(action) -> SecurityAnalysis`).
- `Agent(security_policy_filename="/abs/path.md" | None)`; `agent.static_system_message` shows the result (`S13.security-policy-prompt`).
- `ConversationSettings(confirmation_mode=..., security_analyzer="llm")` (`S13.settings-security`).
- Secrets: `Conversation(agent, secrets={"NAME": "value" | SecretSource})`, `conversation.update_secrets({...})`, `AgentContext(secrets=...)`; `openhands.sdk.secret`: `StaticSecret(value=...)`, `LookupSecret(url=..., headers=...)`, `SecretSource` (subclass `get_value`), `register_local_secret_resolver` / `unregister_local_secret_resolver`. Covers `S13.secret-*`, `S13.mask-*`.
- Env vars: `GRAYSWAN_API_KEY`, `GRAYSWAN_POLICY_ID`; example 04 reads `ADD_SECURITY_ANALYZER` (any non-empty value adds `LLMSecurityAnalyzer`).

## Driving it

Preconditions:
- `uv sync --dev` has run.
- For examples: `LLM_API_KEY` and `LLM_MODEL` (optionally `LLM_BASE_URL`) exported; examples 04 and 16 also need a terminal for `input()`.

- **Risk levels, policies, analyzers (`S13.risk-levels`, `S13.policies`, `S13.llm-analyzer`, `S13.pattern-analyzer`, `S13.policy-rails`, `S13.ensemble`, `S13.toolshield`, `S13.grayswan`).** Deterministic; the Gray Swan HTTP calls are mocked.
  ```sh
  uv run pytest tests/sdk/security -q
  ```
  476 passed, 7 skipped (toolshield extra not installed), 10 xfailed (documented parser bypasses).
- **Confirmation flow in a conversation (`S13.confirm-wait`, `S13.confirm-approve-reject`, `S13.risk-extraction`, `S13.analysis-event`, `S13.security-policy-prompt`).**
  ```sh
  uv run pytest tests/sdk/conversation/local/test_confirmation_mode.py tests/sdk/agent/test_extract_security_risk.py tests/sdk/agent/test_security_analysis_event.py tests/sdk/agent/test_security_policy_integration.py -q
  ```
  All tests pass with a mocked LLM.
- **Settings (`S13.settings-security`).**
  ```sh
  uv run pytest tests/sdk/test_settings.py -q -k conversation_settings_create_request
  ```
  4 tests pass.
- **Secrets and masking (`S13.secret-sources`, `S13.secret-registry`, `S13.secret-injection`, `S13.mask-output`, `S13.mask-tool-output`, `S13.mask-models`, `S13.mask-async`).**
  ```sh
  uv run pytest tests/sdk/conversation/test_secret_source.py tests/sdk/conversation/test_secrets_manager.py tests/sdk/conversation/test_secret_registry_model_masking.py tests/sdk/conversation/test_conversation_secrets_constructor.py tests/cross/test_agent_secrets_integration.py tests/cross/test_secret_masking_tool_payloads.py tests/tools/test_tool_output_secret_masking.py tests/sdk/agent/test_async_secret_masking.py -q
  ```
  All tests pass; `test_agent_secrets_integration.py` starts real terminal sessions and takes about 20 s.
- **Interactive confirmation with a real model (`S13.confirm-wait`, `S13.confirm-approve-reject`).**
  ```sh
  uv run python examples/01_standalone_sdk/04_confirmation_mode_example.py
  ADD_SECURITY_ANALYZER=1 uv run python examples/01_standalone_sdk/04_confirmation_mode_example.py
  ```
  Each action batch is listed and waits for `yes`/`no`; `no` rejects and the agent carries on.
- **LLM analyzer with ConfirmRisky (`S13.llm-analyzer`).**
  ```sh
  uv run python examples/01_standalone_sdk/16_llm_security_analyzer.py
  ```
  `ls` runs unprompted; the echo the prompt asks to mark HIGH stops for confirmation.
- **Custom security policy (`S13.security-policy-prompt`).**
  ```sh
  uv run python examples/01_standalone_sdk/32_configurable_security_policy.py
  ```
  Prints `✓ Custom security policy successfully embedded in system message.` and `EXAMPLE_COST`.
- **Defense-in-depth wiring (`S13.ensemble`, `S13.policies`).** Needs no LLM.
  ```sh
  uv run python examples/01_standalone_sdk/47_defense_in_depth_security.py
  ```
  Prints the analyzer and policy and `EXAMPLE_COST: 0`; it only constructs objects and never runs a conversation.
- **Secrets in the terminal (`S13.secret-injection`, `S13.mask-output`).**
  ```sh
  uv run python examples/01_standalone_sdk/12_custom_secrets.py
  ```
  The agent echoes `$SECRET_TOKEN` and `$SECRET_FUNCTION_TOKEN`; the observations show `<secret-hidden>`, never the values.

## Gotchas

- Examples 04 and 16 are in `_EXCLUDED_EXAMPLES` (they call `input()`); on EOF they reject by default, so piping no input rejects every action.
- Example 16 runs with `persistence_dir="./.conversations"` and `workspace="."`, leaving state in the current directory.
- Example 47 only builds the ensemble and policy; it proves construction, not detection. Detection is proven by the defense-in-depth unit tests.
- Choosing an analyzer does not change the confirmation policy: without `set_confirmation_policy`, the default `NeverConfirm` only records `SecurityAnalysisEvent`s.
- With an analyzer but no risk label from the model, risk is `UNKNOWN`, and `ConfirmRisky()` asks because `confirm_unknown=True` by default.
- Without any analyzer, `security_risk` from the model is discarded and every action is `UNKNOWN`.
- 10 tests in `tests/sdk/security/defense_in_depth/` are strict `xfail`s for known bypasses (command substitution, ANSI-C quoting, homoglyphs, combining characters, payloads past the hard cap, thinking-block payloads); `test_shell_parser_bypasses.py` cites issue #2721. A strict xfail that starts passing fails the run.
- 7 ToolShield tests skip unless the optional `toolshield` extra is installed; this map does not install it.
- Masking only covers values the registry has resolved (tracked); a `LookupSecret` that was never fetched has nothing to mask yet.
- Example 12 overlaps the conversation family; it is listed here for the secret sources and masking it shows.
