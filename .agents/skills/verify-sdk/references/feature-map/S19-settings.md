# Agent settings, persisted schema migrations and agent profiles

An SDK user can describe an agent as data instead of code. `OpenHandsAgentSettings(llm=LLM(...), tools=[...], condenser=LLMSummarizingCondenserSettings(...), verification=VerificationSettings(...), mcp_config={...}, persona=..., agent_context=..., tool_concurrency_limit=...)` serializes to JSON, validates back, and `create_agent()` builds the `Agent` (tools defaulting to the standard set when left unset, a condenser only when enabled, a critic only when enabled and keyed). `ACPAgentSettings` does the same for an ACP-backed agent, resolving the server command from a provider registry. `validate_agent_settings(payload)` picks the variant from `agent_kind` and runs the migration chain on any persisted payload from `schema_version` 0 up to the current 8 (`ConversationSettings` has its own chain, currently 1), rejecting payloads newer than the code; `apply_agent_settings_diff(base, diff)` applies a JSON merge patch, switching variant when `agent_kind` changes; `export_agent_settings_schema()` emits the sectioned schema a settings UI renders. Golden payloads for every past schema version live in `tests/sdk/persisted_settings_baselines/vN/`, and a CI script proves the current code still loads them and the last PyPI release's payloads. On top of settings, an agent profile (`OpenHandsAgentProfile` / `ACPAgentProfile`, schema version 3) is a named, reference-bearing launch spec saved by `AgentProfileStore` under `~/.openhands/agent-profiles/<name>.json`; `resolve_agent_profile(...)` turns it into validated settings by loading the referenced LLM profile, filtering MCP servers and skills. `openhands.sdk.credential` provides `HttpVersionedCredentialBinding`, a versioned load/replace client for file credentials that ACP agents sync with a credential source.

Source: `openhands-sdk/openhands/sdk/settings/`, `openhands-sdk/openhands/sdk/profiles/`, `openhands-sdk/openhands/sdk/credential.py`, `.github/scripts/check_persisted_settings_compat.py`, `tests/sdk/persisted_settings_baselines/`

Needs: `llm`, `tmux`, `network`

Examples: `examples/01_standalone_sdk/46_agent_settings.py`

## Sub-features

- `S19.settings-create-agent`: `OpenHandsAgentSettings(...).create_agent()` returns an `Agent` with the settings' LLM, tools, MCP config and agent context. Unit: `tests/sdk/test_settings.py::test_llm_create_agent_uses_settings_llm_and_tools`. Example: `examples/01_standalone_sdk/46_agent_settings.py`. Real-LLM: none.
- `S19.settings-roundtrip`: settings dump to JSON and `model_validate` restores them, preserving the LLM model, condenser fields, disabled MCP servers and secrets held by a validated instance. Unit: `tests/sdk/test_settings.py::test_llm_roundtrip_preserves_llm_model`, `::test_disabled_mcp_server_survives_settings_round_trip`. Example: `examples/01_standalone_sdk/46_agent_settings.py`. Real-LLM: none.
- `S19.settings-tools`: `tools=None` gives the standard tool set, `tools=[]` gives a bare agent, duplicates collapse, built-ins are matched by class name and attached once, and a registered tool named like a built-in is not replaced. Unit: `tests/sdk/test_settings.py::test_create_agent_defaults_tools_when_none`, `::test_create_agent_empty_tools_stays_bare`, `::test_create_agent_collapses_duplicate_tools`, `::test_builtin_named_twice_is_attached_once`. Example: `examples/01_standalone_sdk/46_agent_settings.py` (terminal-only variant). Real-LLM: none.
- `S19.retired-switches`: the retired booleans `enable_sub_agents` and `enable_switch_llm_tool` (`RETIRED_TOOL_SWITCHES` in `openhands-sdk/openhands/sdk/tool/defaults.py`) fold into the `tools` list on load and in diffs, pin the same set the v6 migration pins (with the browser pinned only for loaded settings), and are never serialized again. Unit: `tests/sdk/test_settings.py::test_retired_tool_switches_are_not_serialized`, `::test_v6_settings_fold_the_retired_switches`, `::test_live_retired_switch_pins_the_same_set_as_the_v6_migration`. Example: none. Real-LLM: none.
- `S19.condenser-settings`: `LLMSummarizingCondenserSettings(enabled=True, max_size=...)` builds an `LLMSummarizingCondenser` whose fields match the condenser's, inheriting `max_tokens` from the LLM unless set; `enabled=False` gives no condenser; `NoOpCondenserSettings` builds a `NoOpCondenser`; a legacy condenser payload defaults to the summarizing variant. Unit: `tests/sdk/test_settings.py::test_llm_create_agent_builds_condenser_when_enabled`, `::test_llm_summarizing_condenser_settings_match_condenser_fields`, `::test_llm_create_agent_builds_no_op_condenser_variant`, `::test_llm_create_agent_no_condenser_when_disabled`. Example: `examples/01_standalone_sdk/46_agent_settings.py`. Real-LLM: none.
- `S19.verification-settings`: `VerificationSettings(critic_enabled=True, ...)` builds a critic (with iterative refinement when configured) only when a critic API key or the LLM key is available; the key round-trips. Unit: `tests/sdk/test_settings.py::test_llm_create_agent_builds_critic_when_enabled`, `::test_llm_create_agent_no_critic_without_api_key`, `::test_llm_create_agent_critic_with_iterative_refinement`. Example: none. Real-LLM: none.
- `S19.mcp-config-secrets`: `mcp_config` is a typed server map; env, headers and bearer auth are redacted in dumps, encrypted with a cipher when one is supplied, legacy plaintext decrypts, and `create_agent()` gets the real values. Unit: `tests/sdk/test_settings.py::test_openhands_agent_settings_mcp_config_redacts_env_and_headers`, `::test_mcp_config_encrypts_env_and_headers_with_cipher`, `::test_openhands_agent_settings_create_agent_keeps_real_mcp_secrets`. Example: none. Real-LLM: none.
- `S19.tool-concurrency-persona`: `tool_concurrency_limit` defaults to 1 and rejects invalid values; `persona` is applied to the built agent's prompt, and without it the built-in prompt is used. Unit: `tests/sdk/test_settings.py::test_tool_concurrency_limit_invalid_values_rejected`, `::test_create_agent_applies_persona`. Example: none. Real-LLM: none.
- `S19.subscription-llm-settings`: subscription-auth LLM fields round-trip through settings and are rehydrated into a working runtime LLM on load. Unit: `tests/sdk/test_settings.py::test_llm_subscription_fields_roundtrip`, `::test_llm_from_persisted_rehydrates_subscription_runtime`. Example: none. Real-LLM: none.
- `S19.acp-settings`: `ACPAgentSettings(acp_server=...)` resolves the default command for known servers (rewriting `npx` to a pinned binary when present), requires an explicit command for a custom server, ignores and warns about an `llm`, and maps the provider's API-key env var. Unit: `tests/sdk/test_settings.py::test_acp_create_agent_uses_server_default_command`, `::test_acp_custom_server_requires_explicit_command`, `::test_acp_settings_llm_warns_and_is_ignored`. Example: none. Real-LLM: none.
- `S19.acp-providers-catalog`: the ACP provider registry (`ACP_PROVIDERS`, detection by agent name or command, file-secret specs) and the install catalog of pinned npm packages with a rendered Docker install plan. Unit: `tests/sdk/settings/test_acp_providers.py`, `tests/sdk/settings/test_acp_install_catalog.py`. Example: none. Real-LLM: none.
- `S19.validate-dispatch`: `validate_agent_settings` dispatches on `agent_kind` (`openhands` or `acp`), defaults to `openhands` when it is missing, and canonicalizes the legacy `llm` kind so it never returns `LLMAgentSettings`. Unit: `tests/sdk/test_settings.py::test_validate_agent_settings_dispatches_on_agent_kind`, `::test_validate_agent_settings_defaults_to_openhands_when_discriminator_missing`, `tests/sdk/test_apply_agent_settings_diff.py::test_validate_never_returns_llm_subclass`. Example: none. Real-LLM: none.
- `S19.schema-migrations`: persisted agent settings from v0 to v7 migrate step by step to v8 (legacy proxy LLM, `modify_params`, MCP auth shapes and `type` to `transport`, ACP LLM removal, retired switches); a newer, negative or non-integer `schema_version` is rejected; `from_persisted` and `model_validate` agree on current payloads. Unit: `tests/sdk/test_settings.py::test_validate_agent_settings_migrates_v0_llm_payload`, `::test_validate_agent_settings_rejects_newer_schema_version`, `::test_openhands_agent_settings_from_persisted_migrates_legacy_payloads`. Example: none. Real-LLM: none.
- `S19.conversation-settings`: `ConversationSettings` (schema v1) round-trips, migrates a v0 payload, rejects newer versions, validates observability metadata, accepts both agent variants, and `create_request(...)` builds a start-conversation request with confirmation policy and security analyzer. Unit: `tests/sdk/test_settings.py::test_conversation_settings_model_dump_roundtrip`, `::test_conversation_settings_from_persisted_migrates_v0_payload`, `::test_conversation_settings_create_request`. Example: none. Real-LLM: none.
- `S19.apply-diff`: `apply_agent_settings_diff(base, diff)` deep-merges within a variant, treats `None` as unset (merge patch), replaces the base with a fresh variant when `agent_kind` switches (dropping `persona` for ACP), and keeps secrets from the base. Unit: `tests/sdk/test_apply_agent_settings_diff.py`. Example: none. Real-LLM: none.
- `S19.schema-export`: `export_agent_settings_schema()` and `export_settings_schema(Model)` emit variant-tagged sections with field metadata (label, prominence), stay backward compatible, and work on both variants. Unit: `tests/sdk/test_settings.py::test_export_agent_settings_schema_emits_variant_tagged_sections`, `::test_export_settings_schema_remains_backward_compatible`, `::test_llm_agent_settings_export_schema_groups_sections`. Example: none. Real-LLM: none.
- `S19.persisted-baselines`: every `tests/sdk/persisted_settings_baselines/vN/*.json` (agent settings, agent profiles, conversation settings, agent-server persisted settings) loads with the current code and keeps its sentinel values; a shape change without a version bump, or a removed profile field, is rejected; every schema version must have a fixture. Unit: `tests/cross/test_check_persisted_settings_compat.py`. Example: none. Real-LLM: none.
- `S19.pypi-baseline-gate`: the CI script generates payloads with the previous PyPI release of `openhands-sdk` and `openhands-agent-server` (via `uv`, with a release-date cutoff) and validates them against the current code. Unit: `tests/cross/test_check_persisted_settings_compat.py::test_generate_baseline_payloads_uses_uv_with_release_cutoff`, `::test_get_pypi_baseline_version_prefers_current_or_previous` (mocked). Example: none. Real-LLM: none.
- `S19.profile-model`: `OpenHandsAgentProfile` requires `llm_profile_ref`, `ACPAgentProfile` requires a known ACP server and rejects LLM refs and persona; both carry a UUID `id`, `name`, `revision`, `mcp_server_refs` (null means all, `[]` means none), `secret_refs`, and never persist secrets. Unit: `tests/sdk/profiles/test_agent_profile.py`, `tests/sdk/profiles/test_secret_refs.py`. Example: none. Real-LLM: none.
- `S19.profile-migrations`: profiles at schema v1 and v2 migrate to v3 (empty or default tools, embedded skills to `disabled_skills`, v2 switches to tools); newer, negative or non-integer versions are rejected. Unit: `tests/sdk/profiles/test_agent_profile.py::test_v1_untouched_default_migrates_empty_tools_to_null`, `::test_rejects_newer_schema_version`. Example: none. Real-LLM: none.
- `S19.profile-store`: `AgentProfileStore(base_dir=None)` saves atomically with the schema version and id, lists, loads (showing available names on a miss), renames (keeping the id), deletes, lists summaries skipping corrupted files, enforces `max_profiles`, and is safe under concurrent access through a file lock. Unit: `tests/sdk/profiles/test_agent_profile_store.py`. Example: none. Real-LLM: none.
- `S19.profile-resolve`: `resolve_agent_profile(profile, llm_store=..., mcp_config=..., available_skills=..., browser_available=...)` builds validated settings: loads the LLM profile (raising `ProfileNotFound`), filters MCP servers (raising `DanglingMcpServerRef`), applies `disabled_skills`, scopes tools and delegation, and keeps persona and verification; `resolve_agent_profile_dry_run` reports the same verdict with secrets redacted. Unit: `tests/sdk/profiles/test_resolver.py`. Example: none. Real-LLM: none.
- `S19.profile-refs`: renaming an LLM profile cascades to every agent profile that cites it, atomically; deleting a referenced LLM profile raises `ProfileReferenced` naming the referrers. Unit: `tests/sdk/profiles/test_profile_refs.py`, `tests/sdk/profiles/test_store_protocol_hoists.py`. Example: none. Real-LLM: none.
- `S19.profile-seed`: `build_seed_profile(settings)` derives the default profile from current settings (persona, explicit tools, ACP branch, no disabled skills); `save_profile_preserving_identity` keeps the id and bumps `revision`. Unit: `tests/sdk/profiles/test_store_protocol_hoists.py`. Example: none. Real-LLM: none.
- `S19.credential-binding`: `HttpVersionedCredentialBinding(url, headers).load()` GETs `{value, version}`, `replace(expected_version, value)` PUTs and returns the new version; 404 and 400/422 raise `CredentialNeedsReauthentication`, 409 `CredentialConflict`, 401/403 `CredentialAuthorizationRejected`, 501 `CredentialBindingUnsupported`, invalid URLs `CredentialInvalidResponse`; `reauthorize()` swaps headers for the same URL. Unit: `tests/sdk/test_credential.py`. Example: none. Real-LLM: none.

## How to get to it (agent POV)

- `from openhands.sdk import OpenHandsAgentSettings`; `from openhands.sdk.settings import LLMSummarizingCondenserSettings, NoOpCondenserSettings, VerificationSettings, ACPAgentSettings, ConversationSettings, validate_agent_settings, apply_agent_settings_diff, default_agent_settings, create_agent_from_settings, export_agent_settings_schema, export_settings_schema`: `S19.settings-*`, `S19.condenser-settings`, `S19.verification-settings`, `S19.acp-settings`, `S19.validate-dispatch`, `S19.apply-diff`, `S19.schema-export`, `S19.conversation-settings`.
- `settings.create_agent()`, `settings.model_dump(mode="json")`, `OpenHandsAgentSettings.model_validate(payload)`, `OpenHandsAgentSettings.from_persisted(payload)`, `ConversationSettings.from_persisted(payload)`: `S19.settings-roundtrip`, `S19.schema-migrations`.
- Constants: `AGENT_SETTINGS_SCHEMA_VERSION = 8`, `CONVERSATION_SETTINGS_SCHEMA_VERSION = 1` (`settings/model.py`), `AGENT_PROFILE_SCHEMA_VERSION = 3` (`profiles/agent_profile.py`).
- Files: `tests/sdk/persisted_settings_baselines/v1..v8/*.json`, `.github/scripts/check_persisted_settings_compat.py`, workflow `.github/workflows/persisted-settings-compat.yml`: `S19.persisted-baselines`, `S19.pypi-baseline-gate`.
- `from openhands.sdk.profiles import AgentProfileStore, OpenHandsAgentProfile, ACPAgentProfile, validate_agent_profile, resolve_agent_profile, resolve_agent_profile_dry_run, cascade_rename, delete_llm_profile, rename_llm_profile, build_seed_profile, save_profile_preserving_identity`; on disk `~/.openhands/agent-profiles/<name>.json` (moved by `OH_PERSISTENCE_DIR`): `S19.profile-*`. LLM profiles themselves (the `llm_profile_ref` targets) belong to the LLM profile store family (example 37).
- `from openhands.sdk.credential import HttpVersionedCredentialBinding, ResolvedCredential, Credential*`: `S19.credential-binding`; consumed by the ACP agent's file-credential sync.
- Env read by example 46: `LLM_API_KEY`, `LLM_MODEL` (default `gpt-5.5`), `LLM_BASE_URL`.

## Driving it

Preconditions:
- `uv sync --dev` has run.
- For example 46: `LLM_API_KEY` and `LLM_MODEL` exported; `tmux` on `PATH` (it builds terminal and file-editor tools and runs a conversation).
- For the full persisted-settings gate: outbound network to pypi.org and the package index.

- **Settings build, round trip, tools, condenser, critic, MCP (`S19.settings-*`, `S19.retired-switches`, `S19.condenser-settings`, `S19.verification-settings`, `S19.mcp-config-secrets`, `S19.tool-concurrency-persona`, `S19.subscription-llm-settings`, `S19.acp-settings`, `S19.validate-dispatch`, `S19.schema-migrations`, `S19.conversation-settings`, `S19.schema-export`).**
  ```sh
  uv run pytest tests/sdk/test_settings.py -q
  uv run python examples/01_standalone_sdk/46_agent_settings.py
  ```
  158 tests pass; the example prints the settings JSON, asserts the restored condenser, runs one conversation, then builds a terminal-only agent with `condenser is None`.
- **Diff application (`S19.apply-diff`).**
  ```sh
  uv run pytest tests/sdk/test_apply_agent_settings_diff.py -q
  ```
- **ACP provider registry and install catalog (`S19.acp-providers-catalog`).**
  ```sh
  uv run pytest tests/sdk/settings -q
  uv run pytest tests/sdk/settings/test_acp_install_catalog_pins_live.py -m acp_live -q
  ```
  The first command passes with the live pins deselected; the second is **blocked** without network (it runs `npx` against the npm registry).
- **Persisted baselines and the PyPI gate (`S19.persisted-baselines`, `S19.pypi-baseline-gate`).**
  ```sh
  uv run pytest tests/cross/test_check_persisted_settings_compat.py -q
  uv run python .github/scripts/check_persisted_settings_compat.py
  ```
  The tests pass offline; the script prints a `::notice` per migrated fixture, `Validated 23 persisted settings fixture(s) under tests/sdk/persisted_settings_baselines` and then, with network, `Validated 8 baseline payload(s) from PyPI release openhands-sdk==1.54.0, openhands-agent-server==1.54.0` (counts and versions at 4cc0582; the second half is **blocked** offline).
- **Agent profiles (`S19.profile-*`).**
  ```sh
  uv run pytest tests/sdk/profiles -q
  ```
  All pass; the store tests use `tmp_path`, not `~/.openhands`.
- **Credential binding (`S19.credential-binding`).**
  ```sh
  uv run pytest tests/sdk/test_credential.py -q
  ```
  Uses an `httpx.MockTransport`; no network needed.

## Gotchas

- `pyproject.toml` `addopts` deselects `stress`, `acp_live` and `docker_live` tests; `uv run pytest tests/sdk/settings -q` reports `86 passed, 13 deselected`, which is expected, not a failure.
- A persisted shape change needs three things together (see `AGENTS.md`): bump the schema version constant, add the migration step, and add `tests/sdk/persisted_settings_baselines/vN/` fixtures for the old shape. `test_validate_fixture_cases_requires_every_schema_version` fails if a version has no fixture.
- `check_persisted_settings_compat.py` fetches `https://pypi.org/pypi/openhands-sdk/json` and runs `uv` with `--exclude-newer`; without network it fails in the PyPI half even though the fixture half passed. If no published baseline exists it prints a `::warning` and exits 0.
- `LLMAgentSettings` is a deprecated alias kept importable; `validate_agent_settings` never returns it. Code that checks `type(settings) is LLMAgentSettings` breaks.
- MCP secrets are redacted in `model_dump()` unless a cipher or an expose context is given; a dumped-then-reloaded settings object without a cipher has lost the real values (`test_openhands_agent_settings_mcp_config_expose_encrypted_requires_cipher`).
- `_DEFAULT_PROFILE_DIR` is computed at import time from `OH_PERSISTENCE_DIR`; set it before importing `openhands.sdk`, or pass `AgentProfileStore(base_dir=...)`.
- `ACPProviderInfo.available_models` is deprecated (removal in 1.59.0); its tests emit `DeprecatedWarning`, which is expected.
- No failing tests were found in this family's commands at 4cc0582.
