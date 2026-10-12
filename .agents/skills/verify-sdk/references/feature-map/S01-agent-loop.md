# Agent step loop

A Python program builds `Agent(llm=..., tools=[...])`, wraps it in `Conversation(agent=..., workspace=...)`, calls `send_message(...)` and then `run()` (or `await arun()`). `run()` repeatedly calls `Agent.step()`: each step builds the LLM message list from the event view (condensing first if the condenser asks), calls `LLM.generate`, and dispatches the reply. Tool calls become `ActionEvent`s that are executed (sequentially by default, or concurrently up to `Agent.tool_concurrency_limit`) and answered by `ObservationEvent`s; a plain text reply or a `FinishAction` sets the status to `FINISHED`; a reasoning-only or empty reply gets a corrective nudge and the loop continues. The loop stops on `FINISHED`, `PAUSED`, `WAITING_FOR_CONFIRMATION`, `STUCK` (the stuck detector saw a repeating pattern), or `ERROR` with a `ConversationErrorEvent` (`MaxIterationsReached` after `max_iteration_per_run` steps, `MaxBudgetReached` after `max_budget_per_run` dollars). Messages sent from another thread while `run()` is busy are picked up by the next step. Images go in as `ImageContent` inside a `Message`; a non-vision model gets a capability message instead of a call. `conversation.ask_agent(question)` asks a side question that leaves no trace in the conversation. A tool spec with `params={"response_schema": Model}` turns that tool's arguments (typically `finish`) into typed structured output.

Source: `openhands-sdk/openhands/sdk/agent/agent.py`, `openhands-sdk/openhands/sdk/agent/base.py`, `openhands-sdk/openhands/sdk/agent/response_dispatch.py`, `openhands-sdk/openhands/sdk/agent/parallel_executor.py`, `openhands-sdk/openhands/sdk/agent/stream_context.py`, `openhands-sdk/openhands/sdk/agent/utils.py`, `openhands-sdk/openhands/sdk/agent/critic_mixin.py`, `openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py`, `openhands-sdk/openhands/sdk/conversation/stuck_detector.py`, `openhands-sdk/openhands/sdk/conversation/types.py`, `openhands-sdk/openhands/sdk/tool/builtins/finish.py`, `openhands-sdk/openhands/sdk/tool/tool.py`

Needs: `llm`, `network`, `tmux`

Examples: `examples/01_standalone_sdk/01_hello_world.py`, `examples/01_standalone_sdk/17_image_input.py`, `examples/01_standalone_sdk/18_send_message_while_processing.py`, `examples/01_standalone_sdk/20_stuck_detector.py`, `examples/01_standalone_sdk/28_ask_agent_example.py`, `examples/01_standalone_sdk/31_iterative_refinement.py`, `examples/01_standalone_sdk/45_parallel_tool_execution.py`, `examples/01_standalone_sdk/56_structured_output.py`

## Sub-features

- `S01.run-to-finish`: `send_message` + `run()` steps until the agent finishes; status moves IDLE to RUNNING to FINISHED, a second `run()` on a finished conversation returns at once, and a new message moves FINISHED back to IDLE. Unit: `tests/sdk/conversation/local/test_agent_status_transition.py`. Example: `examples/01_standalone_sdk/01_hello_world.py`. Real-LLM: `tests/integration/tests/t01_fix_simple_typo.py`, `tests/integration/tests/t02_add_bash_hello.py`.
- `S01.response-dispatch`: each LLM reply is classified as tool calls, content, reasoning-only or empty; tool calls execute, content sets FINISHED, and the batch's `ActionEvent`s are emitted consecutively. Unit: `tests/sdk/agent/test_response_dispatch.py`. Example: none. Real-LLM: none.
- `S01.empty-reply-nudge`: a reasoning-only or completely empty reply injects a corrective user nudge and the loop continues instead of finishing; the nudge does not reset the stuck-detection window. Unit: `tests/sdk/agent/test_reasoning_only_responses.py`, `tests/sdk/agent/test_tool_call_recovery.py`, `tests/sdk/agent/test_response_dispatch.py::test_corrective_nudge_does_not_reset_stuck_detection_window`. Example: none. Real-LLM: none.
- `S01.max-iterations`: after `max_iteration_per_run` steps (default 500) the run stops with status ERROR and a `ConversationErrorEvent(code="MaxIterationsReached")`, unless the last step finished, which keeps FINISHED. Unit: `tests/sdk/conversation/local/test_agent_status_transition.py::test_execution_status_error_on_max_iterations`, `::test_execution_status_finished_on_final_iteration`. Example: `examples/01_standalone_sdk/28_ask_agent_example.py` (`max_iteration_per_run=5`). Real-LLM: none.
- `S01.max-budget`: with `max_budget_per_run` set, the run stops with ERROR and `MaxBudgetReached` once the combined cost of all the conversation's LLMs reaches it; a finished run stays FINISHED. Unit: `tests/sdk/conversation/local/test_agent_status_transition.py::test_execution_status_error_on_max_budget`, `::test_finished_preserved_even_when_over_budget`. Example: none. Real-LLM: none.
- `S01.stuck-detect`: with `stuck_detection=True` (default) the detector flags repeated action/observation pairs (4), repeated action/error pairs (3), agent monologue (3) and alternating patterns (6) in the events since the last user message, and sets status STUCK. Unit: `tests/cross/test_stuck_detector.py`. Example: `examples/01_standalone_sdk/20_stuck_detector.py`. Real-LLM: none.
- `S01.stuck-thresholds`: `stuck_detection_thresholds` (a `StuckDetectionThresholds` or a dict) overrides the four thresholds. Unit: `tests/cross/test_stuck_detector_config.py`. Example: none. Real-LLM: none.
- `S01.stuck-nudge`: a repeating action-error streak first gets one environment nudge message; the conversation goes STUCK only if the streak continues, and recovers if the model self-corrects. Unit: `tests/sdk/conversation/local/test_stuck_detector_nudge.py`. Example: none. Real-LLM: none.
- `S01.stuck-recover`: `run()` on a STUCK conversation and `send_message` after STUCK both resume the loop. Unit: `tests/sdk/conversation/local/test_agent_status_transition.py::test_run_recovers_from_stuck`, `::test_send_message_resets_stuck_to_idle`. Example: none. Real-LLM: none.
- `S01.parallel-tools`: `Agent(tool_concurrency_limit=N)` (default 1, must be >= 1) runs up to N tool calls of one step concurrently, is faster than sequential, keeps results in call order, and keeps the other results when one call errors. Unit: `tests/sdk/agent/test_parallel_execution_integration.py`, `tests/sdk/agent/test_parallel_executor.py`. Example: `examples/01_standalone_sdk/45_parallel_tool_execution.py`. Real-LLM: none.
- `S01.parallel-resource-locks`: concurrent tools that declare the same resource keys serialize, tools that declare no keys share a per-tool mutex, and an empty key list skips locking. Unit: `tests/sdk/agent/test_parallel_executor_locking.py`. Example: none. Real-LLM: none.
- `S01.finish-truncates-batch`: tool calls after a `finish` call in the same batch are dropped, and a call blocked by a hook produces a rejection in place. Unit: `tests/sdk/agent/test_action_batch.py`, `tests/sdk/agent/test_parallel_execution_integration.py::test_finish_tool_truncates_subsequent_tools`. Example: none. Real-LLM: none.
- `S01.message-while-running`: `send_message` from another thread while `run()` or `arun()` is mid-step is absorbed by the next step instead of being lost or ending the run; a message during a confirmation wait supersedes the pending action. Unit: `tests/sdk/agent/test_message_during_streaming_arun.py`, `tests/sdk/agent/test_message_while_finishing.py`. Example: `examples/01_standalone_sdk/18_send_message_while_processing.py`. Real-LLM: none.
- `S01.async-step`: `arun()`/`astep()` follow the same control flow and release the state lock while the LLM call is in flight, so other threads can read state and send messages. Unit: `tests/sdk/agent/test_astep_releases_state_lock.py`. Example: none. Real-LLM: none.
- `S01.image-input`: a user `Message` with `ImageContent(image_urls=[...])` (http URL or base64 `data:` URL) reaches a vision model; with more than 20 images to an Anthropic model, base64 images are downscaled to 2000x2000 px. Unit: `tests/sdk/llm/test_vision_support.py`, `tests/sdk/llm/test_llm_image_resizing.py`. Example: `examples/01_standalone_sdk/17_image_input.py`. Real-LLM: none (`tests/integration/tests/t08_image_file_viewing.py` covers images read by a tool, not user input).
- `S01.image-non-vision`: images sent to a non-vision model produce an agent message saying the model cannot see images and the run finishes without an LLM call; if a vision profile tool is available the images are replaced by references the agent can inspect with that tool. Unit: `tests/sdk/agent/test_non_multimodal_image_input.py`. Example: none. Real-LLM: none.
- `S01.ask-agent`: `conversation.ask_agent(question)` returns a direct LLM answer built from the current history, adds no events and leaves status unchanged, works while `run()` is in flight, drops unanswered tool calls from the context, and raises on context-window errors. Unit: `tests/sdk/conversation/test_ask_agent.py`. Example: `examples/01_standalone_sdk/28_ask_agent_example.py`. Real-LLM: none.
- `S01.structured-output`: `Tool(name=..., params={"response_schema": Model})` extends that tool's action schema with the model's fields, validates the LLM's arguments against it, and `tool.parse_last_response(events)` returns the latest typed instance. Invalid schemas (object-level constraints, dynamic fields, field collisions, reserved names, toolsets) are rejected. Unit: `tests/sdk/tool/test_response_schema.py`. Example: `examples/01_standalone_sdk/56_structured_output.py`. Real-LLM: none.
- `S01.malformed-tool-call`: malformed tool arguments are repaired when possible (control characters, stringified JSON); a call that still fails validation becomes a user `MessageEvent` with the validation error and the loop continues. Unit: `tests/sdk/agent/test_fix_malformed_tool_arguments.py`, `tests/sdk/agent/test_tool_validation_error_message.py`. Example: none. Real-LLM: none.
- `S01.unknown-tool`: a call to a tool the agent does not have yields an `AgentErrorEvent` the model sees, not a crash. Unit: `tests/sdk/agent/test_nonexistent_tool_handling.py`. Example: none. Real-LLM: none.
- `S01.tool-exception`: an exception inside a tool executor becomes an `AgentErrorEvent` for that call and the conversation continues. Unit: `tests/sdk/agent/test_tool_execution_error_handling.py`. Example: none. Real-LLM: none.
- `S01.content-policy`: an output blocked by the provider's content filter becomes a user nudge to rephrase, not a fatal error. Unit: `tests/sdk/agent/test_agent_content_policy_violation.py`. Example: none. Real-LLM: none.
- `S01.context-overflow`: a context-window or malformed-history error from the LLM emits a `CondensationRequest` when the condenser handles requests, and is raised otherwise. Unit: `tests/sdk/agent/test_agent_context_window_condensation.py`. Example: none. Real-LLM: `tests/integration/tests/c02_hard_context_reset.py`.
- `S01.iterative-refinement`: a program-level loop of fresh conversations (refactor, then critique, then refactor with feedback) until a score threshold or an iteration cap is met. Critic-driven refinement inside one conversation is family S12. Unit: **none (untested)**. Example: `examples/01_standalone_sdk/31_iterative_refinement.py`. Real-LLM: none.

## How to get to it (agent POV)

- `Conversation(agent=..., workspace=..., callbacks=[...], max_iteration_per_run=500, stuck_detection=True, stuck_detection_thresholds=None, max_budget_per_run=None)` returns a `LocalConversation` for a local workspace; `conversation.run()` / `await conversation.arun()` drive the loop. Covers `S01.run-to-finish`, `S01.max-*`, `S01.stuck-*`, `S01.async-step`.
- `conversation.state.execution_status` (`ConversationExecutionStatus`: IDLE, RUNNING, PAUSED, WAITING_FOR_CONFIRMATION, FINISHED, ERROR, STUCK) and `ConversationErrorEvent.code` are the observable outcome of a run; `conversation.stuck_detector.is_stuck()` re-checks on demand.
- `Agent(llm=..., tools=[Tool(name=TerminalTool.name), ...], tool_concurrency_limit=1, condenser=..., critic=..., include_default_tools=[...])`; `get_default_agent(llm=...)` from `openhands.tools.preset.default` gives the stock tool set. Covers `S01.parallel-*`, `S01.finish-truncates-batch`, `S01.context-overflow`.
- `conversation.send_message(str | Message)` from any thread, including while `run()` runs in a `threading.Thread`. Covers `S01.message-while-running`.
- `Message(role="user", content=[TextContent(...), ImageContent(image_urls=[...])])`; `llm.vision_is_active()` tells whether images will be sent; `LLM(disable_vision=True)` forces text-only. Covers `S01.image-*`.
- `conversation.ask_agent("question")` returns `str`. Covers `S01.ask-agent`.
- `register_tool("FinishTool", FinishTool)` then `Tool(name="FinishTool", params={"response_schema": MyModel})`; read back with `agent.tools_map["finish"].parse_last_response(conversation.state.events)`. Covers `S01.structured-output`.
- `Agent.step()` / `Agent.astep()` are what `run()` calls; custom agents subclass `AgentBase` and implement `step`.

## Driving it

Preconditions:
- `uv sync --dev` has run.
- For example bullets: `LLM_API_KEY` exported, optionally `LLM_MODEL` (default `gpt-5.5`) and `LLM_BASE_URL`; `tmux` installed (the terminal tool); network access.

- **Run loop and status transitions (`S01.run-to-finish`, `S01.max-iterations`, `S01.max-budget`, `S01.stuck-recover`).** Deterministic proof with a scripted LLM, then the hello-world example with a real model.
  ```sh
  uv run pytest tests/sdk/conversation/local/test_agent_status_transition.py -q
  uv run python examples/01_standalone_sdk/01_hello_world.py
  ```
  12 tests pass; the example writes `FACTS.txt` in the repo root and exits.
- **Reply classification and nudges (`S01.response-dispatch`, `S01.empty-reply-nudge`).**
  ```sh
  uv run pytest tests/sdk/agent/test_response_dispatch.py tests/sdk/agent/test_reasoning_only_responses.py tests/sdk/agent/test_tool_call_recovery.py -q
  ```
  The tests pass: content finishes, reasoning-only and empty replies inject a nudge.
- **Stuck detection (`S01.stuck-detect`, `S01.stuck-thresholds`, `S01.stuck-nudge`).**
  ```sh
  uv run pytest tests/cross/test_stuck_detector.py tests/cross/test_stuck_detector_config.py tests/sdk/conversation/local/test_stuck_detector_nudge.py -q
  uv run python examples/01_standalone_sdk/20_stuck_detector.py
  ```
  The tests pass; the example asks for five identical `ls` actions and prints `Final stuck status: True` if the model complies (a model that refuses to repeat itself prints `False`).
- **Parallel tool execution (`S01.parallel-tools`, `S01.parallel-resource-locks`, `S01.finish-truncates-batch`).**
  ```sh
  uv run pytest tests/sdk/agent/test_parallel_execution_integration.py tests/sdk/agent/test_parallel_executor.py tests/sdk/agent/test_parallel_executor_locking.py tests/sdk/agent/test_action_batch.py -q
  uv run python examples/01_standalone_sdk/45_parallel_tool_execution.py
  ```
  The tests pass; the example prints a "Parallelism Report" listing, per agent, the batches whose tool calls ran in parallel.
- **Messages during a run, async loop (`S01.message-while-running`, `S01.async-step`).**
  ```sh
  uv run pytest tests/sdk/agent/test_message_during_streaming_arun.py tests/sdk/agent/test_message_while_finishing.py tests/sdk/agent/test_astep_releases_state_lock.py -q
  uv run python examples/01_standalone_sdk/18_send_message_while_processing.py
  ```
  The tests pass; the example's `document.txt` has three lines, the third from a message sent while the agent was sleeping.
- **Image input (`S01.image-input`, `S01.image-non-vision`).**
  ```sh
  uv run pytest tests/sdk/llm/test_vision_support.py tests/sdk/llm/test_llm_image_resizing.py tests/sdk/agent/test_non_multimodal_image_input.py -q
  uv run python examples/01_standalone_sdk/17_image_input.py
  ```
  The tests pass; the example describes the python.org icon, writes `image_report.md`, then lists 21 colours from downscaled images.
- **Side questions (`S01.ask-agent`).**
  ```sh
  uv run pytest tests/sdk/conversation/test_ask_agent.py -q
  uv run python examples/01_standalone_sdk/28_ask_agent_example.py
  ```
  The tests pass; the example prints three answers obtained while `run()` is still going and a final answer after it ends.
- **Structured output (`S01.structured-output`).**
  ```sh
  uv run pytest tests/sdk/tool/test_response_schema.py -q
  uv run python examples/01_standalone_sdk/56_structured_output.py
  ```
  35 tests pass; the example prints typed `CommandRationale` objects per terminal call and a `ProjectFacts` instance from `finish`.
- **Error recovery inside a step (`S01.malformed-tool-call`, `S01.unknown-tool`, `S01.tool-exception`, `S01.content-policy`, `S01.context-overflow`).**
  ```sh
  uv run pytest tests/sdk/agent/test_fix_malformed_tool_arguments.py tests/sdk/agent/test_tool_validation_error_message.py tests/sdk/agent/test_nonexistent_tool_handling.py tests/sdk/agent/test_tool_execution_error_handling.py tests/sdk/agent/test_agent_content_policy_violation.py tests/sdk/agent/test_agent_context_window_condensation.py -q
  ```
  The tests pass; each error turns into an event the model sees, or a condensation request, instead of ending the run.
- **Iterative refinement, untested (`S01.iterative-refinement`).** Only the example exercises it.
  ```sh
  MAX_ITERATIONS=2 PHASE_MAX_ITERATIONS=15 uv run python examples/01_standalone_sdk/31_iterative_refinement.py
  ```
  The example converts a sample COBOL file to Java, scores it with a critique conversation, and repeats with feedback until the score reaches `QUALITY_THRESHOLD` (default 90) or `MAX_ITERATIONS`.
- **Real-model task runs (`S01.run-to-finish`, `S01.context-overflow`).** Needs a model key for the integration runner.
  ```sh
  uv run python tests/integration/run_infer.py --llm-config '{"model": "litellm_proxy/anthropic/claude-sonnet-4-5-20250929"}' --eval-ids t01_fix_simple_typo,t02_add_bash_hello
  ```
  Each selected task reports pass/fail in `tests/integration/outputs/`.

## Gotchas

- `01_hello_world.py` is in `_EXCLUDED_EXAMPLES` in `tests/examples/test_examples.py`, so the `test-examples` label never runs it; the other seven examples here do run there (`pytest tests/examples/test_examples.py --run-examples`).
- All examples read `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`; `56_structured_output.py` defaults `LLM_MODEL` to `anthropic/claude-sonnet-4-5-20250929`, the rest to `gpt-5.5`. `17_image_input.py` asserts `llm.vision_is_active()` and fails fast on a text-only model; it also fetches an image from python.org.
- Examples run with the repo root as workspace and write files there (`FACTS.txt`, `image_report.md`, the document from example 18).
- `31_iterative_refinement.py` reads `QUALITY_THRESHOLD`, `MAX_ITERATIONS`, `PHASE_MAX_ITERATIONS`, `COBOL_SAMPLE_LIMIT`; it is several full conversations per iteration and the slowest example here.
- `max_iteration_per_run` counts steps, not tool calls; a parallel batch of tool calls is one step. Hitting the cap is status ERROR, not FINISHED.
- `stuck_detection` is on by default. A test or example that deliberately repeats an action will go STUCK (after one nudge for repeating errors).
- `tool_concurrency_limit > 1` shares the conversation, filesystem and working directory between concurrent tools; races on shared state are the caller's problem unless the tool declares resource keys.
- `ask_agent` copies the agent's LLM with streaming disabled; it is registered in `conversation.llm_registry` under usage id `ask-agent-llm`, so its cost shows up in the conversation stats separately from the agent's.
- Example 18 and 28 run `conversation.run()` in a `threading.Thread`; join the thread before reading final state.
- All pytest commands above passed on 4cc0582 (245 tests in the agent/conversation set, 27 in the status/stuck set).
