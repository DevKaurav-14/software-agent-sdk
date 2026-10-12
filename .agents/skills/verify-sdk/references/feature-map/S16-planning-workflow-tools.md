# Planning, task tracking, oracle, ToM and workflow tools

Tools an SDK program adds to an agent to help it plan and coordinate rather than to touch the system directly. `task_tracker` keeps a structured task list (`plan` replaces it, `view` shows it, each item `todo`, `in_progress` or `done`) and saves it as `TASKS.json` in the conversation's persistence directory. The planning preset (`get_planning_agent(llm)`) is a read-only agent with `glob`, `grep` and `planning_file_editor`, a planning system prompt that fixes a five-section plan structure, and a larger summarizing condenser; `planning_file_editor` can view any file but edit only `PLAN.md`, which it creates with section headers at `.agents_tmp/PLAN.md` (or a legacy root `PLAN.md`, or an absolute `plan_path`). Example 24 chains a planning conversation and an execution conversation over the same workspace. `ask_oracle` sends the agent's question to a second model, the saved LLM profile named `oracle`, and returns its answer. `tom_consult` and `sleeptime_compute` wrap the `tom-swe` Theory-of-Mind agent: one gives personalized guidance for a vague request, the other indexes past conversations into a user model stored under the user persistence directory. `workflow` (from `workflow_tool_set`) runs a Python script the agent writes, `async def main(wf)`, in a restricted namespace where `wf.run_agent`, `wf.map_agents`, `wf.pipeline` and `wf.reduce_agent` fan work out to registered sub-agents with a concurrency cap and a one-hour limit.

Source: `openhands-tools/openhands/tools/task_tracker/`, `openhands-tools/openhands/tools/planning_file_editor/`, `openhands-tools/openhands/tools/preset/planning.py`, `openhands-tools/openhands/tools/ask_oracle/`, `openhands-tools/openhands/tools/tom_consult/`, `openhands-tools/openhands/tools/workflow/`, `openhands-sdk/openhands/sdk/context/prompts/sections/planning.py`

Needs: `llm` (examples, real oracle and ToM calls, workflow sub-agents)

Examples: `examples/01_standalone_sdk/24_planning_agent_workflow.py`, `examples/01_standalone_sdk/30_tom_agent.py`, `examples/01_standalone_sdk/52_dynamic_workflow.py`, `examples/01_standalone_sdk/58_ask_oracle_tool/main.py`

## Sub-features

- `S16.task-tracker-plan-view`: `TaskTrackerAction(command="plan", task_list=[TaskItem(title=..., notes=..., status=...)])` replaces the list and `command="view"` returns it as a numbered Markdown list with status icons. Unit: **none (untested)**. Example: `examples/01_standalone_sdk/01_hello_world.py` (tool attached). Real-LLM: none.
- `S16.task-tracker-persistence`: `TaskTrackerTool.create(conv_state)` points `save_dir` at the conversation's persistence directory (which includes the conversation id); each `plan` writes `TASKS.json` there and a new executor on the same directory loads it back. Unit: **none (untested)** for writing and reloading; `tests/cross/test_registry_directories.py` only checks `save_dir`. Example: none. Real-LLM: none.
- `S16.planning-tools`: `get_planning_tools(plan_path=None)` registers and returns `glob`, `grep` and `planning_file_editor`, forwarding `plan_path` as the editor's `params`; `glob` and `grep` register on import. Unit: `tests/tools/test_planning_preset.py`, `tests/cross/test_automatic_registration.py` (`test_grep_tool_automatic_registration`, `test_glob_tool_automatic_registration`, `test_planning_file_editor_tool_automatic_registration`). Example: `examples/01_standalone_sdk/24_planning_agent_workflow.py`. Real-LLM: `tests/integration/run_infer.py --tool-preset planning`.
- `S16.plan-file-location`: without `plan_path` the editor uses `<workspace>/.agents_tmp/PLAN.md`, or an existing legacy `<workspace>/PLAN.md` (with a warning); an absolute `plan_path` is used as given and its parent directory created; a relative `plan_path` raises `ValueError`; the tool description names the path. Unit: `tests/tools/planning_file_editor/test_planning_file_editor_tool.py`. Example: `examples/01_standalone_sdk/24_planning_agent_workflow.py`. Real-LLM: none.
- `S16.plan-file-headers`: a missing `PLAN.md` is created with the five numbered headers (`OBJECTIVE`, `CONTEXT SUMMARY`, `APPROACH OVERVIEW`, `IMPLEMENTATION STEPS`, `TESTING AND VALIDATION`) from `get_plan_headers()`. Unit: **none (untested)**; the tests check that the file exists, not its content. Example: `examples/01_standalone_sdk/24_planning_agent_workflow.py`. Real-LLM: none.
- `S16.plan-edit-restriction`: `planning_file_editor` allows `view` on any path but answers `create`, `str_replace`, `insert` and `undo_edit` on any file other than the plan with an error observation ("Operation ... is not allowed"). Unit: **none (untested)**; no test exercises `FileEditorExecutor(allowed_edits_files=...)`. Example: none. Real-LLM: none.
- `S16.planning-agent`: `get_planning_agent(llm)` builds an `Agent` with the planning tools, `system_prompt_filename="system_prompt_planning.j2"` (mapped to the planning prompt preset) with `plan_structure` filled in, and an `LLMSummarizingCondenser` (`max_size=100`, `keep_first=6`, `usage_id="planning_condenser"`). Unit: `tests/sdk/context/prompts/test_planning_registry.py` (the prompt section against a snapshot; `get_planning_agent` itself is not unit-tested). Example: `examples/01_standalone_sdk/24_planning_agent_workflow.py`. Real-LLM: none.
- `S16.plan-then-execute`: a planning conversation writes the plan and a second conversation with `get_default_agent(llm, cli_mode=True)` in the same workspace reads `.agents_tmp/PLAN.md` and implements it. Unit: **none (untested)**. Example: `examples/01_standalone_sdk/24_planning_agent_workflow.py`. Real-LLM: none.
- `S16.oracle-tool`: `Tool(name="ask_oracle")` resolves without params (params are rejected), and its description tells the agent when to ask for a second opinion. Unit: `tests/tools/ask_oracle/test_ask_oracle.py` (`test_ask_oracle_tool_added_by_name`, `test_ask_oracle_tool_rejects_parameters`, `test_ask_oracle_tool_description_guides_second_opinion_usage`). Example: `examples/01_standalone_sdk/58_ask_oracle_tool/main.py`. Real-LLM: none.
- `S16.oracle-consult`: a call loads the `oracle` profile from the conversation's profile store (`LocalConversation(profile_store_dir=...)`), sends the question with context, returns the answer as the observation, and books cost under an `oracle` usage id. Unit: `tests/tools/ask_oracle/test_ask_oracle.py::test_ask_oracle_tool_returns_oracle_recommendation`. Example: `examples/01_standalone_sdk/58_ask_oracle_tool/main.py`. Real-LLM: none.
- `S16.oracle-errors`: without an active conversation, without an `oracle` profile ("Save one to enable it"), or with an empty answer, the tool returns an error observation instead of raising. Unit: `tests/tools/ask_oracle/test_ask_oracle.py` (`test_ask_oracle_tool_requires_active_conversation`, `test_ask_oracle_tool_reports_missing_profile`, `test_ask_oracle_tool_reports_empty_oracle_response`). Example: none. Real-LLM: none.
- `S16.tom-consult`: `Tool(name="tom_consult", params={"enable_rag": True, "llm_model": ..., "api_key": ..., "api_base": ...})` lets the agent ask the ToM agent about the user's last message or a custom query and get `suggestions`, `confidence` and `reasoning`; it declares no resource keys. Unit: `tests/tools/tom_consult/test_tom_consult_tool.py` (declared resources only; the consult call is not tested). Example: `examples/01_standalone_sdk/30_tom_agent.py`. Real-LLM: none.
- `S16.tom-sleeptime`: `sleeptime_compute` (often called up front with `conversation.execute_tool("sleeptime_compute", SleeptimeComputeAction())`) indexes stored conversations and reports `sessions_processed`. Unit: **none (untested)**. Example: `examples/01_standalone_sdk/30_tom_agent.py`. Real-LLM: none.
- `S16.tom-storage-root`: both ToM tools keep their user model in a `LocalFileStore` rooted at the user persistence directory (`~/.openhands`, or `OH_PERSISTENCE_DIR`). Unit: `tests/cross/test_persistence_dir_call_sites.py::test_tom_consult_file_store_root`. Example: `examples/01_standalone_sdk/30_tom_agent.py`. Real-LLM: none.
- `S16.workflow-toolset`: `Tool(name="workflow_tool_set", params={"sub_agent_scope": {...}})` yields one `workflow` tool (`name`, `script`, `max_concurrency` 1 to 64, default 8); the tool needs a local conversation and returns an error observation without one. Unit: `tests/tools/workflow/test_workflow_tool.py` (`test_workflow_executor_success_path`, `test_workflow_executor_returns_error_observation_without_conversation`), `tests/cross/test_default_tool_names.py::test_delegation_names_are_the_tools_that_take_a_sub_agent_scope`. Example: `examples/01_standalone_sdk/52_dynamic_workflow.py`. Real-LLM: none.
- `S16.workflow-script-validation`: a script must define `async def main(wf)`; imports, unsafe builtins and modules, private `wf` attributes and `wf.close()` are rejected before it runs. Unit: `tests/tools/workflow/test_workflow_tool.py` (`test_validate_workflow_script_rejects_*`). Example: none. Real-LLM: none.
- `S16.workflow-fan-out`: `wf.run_agent(prompt, subagent_type="general-purpose")` starts one sub-agent task and returns its result; `wf.map_agents(items, prompt, ...)` runs one per item under the concurrency cap and reports every failure; `wf.reduce_agent` summarizes; `wf.flatten` flattens one level. Unit: `tests/tools/workflow/test_workflow_tool.py` (`test_execute_workflow_script_runs_map_and_reduce`, `test_run_agent_returns_task_result`, `test_map_agents_uses_context_default_concurrency_when_none_given`, `test_map_agents_reports_all_sub_agent_failures`, `test_map_agents_respects_context_concurrency_cap`, `test_workflow_context_helper_flattens_one_level`). Example: `examples/01_standalone_sdk/52_dynamic_workflow.py`. Real-LLM: none.
- `S16.workflow-pipeline`: `wf.pipeline(items, stage1, stage2, ...)` runs sync or async stages per item with no barrier between stages, keeps item order, and drops a failed item to `None`; it needs at least one stage. Unit: `tests/tools/workflow/test_workflow_tool.py` (`test_pipeline_*`). Example: none. Real-LLM: none.
- `S16.workflow-errors-and-output`: the script can catch common exceptions and `ExceptionGroup`s; uncaught errors come back formatted (with group details); large results are truncated by whole elements or characters before they reach the LLM. Unit: `tests/tools/workflow/test_workflow_tool.py` (`test_workflow_script_can_catch_*`, `test_format_exception_includes_exception_group_details`, `test_format_value_*`). Example: none. Real-LLM: none.
- `S16.workflow-lifecycle`: closing the context closes the task manager once, and `run_agent` after close raises. Unit: `tests/tools/workflow/test_workflow_tool.py` (`test_workflow_context_close_propagates_to_manager`, `test_workflow_context_close_is_idempotent`, `test_run_agent_raises_after_close`). Example: none. Real-LLM: none.

## How to get to it (agent POV)

- Task tracker: `Tool(name="task_tracker")` (in every preset); direct use `TaskTrackerExecutor(save_dir=...)` with `TaskTrackerAction` and `TaskItem` from `openhands.tools.task_tracker.definition`. `S16.task-tracker-*`.
- Planning: `from openhands.tools.preset.planning import get_planning_agent, get_planning_tools, get_plan_headers, format_plan_structure`; `Tool(name="planning_file_editor", params={"plan_path": "/abs/PLAN.md"})`; direct use `PlanningFileEditorExecutor(workspace_root=..., plan_path=...)` from `openhands.tools.planning_file_editor.impl`. `S16.planning-*`, `S16.plan-*`.
- Oracle: save a profile first, `LLMProfileStore(dir).save("oracle", LLM(...), include_secrets=True)` (`ORACLE_PROFILE_NAME` from `openhands.tools.ask_oracle`), then `Agent(tools=[Tool(name=AskOracleTool.name)])` and `LocalConversation(..., profile_store_dir=dir)`. `S16.oracle-*`.
- ToM: `from openhands.tools.tom_consult import TomConsultTool, SleeptimeComputeTool, SleeptimeComputeAction`; `Tool(name=TomConsultTool.name, params=tom_params)`; `OH_PERSISTENCE_DIR` moves the user-model store. `S16.tom-*`.
- Workflow: `from openhands.tools.workflow import WorkflowToolSet`; `Tool(name=WorkflowToolSet.name)`; sub-agents come from `register_agent_if_absent(name=..., factory_func=..., description=...)` (`openhands.sdk.subagent`) or the built-ins; `WorkflowTool.create(executor=...)` injects a custom executor. `S16.workflow-*`.
- Integration runner: `tests/integration/run_infer.py --tool-preset planning` swaps in `get_planning_tools()`.

## Driving it

Preconditions:

- `uv sync --dev` has run (it installs `tom-swe`, a required dependency of `openhands-tools`).
- For example bullets: `LLM_API_KEY` (and optionally `LLM_MODEL`, `LLM_BASE_URL`) exported.

- **Planning tools and plan file (`S16.planning-tools`, `S16.plan-file-location`, `S16.planning-agent`).**
  ```sh
  uv run pytest tests/tools/planning_file_editor tests/tools/test_planning_preset.py tests/sdk/context/prompts/test_planning_registry.py tests/cross/test_automatic_registration.py -q
  ```
  23 pass.
- **Plan headers and edit restriction (`S16.plan-file-headers`, `S16.plan-edit-restriction`), untested.** Deterministic check without a model.
  ```sh
  uv run python -c "
  import os, tempfile
  from openhands.tools.planning_file_editor.impl import PlanningFileEditorExecutor
  from openhands.tools.planning_file_editor.definition import PlanningFileEditorAction
  from openhands.tools.preset.planning import get_plan_headers
  d = tempfile.mkdtemp(); plan = os.path.join(d, '.agents_tmp', 'PLAN.md'); os.makedirs(os.path.dirname(plan))
  ex = PlanningFileEditorExecutor(workspace_root=d, plan_path=plan)
  print(ex(PlanningFileEditorAction(command='create', path=os.path.join(d, 'x.py'), file_text='x')).is_error)
  print(ex(PlanningFileEditorAction(command='create', path=plan, file_text=get_plan_headers())).is_error)
  "
  ```
  Prints `True` (edit outside the plan refused) then `False`.
- **Task tracker (`S16.task-tracker-plan-view`, `S16.task-tracker-persistence`), untested.**
  ```sh
  uv run pytest tests/cross/test_registry_directories.py -q
  uv run python -c "
  import os, tempfile
  from openhands.tools.task_tracker.definition import TaskTrackerExecutor, TaskTrackerAction, TaskItem
  d = tempfile.mkdtemp()
  TaskTrackerExecutor(save_dir=d)(TaskTrackerAction(command='plan', task_list=[TaskItem(title='a', status='in_progress')]))
  print(os.listdir(d)); print(TaskTrackerExecutor(save_dir=d)(TaskTrackerAction(command='view')).text)
  "
  ```
  The test passes; the snippet prints `['TASKS.json']` and a "# Task List" with the reloaded item.
- **Planning workflow with a real model (`S16.planning-agent`, `S16.plan-then-execute`).**
  ```sh
  uv run python examples/01_standalone_sdk/24_planning_agent_workflow.py
  ```
  It prints the plan path in a temp workspace, the execution result, and the files created.
- **Oracle (`S16.oracle-tool`, `S16.oracle-consult`, `S16.oracle-errors`).** Unit proof with a test LLM, then the example.
  ```sh
  uv run pytest tests/tools/ask_oracle -q
  uv run python examples/01_standalone_sdk/58_ask_oracle_tool/main.py
  ```
  7 tests pass; the example prints both model names and a two-word answer, and `Total cost`.
- **ToM (`S16.tom-consult`, `S16.tom-sleeptime`, `S16.tom-storage-root`); sleeptime compute untested, consult only for declared resources.**
  ```sh
  uv run pytest tests/tools/tom_consult "tests/cross/test_persistence_dir_call_sites.py::test_tom_consult_file_store_root" -q
  uv run python examples/01_standalone_sdk/30_tom_agent.py
  ```
  3 tests pass; the example prints the sleeptime result and sessions processed, then runs a conversation that consults Tom.
- **Workflow (`S16.workflow-*`).** The task manager is faked in the tests.
  ```sh
  uv run pytest tests/tools/workflow tests/cross/test_default_tool_names.py -q
  uv run python examples/01_standalone_sdk/52_dynamic_workflow.py
  ```
  37 tests pass; the example has the parent agent write and run a workflow that fans `coverage_auditor` sub-agents over the repo and prints the reducer's report.

## Gotchas

- `TaskTrackerExecutor`'s docstring says tasks go to `TASKS.md`; the file actually written and read is `TASKS.json`.
- `TaskTrackerTool` only persists when the conversation has a persistence directory; with none, `save_dir` is `None` and the list lives in memory.
- Example 30 stores its conversations and the ToM user model under `~/.openhands` (it sets `persistence_dir` to `~/.openhands/conversations`); set `OH_PERSISTENCE_DIR` to keep a test run out of your home directory. Its ToM tools get the API key in plain `params`.
- Example 58 defaults `LLM_BASE_URL` to `https://llm-proxy.app.all-hands.dev` and uses `ASK_ORACLE_PRIMARY_MODEL` / `ASK_ORACLE_MODEL` to pick the two models; without them both are `LLM_MODEL` (default `openai/gpt-5.5`).
- Example 52 sets `max_iteration_per_run=6`; a model that needs more turns to write the script stops early. Its sub-agents run against the current repository (read-only by instruction only).
- The workflow tool runs the script with `asyncio.run` in the tool thread and a hard one-hour limit (`_WORKFLOW_TIMEOUT_SECONDS`); the sandbox is an AST check plus restricted globals, not process isolation.
- `get_planning_agent` passes `system_prompt_filename="system_prompt_planning.j2"`, a file that no longer exists; the name is mapped to the planning prompt preset in `openhands-sdk/openhands/sdk/agent/base.py`, so do not look for the template.
