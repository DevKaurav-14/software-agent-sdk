# Custom tools, client-defined tools and the tool registry

How an SDK program defines its own tools and how every tool reaches an agent. A custom tool is four Python classes: an `Action` (pydantic fields become the LLM-facing JSON schema), an `Observation` (its `to_llm_content` is what the model sees), a `ToolExecutor` (`__call__(action, conversation)`), and a `ToolDefinition` subclass whose `create(conv_state, **params)` returns one or more tool instances; a `create` that returns several tools sharing one executor is a tool set. `register_tool(name, ToolClass)` puts a resolver in a process-wide registry; the agent holds only `Tool(name=..., params=...)` specs and the conversation resolves them at start (`resolve_tool`), so specs serialize and unknown names fail. A tool's `name` defaults to its class name in snake_case without `_tool`. The registry also answers usability (`is_usable()`), builds a sealed tool catalog, and records each tool's module for remote re-import. The SDK turns a definition into OpenAI chat, Responses and MCP schemas and adds `security_risk` (for non-read-only tools) and `summary` fields. A client-defined tool needs no Python at all: `ClientToolSpec(name, description, parameters)` passed as `Conversation(..., client_tools=[...])` becomes a `ClientTool` whose executor returns an acknowledgment at once, so the program (or a frontend) handles the `ActionEvent` itself; specs are persisted and restored on resume, and a name that collides with a built-in or with a different schema is rejected.

Source: `openhands-sdk/openhands/sdk/tool/`, `openhands-sdk/openhands/sdk/agent/base.py`, `openhands-sdk/openhands/sdk/conversation/conversation.py`, `openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py`

Needs: `llm` (examples only)

Examples: `examples/01_standalone_sdk/02_custom_tools.py`, `examples/01_standalone_sdk/53_client_defined_tools.py`

## Sub-features

- `S17.custom-tool-definition`: a `ToolDefinition` built from an `Action`, an `Observation` and an executor validates actions, calls the executor, checks the returned observation type, and exposes `as_executable()`; calling a tool without an executor raises. Unit: `tests/sdk/tool/test_tool_definition.py`. Example: `examples/01_standalone_sdk/02_custom_tools.py` (`GrepTool`). Real-LLM: none.
- `S17.tool-set`: one registered name whose `create()` returns several tools sharing state (`BashAndGrepToolSet` returns a terminal and a grep tool on one `TerminalExecutor`); every returned tool is added to the agent. Unit: `tests/tools/browser_use/test_browser_toolset.py::test_browser_toolset_create_tools_have_shared_executor` (the built-in instance of the pattern). Example: `examples/01_standalone_sdk/02_custom_tools.py`. Real-LLM: none.
- `S17.register-tool`: `register_tool(name, factory)` accepts a `ToolDefinition` subclass (resolved through `create(**params)`) or a ready instance with an executor (params rejected, same object returned); a bare callable is rejected, an empty name raises `ValueError`, and a duplicate name logs a warning and replaces the old entry. Unit: `tests/sdk/tool/test_registry.py` (`test_register_tool_rejects_callable_factory`, `test_register_tool_instance_rejects_params`, `test_register_tool_instance_returns_same_object`, `test_register_tool_type_uses_create_params`, `test_tool_registration_typed_inspection`). Example: `examples/01_standalone_sdk/02_custom_tools.py`. Real-LLM: none.
- `S17.resolve-tool`: `resolve_tool(Tool(name=..., params=...), conv_state)` passes `params` to `create()` with the conversation state (working dir, persistence dir), falls back to built-ins under their snake_case names, applies a `response_schema` param to a single tool, and raises `KeyError` for an unregistered name. Unit: `tests/cross/test_registry_directories.py`, `tests/sdk/tool/test_registry.py::test_builtin_resolves_under_its_snake_case_name`, `tests/sdk/tool/test_response_schema.py::test_builtin_finish_tool_spec_resolves_without_registry_entry` (the unregistered-name `KeyError` has no test). Example: none. Real-LLM: none.
- `S17.auto-naming`: `ToolDefinition.name` is derived from the class name (`FileEditorTool` to `file_editor`) unless the class sets `name`. Unit: `tests/cross/test_automatic_naming.py`. Example: `examples/01_standalone_sdk/02_custom_tools.py` (`BashAndGrepToolSet.name`). Real-LLM: none.
- `S17.auto-registration`: importing a built-in tool module (or `openhands.tools`) registers its tools, after which specs resolve. Unit: `tests/cross/test_automatic_registration.py`, `tests/tools/test_init.py`. Example: none. Real-LLM: none.
- `S17.tool-spec`: `Tool(name, params)` is frozen, round-trips through JSON, and rejects an empty name. Unit: `tests/sdk/tool/test_tool.py`. Example: `examples/01_standalone_sdk/02_custom_tools.py`. Real-LLM: none.
- `S17.agent-tool-init`: the agent turns its specs into tools at conversation start, adds built-ins (`finish`, `think`) unless `include_default_tools` narrows or empties them, rejects duplicate tool names, and does not let a runtime tool replace an existing one; a custom tool may replace `finish`. Unit: `tests/sdk/agent/test_agent_tool_init.py`. Example: `examples/01_standalone_sdk/02_custom_tools.py`. Real-LLM: none.
- `S17.llm-schemas`: `to_openai_tool()`, `to_responses_tool()` (with `strict` and parameters) and `to_mcp_tool()` render the action schema without the internal `kind` field, keep required fields and annotations, and expand nested and circular `$ref`s without recursion errors. Unit: `tests/sdk/tool/test_mcp_schema.py`, `tests/sdk/tool/test_to_responses_tool.py`, `tests/sdk/tool/test_tool_definition.py` (`test_to_mcp_tool_*`, `test_mcp_tool_schema_required_fields`). Example: none. Real-LLM: none.
- `S17.injected-fields`: a `security_risk` parameter is added to tools that are not read-only (optional, ahead of content parameters, gated by the security setting) and a `summary` parameter is always added, while an MCP tool's own description is kept. Unit: `tests/sdk/tool/test_tool_definition.py` (`test_security_risk_only_added_for_non_readonly_tools`, `test_security_risk_is_optional_field_in_schema`, `test_security_risk_precedes_content_params_in_schema`), `tests/sdk/tool/test_to_responses_tool_security.py`, `tests/sdk/tool/test_to_responses_tool_summary.py`. Example: none. Real-LLM: none.
- `S17.schema-serialization`: `Action`/`Observation` subclasses are frozen and serialize as a discriminated union by `kind`, including nested polymorphic fields; tool definitions are immutable and `set_executor` returns a copy. Unit: `tests/sdk/tool/test_tool_serialization.py`, `tests/sdk/tool/test_schema_immutability.py`, `tests/sdk/tool/test_tool_immutability.py`. Example: none. Real-LLM: none.
- `S17.py-type`: `py_type()` maps JSON-schema types (string, integer, number, boolean, object, arrays, nullable unions) to Python types for dynamically built actions. Unit: `tests/sdk/tool/test_py_type.py`. Example: none. Real-LLM: none.
- `S17.output-coercion`: odd executor results (an observation with `None` content and other shapes) still become a valid tool result message. Unit: `tests/sdk/tool/test_tool_call_output_coercion.py`. Example: none. Real-LLM: none.
- `S17.annotations-and-resources`: `ToolAnnotations` (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) travel with the tool, and `declared_resources(action)` returns `DeclaredResources` keys that the parallel executor locks on. Unit: `tests/sdk/tool/test_tool_definition.py::test_tool_creation_with_annotations`, `tests/sdk/agent/test_parallel_executor_locking.py`. Example: `examples/01_standalone_sdk/45_parallel_tool_execution.py`. Real-LLM: none.
- `S17.usability`: a tool class's `is_usable()` decides `is_tool_usable(name)`, `is_tool_available(name)` and `list_usable_tools()`; a checker that raises counts as unusable. Unit: `tests/sdk/tool/test_registry.py::test_register_tool_type_respects_is_usable`, `tests/sdk/tool/test_defaults.py::test_is_tool_usable_contract`. Example: none. Real-LLM: none.
- `S17.catalog`: `list_tool_catalog(check_usable=...)` lists offered tools with `user_selectable`, `usable`, `description` and `in_default_set`, offers built-ins once under their snake_case names, hides the profile router, and after `seal_tool_catalog()` ignores later registrations until `unseal_tool_catalog()`. Unit: `tests/sdk/tool/test_registry.py` (`test_catalog_*`, `test_sealed_catalog_*`, `test_unsealed_catalog_tracks_registrations_again`). Example: none. Real-LLM: none.
- `S17.module-qualnames`: `get_tool_module_qualnames()` maps each registered tool name to the module that defined it (a copy), which a remote conversation forwards so the server imports the same modules. Unit: `tests/cross/test_registry_qualnames.py`. Example: `examples/02_remote_agent_server/06_custom_tool/main.py` (server side). Real-LLM: none.
- `S17.client-tool-spec`: `ClientToolSpec(name, description, parameters, annotations)` round-trips through JSON and requires an object `parameters` schema. Unit: `tests/sdk/tool/test_client_tool.py` (`test_spec_*`). Example: `examples/01_standalone_sdk/53_client_defined_tools.py`. Real-LLM: none.
- `S17.client-tool-ack`: a `ClientTool` built from a spec gets a dynamic `ClientAction_<name>` action type, its executor returns a `ClientToolObservation` acknowledgment without doing anything, and its `ActionEvent` round-trips through JSON (including an argument named `kind`). Unit: `tests/sdk/tool/test_client_tool.py` (`test_executor_returns_acknowledgment`, `test_from_spec_*`, `test_client_tool_callable`, `test_client_tool_kind_argument_*`, `test_create_*`). Example: `examples/01_standalone_sdk/53_client_defined_tools.py`. Real-LLM: none.
- `S17.client-tool-schema`: the OpenAI schema keeps the client's constraints (enums, required), `security_risk` is injected when annotations are unset, and the MCP view uses the original schema. Unit: `tests/sdk/tool/test_client_tool.py` (`test_to_openai_tool`, `test_openai_schema_preserves_client_constraints`, `test_security_risk_injected_when_annotations_unset`, `test_mcp_tool_uses_original_schema`). Example: none. Real-LLM: none.
- `S17.client-tool-registration`: `register_client_tools(specs)` returns `Tool` specs carrying the schema in `params`, reuses the action type for an identical spec, raises `ClientToolSchemaConflictError` for the same name with a different schema, and `ClientToolRegistrationError` for duplicate names in one call or a built-in tool name. Unit: `tests/sdk/tool/test_client_tool.py` (`test_same_spec_reuses_action_type`, `test_same_name_different_schema_conflicts`, `test_register_client_tools_*`), `tests/cross/test_client_tool_registration.py`. Example: none. Real-LLM: none.
- `S17.client-tools-conversation`: `Conversation(..., client_tools=SPECS)` registers the specs and injects them into the agent; a persisted conversation resumes with its client tools without passing them again; a client tool named like a built-in the agent does not attach still resumes, one named like an attached built-in is rejected. Unit: `tests/sdk/conversation/local/test_client_tools_persistence.py`. Example: `examples/01_standalone_sdk/53_client_defined_tools.py`. Real-LLM: none.
- `S17.execute-tool`: `conversation.execute_tool(name, action)` runs a resolved tool outside the agent loop and returns its observation. Unit: `tests/sdk/tool/test_switch_llm.py`, `tests/tools/ask_oracle/test_ask_oracle.py`. Example: `examples/01_standalone_sdk/38_browser_session_recording.py`. Real-LLM: none.

## How to get to it (agent POV)

- Imports: `from openhands.sdk import Action, Observation, ToolDefinition, TextContent, ImageContent`; `from openhands.sdk.tool import Tool, ToolExecutor, ToolAnnotations, DeclaredResources, register_tool, resolve_tool, list_registered_tools, list_tool_catalog, is_tool_usable, ClientToolSpec, register_client_tools`.
- Define and register: subclass, then `register_tool(MyTool.name, MyTool)` at import time; reference it as `Agent(tools=[Tool(name=MyTool.name, params={...})])`. `params` keys are `create()` keyword arguments. `S17.custom-tool-definition`, `S17.tool-set`, `S17.register-tool`, `S17.resolve-tool`, `S17.auto-naming`, `S17.tool-spec`.
- Built-in tool control: `Agent(include_default_tools=[...])` (names of `BUILT_IN_TOOLS` classes, empty list for none). `S17.agent-tool-init`.
- Client tools: `Conversation(agent=..., workspace=..., client_tools=[ClientToolSpec(...)], callbacks=[on_event])`; in the callback, an `ActionEvent` with `event.tool_name` in your names is your cue to act. `S17.client-*`.
- Direct execution: `conversation.execute_tool("tool_name", SomeAction(...))`. `S17.execute-tool`.
- Catalog and usability: `list_tool_catalog()`, `seal_tool_catalog()` / `unseal_tool_catalog()` (in `openhands.sdk.tool.registry`), `ToolDefinition.is_usable()` classmethod. `S17.catalog`, `S17.usability`.
- Remote counterpart (owned by the agent server map): `examples/02_remote_agent_server/06_custom_tool/` (custom tool image, `tool_module_qualnames`) and `examples/02_remote_agent_server/14_client_defined_tools.py` (`client_tools` over REST).

## Driving it

Preconditions:

- `uv sync --dev` has run.
- For example bullets: `LLM_API_KEY` exported (optionally `LLM_MODEL`, `LLM_BASE_URL`).

- **Definitions, schemas, serialization, registry, catalog (`S17.custom-tool-definition`, `S17.register-tool`, `S17.resolve-tool`, `S17.tool-spec`, `S17.llm-schemas`, `S17.injected-fields`, `S17.schema-serialization`, `S17.py-type`, `S17.output-coercion`, `S17.usability`, `S17.catalog`, `S17.client-tool-spec`, `S17.client-tool-ack`, `S17.client-tool-schema`, `S17.client-tool-registration`).**
  ```sh
  uv run pytest tests/sdk/tool -q
  ```
  276 pass (this directory also holds built-in tool tests such as `switch_llm` and `invoke_skill`, owned by other families).
- **Cross-package registration, naming, qualnames (`S17.auto-naming`, `S17.auto-registration`, `S17.module-qualnames`, `S17.client-tool-registration`, `S17.resolve-tool`).**
  ```sh
  uv run pytest tests/cross/test_client_tool_registration.py tests/cross/test_registry_qualnames.py tests/cross/test_registry_directories.py tests/cross/test_automatic_naming.py tests/cross/test_automatic_registration.py tests/tools/test_init.py -q
  ```
  21 pass.
- **Agent tool init, client tools in a conversation, parallel resources (`S17.agent-tool-init`, `S17.client-tools-conversation`, `S17.annotations-and-resources`, `S17.tool-set`).**
  ```sh
  uv run pytest tests/sdk/agent/test_agent_tool_init.py tests/sdk/conversation/local/test_client_tools_persistence.py tests/sdk/agent/test_parallel_executor_locking.py "tests/tools/browser_use/test_browser_toolset.py::test_browser_toolset_create_tools_have_shared_executor" -q
  ```
  17 pass.
- **Direct tool execution (`S17.execute-tool`).**
  ```sh
  uv run pytest tests/sdk/tool/test_switch_llm.py tests/tools/ask_oracle/test_ask_oracle.py -q
  ```
  All tests pass.
- **Unregistered tool name (`S17.resolve-tool`), no test.**
  ```sh
  uv run python -c "
  from openhands.sdk.tool import Tool, resolve_tool
  try: resolve_tool(Tool(name='no_such_tool'), None)
  except KeyError as e: print('KeyError', e)
  "
  ```
  Prints `KeyError "ToolDefinition 'no_such_tool' is not registered"`.
- **Custom tools with a real model (`S17.custom-tool-definition`, `S17.tool-set`).**
  ```sh
  uv run python examples/01_standalone_sdk/02_custom_tools.py
  ```
  The agent calls the custom `grep` tool on `*.py` files, writes a summary file, then deletes it.
- **Client tools with a real model (`S17.client-tools-conversation`, `S17.client-tool-ack`).**
  ```sh
  uv run python examples/01_standalone_sdk/53_client_defined_tools.py
  ```
  It prints `[CLIENT HANDLER] show_notification(...)` and `navigate_to(...)` lines and asserts both were called.

## Gotchas

- The registry is process-global: a test or script that registers a name changes it for every later conversation in the process, and a duplicate registration only warns (a TODO in `register_tool` says it should raise).
- Registration happens on import. A spec whose module was never imported fails at conversation start with `KeyError ... is not registered`, not at `Agent(...)` construction.
- `Tool.params` must be JSON-serializable for persisted or remote conversations; live objects (executors, clients) belong inside `create()`, as example 02 does with `TerminalExecutor`.
- Example 02's `GrepTool` gets the class-derived name `grep`, the same as the built-in grep tool; adding `Tool(name="grep")` next to `BashAndGrepToolSet` would trip the agent's duplicate-name check.
- Client tool executors only acknowledge. The SDK does not wait for the client's result; the model sees the acknowledgment text. Handle results through a follow-up message.
- A client tool whose name matches a built-in the agent attaches (for example `finish`) is rejected at conversation creation (`ClientToolRegistrationError`).
