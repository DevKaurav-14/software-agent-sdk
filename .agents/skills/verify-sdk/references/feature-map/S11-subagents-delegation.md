# Sub-agents and delegation

A Python program gives its main `Agent` the task tool (`Tool(name=TaskToolSet.name)`) and registers sub-agent types; the model then calls `task` with a prompt and a `subagent_type`, and the SDK runs a separate, blocking `LocalConversation` for that sub-agent in the same workspace and returns its final answer as a `TaskObservation`. Sub-agent types come from four sources, first registration wins by name: programmatic `register_agent(...)`, plugin agents, Markdown files under `.agents/agents/` or `.openhands/agents/` (project, then user home), and the built-in Markdown agents shipped in `openhands-tools` (`general-purpose`, `code-explorer`, `bash-runner`, `web-researcher`) that `register_builtins_agents()` adds. A task can be resumed by its `task_xxxxxxxx` id, its metrics roll up into the parent's `conversation_stats`, its iteration and budget limits and confirmation policy come from the definition or the parent, and a `SubAgentScope` can forbid sub-agents from using tools or MCP servers the parent lacks.

Source: `openhands-sdk/openhands/sdk/subagent/`, `openhands-tools/openhands/tools/task/`, `openhands-tools/openhands/tools/delegate/`, `openhands-tools/openhands/tools/preset/default.py`, `openhands-tools/openhands/tools/preset/subagents/`, `openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py`

Needs: `llm`

Examples: `examples/01_standalone_sdk/25_agent_delegation.py`, `examples/01_standalone_sdk/41_task_tool_set.py`, `examples/01_standalone_sdk/42_file_based_subagents.py`

## Sub-features

- `S11.register-programmatic`: `register_agent(name, factory_func, description)` adds a type that `get_agent_factory(name)` returns; a duplicate name raises, and an unknown name raises `ValueError("Unknown agent ...")`. Unit: `tests/sdk/subagent/test_subagent_registry.py::test_register_and_retrieve_custom_agent_factory`, `::test_unknown_agent_type_raises_value_error`. Example: `examples/01_standalone_sdk/25_agent_delegation.py`. Real-LLM: none.
- `S11.register-if-absent`: `register_agent_if_absent` keeps an existing registration and returns False, so plugin, file and built-in sources never overwrite programmatic ones. Unit: `tests/sdk/subagent/test_subagent_registry.py::test_register_agent_if_absent_existing`, `::test_register_file_agents_skips_programmatic`. Example: none. Real-LLM: none.
- `S11.markdown-schema`: `AgentDefinition.load` parses YAML frontmatter (`name`, `description`, `tools`, `skills`, `model`, `color`, `max_iteration_per_run`, `max_budget_per_run`, `hooks`, `profile_store_dir`, `mcp_config`, `permission_mode`, `condenser`); the body becomes the system prompt, `<example>` tags become `when_to_use_examples`, unknown keys land in `metadata`, invalid values raise. Unit: `tests/sdk/subagent/test_subagent_schema.py`. Example: none. Real-LLM: none.
- `S11.file-discovery`: `load_project_agents` / `load_user_agents` scan only top-level `*.md` in `.agents/agents/` then `.openhands/agents/`, skip `README.md`, and `.agents` wins over `.openhands` for one name; `discover_agents` reports level and source without touching the registry. Unit: `tests/sdk/subagent/test_subagent_loader.py`, `tests/sdk/subagent/test_discover_agents.py`. Example: none. Real-LLM: none.
- `S11.file-precedence`: `register_file_agents(work_dir)` registers project agents before user agents, so project wins by name. Unit: `tests/sdk/subagent/test_subagent_registry.py::test_register_file_agents_project_priority`. Example: none. Real-LLM: none.
- `S11.conversation-autoregister`: the first `send_message()`/`run()` of a `LocalConversation` calls `register_file_agents(workspace.working_dir)`, so Markdown agents in the workspace become task types without any explicit call. Unit: **none (untested)** (only `register_file_agents` itself and plugin agents, `tests/sdk/conversation/test_local_conversation_agent_plugins.py::TestClientExtension::test_agents_are_registered`, are tested). Example: none. Real-LLM: none.
- `S11.plugin-agents`: `register_plugin_agents` registers `Plugin.agents` with their hooks, skipping existing names. Unit: `tests/sdk/subagent/test_subagent_registry.py::test_register_plugin_agents`, `::test_register_plugin_agents_with_hooks`. Example: none. Real-LLM: none.
- `S11.definition-factory`: `agent_definition_to_factory(defn)` builds an `Agent` with the definition's tools (unknown tool raises), skills (project over user, unknown raises), system prompt as `system_message_suffix`, MCP config, and a default summarizing condenser unless `condenser: none`. Unit: `tests/sdk/subagent/test_subagent_registry.py` (`test_agent_definition_to_factory_*`, `test_factory_*condenser*`). Example: `examples/01_standalone_sdk/42_file_based_subagents.py`. Real-LLM: none.
- `S11.definition-model`: `model: inherit` reuses the parent LLM; another value loads that LLM profile from `profile_store_dir` or the default store, and a missing profile raises. Unit: `tests/sdk/subagent/test_subagent_registry.py::test_agent_definition_to_factory_model_profile`, `::test_agent_definition_to_factory_model_profile_not_found`, `::test_agent_definition_to_factory_profile_store_dir`. Example: none. Real-LLM: none.
- `S11.builtin-agents`: `register_builtins_agents(enable_browser=True)` registers the four built-in Markdown agents as fallbacks, leaves out `web-researcher` when `enable_browser=False`, and keeps deprecated names (`default`, `default cli mode`, `explore`, `bash`) working with a `DeprecatedWarning`. Unit: `tests/tools/test_builtin_agents.py`. Example: `examples/01_standalone_sdk/25_agent_delegation.py`. Real-LLM: none.
- `S11.factory-info`: the `task` tool description lists the registered types (`get_factory_info`) and includes usage examples only for registered built-ins. Unit: `tests/sdk/subagent/test_subagent_registry.py::test_factory_info`, `tests/tools/task/test_task_tool_set.py::TestTaskToolExamples`. Example: none. Real-LLM: none.
- `S11.task-run`: a `task` call starts a fresh sub-conversation, sends the prompt (with the parent visualizer name as sender), runs it to completion and returns its final response with `status` `completed`; ids are sequential `task_00000001`, ... and unique under concurrency. Unit: `tests/tools/task/test_task_tool_set.py::TestTaskToolSetIntegration::test_basic_task_delegation_and_result`, `tests/tools/task/test_task_manager_thread_safety.py`. Example: `examples/01_standalone_sdk/41_task_tool_set.py`. Real-LLM: none.
- `S11.task-resume`: `task(resume="task_...")` reopens the same sub-conversation id from the persistence dir, so the sub-agent keeps its earlier context; an unknown id returns an error observation listing the known ids. Unit: `tests/tools/task/test_task_tool_set.py::TestTaskToolSetIntegration::test_task_resume_across_turns`, `::test_resume_nonexistent_task_returns_error`, `tests/tools/task/test_task_manager.py::TestTaskManager::test_resume_after_evict`. Example: `examples/01_standalone_sdk/41_task_tool_set.py`. Real-LLM: none.
- `S11.task-errors`: an unknown `subagent_type`, an exception in the sub-agent, or a non-FINISHED stop (iteration limit, stuck, paused) comes back as an error observation with the last `ConversationErrorEvent` detail and any partial output, never as an empty success. Unit: `tests/tools/task/test_task_tool_set.py::TestTaskToolSetIntegration::test_unknown_agent_type_returns_error_observation`, `::test_sub_agent_exception_returns_error_observation`, `tests/tools/task/test_task_manager.py::TestRunTask::test_non_finished_status_surfaced_as_error`, `::TestRunErrorSurfacing`. Example: none. Real-LLM: none.
- `S11.task-limits`: the sub-conversation's `max_iteration_per_run` and `max_budget_per_run` come from the definition, else from the parent conversation. Unit: `tests/tools/task/test_task_manager.py::TestTaskManager::test_create_task_prefers_factory_max_iteration_over_parent`, `::TestTaskManagerBudget`. Example: none. Real-LLM: none.
- `S11.task-metrics`: each sub-agent gets its own LLM copy (streaming off, fresh metrics), and after a run its combined metrics are stored in the parent's `conversation_stats.usage_to_metrics["task:<id>"]`, replaced on resume, not double counted. Unit: `tests/tools/task/test_task_manager.py::TestTaskMetrics`. Example: `examples/01_standalone_sdk/25_agent_delegation.py` (prints `EXAMPLE_COST`). Real-LLM: none.
- `S11.task-persistence`: with a persisting parent, sub-conversations are stored under `<parent persistence_dir>/subagents/` and kept on close; without one they go to a temporary `openhands_tasks_*` dir that `close()` deletes. Unit: `tests/tools/task/test_task_manager.py::TestTaskManagerPersistence`. Example: none. Real-LLM: none.
- `S11.task-hooks`: a definition's `hooks` become the sub-conversation's `hook_config`, on create and on resume. Unit: `tests/tools/task/test_task_manager.py::TestTaskManagerHooks`. Example: none. Real-LLM: none.
- `S11.task-observability`: sub-conversations share the parent's prompt cache key and carry delegate trace metadata (`is_delegate`, `task_id`, `subagent_type`, `parent_session_id`, parent span link) and the `delegate` tag. Unit: `tests/tools/task/test_task_manager.py::TestTaskManager::test_sub_agents_inherit_parent_prompt_cache_key`, `::test_marks_conversation_as_delegate_with_linking_metadata`, `::test_delegate_metadata_includes_parent_span_link`. Example: none. Real-LLM: none.
- `S11.task-confirmation`: a definition's `permission_mode` sets the sub-conversation's confirmation policy, omission inherits the parent's; when the sub-agent waits for confirmation, `TaskToolSet.create(confirmation_handler=...)` decides, and without a handler the actions are approved. Unit: **none (untested)**. Example: none. Real-LLM: none.
- `S11.sub-agent-scope`: `SubAgentScope(tools=True, mcp_servers=True)` (the `sub_agent_scope` tool param) hides and refuses sub-agents whose tools or MCP servers the parent lacks, compares built-in tool names canonically, propagates to nested delegation tools, and says so when no sub-agent fits. Unit: `tests/sdk/subagent/test_subagent_scope.py`, `tests/tools/task/test_sub_agent_scope.py`. Example: none. Real-LLM: none.
- `S11.delegate-executor`: the older `DelegateExecutor` (`spawn` named sub-agents, then `delegate` a dict of tasks run in parallel threads) closes replaced and spawned sub-agents, rolls back a partial spawn, merges metrics, and inherits the parent's persistence dir. Unit: `tests/tools/delegate/test_delegation.py`. Example: none. Real-LLM: none.
- `S11.delegation-visualizer`: `DelegationVisualizer(name=...)` labels messages by sender and agent name and creates per-task sub-visualizers. Unit: `tests/tools/delegate/test_visualizer.py`. Example: all three examples. Real-LLM: none.

## How to get to it (agent POV)

- `Agent(tools=[Tool(name=TaskToolSet.name)])` (`openhands.tools.task`; importing the module registers `task_tool_set` and `task`). Tool params: `Tool(name="task_tool_set", params={"sub_agent_scope": {"tools": True, "mcp_servers": True}})`. Model-facing action: `TaskAction(prompt, subagent_type="general-purpose", resume=None, description=None)`. Covers `S11.task-*`, `S11.sub-agent-scope`, `S11.factory-info`.
- `TaskToolSet.create(conv_state, confirmation_handler=..., sub_agent_scope=...)` when building tools by hand (`S11.task-confirmation`).
- `openhands.sdk.subagent`: `register_agent`, `register_agent_if_absent`, `register_file_agents`, `register_plugin_agents`, `get_agent_factory`, `get_factory_info`, `discover_agents`, `load_project_agents`, `load_user_agents`, `AgentDefinition`, `agent_definition_to_factory`, `SubAgentScope` (also re-exported: `from openhands.sdk import register_agent, agent_definition_to_factory`). Covers `S11.register-*`, `S11.markdown-schema`, `S11.file-*`, `S11.definition-*`, `S11.plugin-agents`.
- `openhands.tools.register_builtins_agents(enable_browser=True)`; definitions in `openhands-tools/openhands/tools/preset/subagents/*.md` (`S11.builtin-agents`).
- Files on disk: `{workspace}/.agents/agents/*.md`, `{workspace}/.openhands/agents/*.md`, `~/.agents/agents/*.md`, `~/.openhands/agents/*.md`, picked up on the conversation's first `send_message()`/`run()` (`S11.conversation-autoregister`).
- `Agent(tool_concurrency_limit=2)` lets two `task` calls in one model response run in parallel (example 25).
- `openhands.tools.delegate`: `DelegateExecutor(max_children=5, confirmation_handler=...)`, `DelegationVisualizer` (`S11.delegate-executor`, `S11.delegation-visualizer`).

## Driving it

Preconditions:
- `uv sync --dev` has run.
- `LLM_API_KEY` and `LLM_MODEL` (and optionally `LLM_BASE_URL`) exported for the example bullets.

- **Registry, schema and file discovery (`S11.register-programmatic`, `S11.register-if-absent`, `S11.markdown-schema`, `S11.file-discovery`, `S11.file-precedence`, `S11.plugin-agents`, `S11.definition-factory`, `S11.definition-model`, `S11.factory-info`, `S11.sub-agent-scope`).**
  ```sh
  uv run pytest tests/sdk/subagent -q
  ```
  All tests pass with no LLM or network.
- **Built-in agents (`S11.builtin-agents`).**
  ```sh
  uv run pytest tests/tools/test_builtin_agents.py -q
  ```
  The four built-ins register; `web-researcher` is absent with `enable_browser=False`; deprecated names warn.
- **Task tool lifecycle (`S11.task-run`, `S11.task-resume`, `S11.task-errors`, `S11.task-limits`, `S11.task-metrics`, `S11.task-persistence`, `S11.task-hooks`, `S11.task-observability`, `S11.sub-agent-scope`).** Mocked LLMs, deterministic.
  ```sh
  uv run pytest tests/tools/task -q
  ```
  The tests pass; then with a real model:
  ```sh
  uv run python examples/01_standalone_sdk/41_task_tool_set.py
  ```
  The quiz host calls `task` twice, the second time with `resume`, and prints `EXAMPLE_COST`.
- **Programmatic plus built-in types in parallel (`S11.register-programmatic`, `S11.builtin-agents`, `S11.task-metrics`).**
  ```sh
  uv run python examples/01_standalone_sdk/25_agent_delegation.py
  ```
  Two `task` calls run in parallel, a `bash-runner` sub-agent writes `london_trip_report.txt` into the current directory, and `EXAMPLE_COST` reflects sub-agent spend.
- **Inline `AgentDefinition` (`S11.definition-factory`).**
  ```sh
  uv run python examples/01_standalone_sdk/42_file_based_subagents.py
  ```
  The orchestrator delegates to `grammar-checker`, which reads `README.md` with `file_editor`.
- **Delegate executor and visualizer (`S11.delegate-executor`, `S11.delegation-visualizer`).**
  ```sh
  uv run pytest tests/tools/delegate -q
  ```
  All tests pass.
- **Workspace Markdown agents picked up by a conversation (`S11.conversation-autoregister`), untested.** Put a `.agents/agents/<name>.md` in the workspace, start a conversation with `TaskToolSet` and ask it to delegate to `<name>`; the `task` observation should name that sub-agent. No test proves this.
- **Sub-agent confirmation (`S11.task-confirmation`), untested.** Needs a Markdown agent with `permission_mode: always_confirm` and a `confirmation_handler` that returns False; the sub-agent's actions should be rejected. No test exercises it.

## Gotchas

- Example 42's file name says "file based" but it defines the agent inline with `AgentDefinition`; no example loads `.agents/agents/*.md` from disk.
- The registry is a process-wide global. Tests reset it through `_reset_registry_for_tests()`; a script that calls `register_agent` twice with one name raises. Built-ins registered before a workspace's file agents win over them by name (the agent server does this at import).
- `register_builtins_agents()` also calls `register_default_tools(...)`. Without it, a built-in type that names `terminal`/`file_editor` raises `ValueError` at factory time for an unregistered tool. Example 41 does not call it, so only `animal_expert` is available there.
- Example 25 tells the model to use "the bash sub-agent"; the registered name is `bash-runner` (`bash` survives only as a deprecated alias).
- Sub-agent LLMs are copies of the parent's LLM with `stream=False`; `model:` in a definition switches to an LLM profile, not to a raw model string.
- There is no registered tool definition for `DelegateExecutor` in this checkout (only `TaskToolSet`/`TaskTool` call `register_tool`); `DelegateExecutor` is a library class exercised only by its unit tests.
- `TaskAction.max_turns` is deprecated and ignored.
- `tests/tools/delegate/test_delegation.py` emits `PydanticSerializationUnexpectedValue` warnings from `MagicMock` parents; they are harmless.
- All three examples run in `tests/examples/test_examples.py` (none is in `_EXCLUDED_EXAMPLES`) but only on the `test-examples` label.
