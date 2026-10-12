# Critic and critic-driven refinement

A Python program passes `Agent(critic=...)` and the agent scores its own work while it runs: in the default `finish_and_message` mode the critic evaluates the event history whenever the agent emits a `FinishAction` or a plain agent message, and in `all_actions` mode after every action. The result, a `CriticResult` with a 0 to 1 `score`, a `message` and optional `metadata`, is attached to the emitted `ActionEvent` or `MessageEvent` as `critic_result` and rendered by the visualizer as stars and categorized features. With `critic.iterative_refinement=IterativeRefinementConfig(success_threshold, max_iterations)`, a `FinishAction` whose critic result is below the threshold (or, for `APIBasedCritic`, shows a high-probability agent issue) does not finish the conversation: `Conversation.run()` injects a user follow-up prompt and keeps going, counting refinements in `state.agent_state["iterative_refinement_iteration"]` until the score passes or `max_iterations` is reached. Built-in critics: `APIBasedCritic` (a remote classifier service), `AgentFinishedCritic`, `EmptyPatchCritic` and `PassCritic` (deterministic). `OpenHandsAgentSettings.verification` builds an `APIBasedCritic` from settings.

Source: `openhands-sdk/openhands/sdk/critic/`, `openhands-sdk/openhands/sdk/agent/critic_mixin.py`, `openhands-sdk/openhands/sdk/agent/agent.py`, `openhands-sdk/openhands/sdk/agent/response_dispatch.py`, `openhands-sdk/openhands/sdk/event/llm_convertible/action.py`, `openhands-sdk/openhands/sdk/event/llm_convertible/message.py`, `openhands-sdk/openhands/sdk/settings/model.py`

Needs: `llm`, `network`

Examples: `examples/01_standalone_sdk/34_critic_example.py`

## Sub-features

- `S12.critic-result`: `CriticResult(score, message, metadata)` validates `score` in [0, 1]; `success` is `score >= 0.5`. Unit: `tests/sdk/critic/test_critic.py::test_critic_result_success_threshold`, `::test_critic_result_validation`. Example: none. Real-LLM: none.
- `S12.critic-display`: `CriticResult.visualize` renders a star rating with colors, the JSON probability message sorted, and categorized features above the display threshold. Unit: `tests/sdk/critic/test_critic_display.py`. Example: `examples/01_standalone_sdk/34_critic_example.py`. Real-LLM: none.
- `S12.rule-critics`: `PassCritic` always scores 1.0; `EmptyPatchCritic` scores 0.0 for an empty or missing `git_patch`; `AgentFinishedCritic` needs both a non-empty patch and a last `ActionEvent` that is a `FinishAction`; `CriticBase` is abstract. Unit: `tests/sdk/critic/test_critic.py`. Example: none. Real-LLM: none.
- `S12.eval-mode`: `mode="finish_and_message"` evaluates on `FinishAction` (and on agent `MessageEvent`s in the response path), `mode="all_actions"` on every action, no critic on nothing. Unit: `tests/sdk/agent/test_iterative_refinement.py::TestShouldEvaluateWithCritic`. Example: none. Real-LLM: none.
- `S12.result-on-events`: during a run the critic result lands on the emitted `ActionEvent.critic_result` / `MessageEvent.critic_result`; a critic exception is logged and the event is emitted without a result. Unit: **none (untested)** (only the decision function above is tested; no test runs `Agent.step` with a critic). Example: `examples/01_standalone_sdk/34_critic_example.py`. Real-LLM: none.
- `S12.refinement-config`: `IterativeRefinementConfig` defaults to `success_threshold=0.6`, `max_iterations=3`, and rejects a threshold outside [0, 1] or `max_iterations < 1`. Unit: `tests/sdk/agent/test_iterative_refinement.py::TestIterativeRefinementConfig`. Example: none. Real-LLM: none.
- `S12.refinement-decision`: after a `FinishAction` the agent continues only when a critic and refinement config exist, the finish carries a critic result, `should_refine` is true and the counter is below `max_iterations`; a score at the threshold stops; the counter in `agent_state` increments only when refinement continues. Unit: `tests/sdk/agent/test_iterative_refinement.py::TestCheckIterativeRefinement`. Example: `examples/01_standalone_sdk/34_critic_example.py`. Real-LLM: none.
- `S12.refinement-followup`: when refinement continues, the action batch emits a `MessageEvent(source="user")` with the critic's follow-up prompt instead of marking the conversation FINISHED; a finish blocked by a hook is not finalized. Unit: `tests/sdk/agent/test_action_batch.py::test_finalize_emits_followup_on_refinement`, `::test_finalize_marks_finished`, `::test_finalize_noop_when_finish_blocked`. Example: `examples/01_standalone_sdk/34_critic_example.py`. Real-LLM: none.
- `S12.custom-refine-policy`: subclasses override `should_refine` and `get_followup_prompt`; `APIBasedCritic.should_refine` also refines when an agent behavioral issue has probability at or above `issue_threshold` (0.75), even if the score meets the threshold. Unit: `tests/sdk/agent/test_iterative_refinement.py::TestCheckIterativeRefinement::test_high_probability_issue_continues_even_when_score_meets_threshold`. Example: `examples/01_standalone_sdk/34_critic_example.py` (`SingleRefinementCritic`). Real-LLM: none.
- `S12.api-followup-prompt`: `APIBasedCritic.get_followup_prompt` lists agent issues, predicted user follow-ups, infrastructure issues and other observations with probabilities. Unit: **none (untested)**. Example: `examples/01_standalone_sdk/34_critic_example.py`. Real-LLM: none.
- `S12.api-evaluate`: `APIBasedCritic.evaluate` requires a `SystemPromptEvent` with tools, condenses the history through `View`, renders it with the Qwen chat template, POSTs `{server_url}/classify` with a bearer key (retrying HTTP 500 up to 3 times), and returns `score = probs["success"]` with `event_ids` and `categorized_features` metadata. Unit: **none (untested)** (no test mocks `/classify`). Example: `examples/01_standalone_sdk/34_critic_example.py`. Real-LLM: none.
- `S12.chat-template`: `ChatTemplateRenderer` reproduces the `transformers` rendering of the Qwen3 template, tools included. Unit: `tests/sdk/critic/api/test_template_render.py`. Example: none. Real-LLM: none.
- `S12.api-key-handling`: `APIBasedCritic.api_key` accepts `str` or `SecretStr`, treats empty and whitespace keys and the redacted placeholder as missing, refuses inference without a key, hides the key in `repr` and dumps, and exposes or encrypts it only with an expose or cipher context, also when nested in a dumped `Agent`. Unit: `tests/sdk/critic/test_critic_client.py`. Example: none. Real-LLM: none.
- `S12.settings-critic`: `OpenHandsAgentSettings.verification` (`critic_enabled`, `critic_mode`, `enable_iterative_refinement`, `critic_threshold`, `max_refinement_iterations`, `critic_server_url`, `critic_model_name`, `critic_api_key`) builds an `APIBasedCritic` in `create_agent()`, falls back to the LLM key, and builds none without any key. Unit: `tests/sdk/test_settings.py` (`test_llm_create_agent_*critic*`, `test_verification_settings_critic_api_key_roundtrip`). Example: none. Real-LLM: none.
- `S12.end-to-end-refinement`: a live run with a critic below threshold performs exactly the configured number of refinements and still finishes. Unit: **none (untested)**. Example: `examples/01_standalone_sdk/34_critic_example.py`. Real-LLM: none (only via the example on the `test-examples` label).

## How to get to it (agent POV)

- `Agent(llm=..., tools=..., critic=APIBasedCritic(server_url=..., api_key=..., model_name=..., mode=..., iterative_refinement=IterativeRefinementConfig(...)))`; imports from `openhands.sdk.critic`. Covers `S12.eval-mode`, `S12.result-on-events`, `S12.refinement-*`, `S12.api-*`.
- `PassCritic()`, `EmptyPatchCritic()`, `AgentFinishedCritic()`: call `.evaluate(events, git_patch=...)` directly; they are useful offline or in evaluation harnesses (`S12.rule-critics`).
- Subclass `CriticBase` (implement `evaluate`) or `APIBasedCritic` (override `should_refine` / `get_followup_prompt`) (`S12.custom-refine-policy`).
- Read the outcome: `event.critic_result` on `ActionEvent`/`MessageEvent` in `conversation.state.events`; `conversation.state.agent_state[ITERATIVE_REFINEMENT_ITERATION_KEY]` (`openhands.sdk.agent.critic_mixin`).
- `OpenHandsAgentSettings(llm=..., verification=VerificationSettings(critic_enabled=True, ...)).create_agent()` (`S12.settings-critic`).
- Defaults: `server_url="https://llm-proxy.app.all-hands.dev/vllm"`, `model_name="critic"`, `tokenizer_name="Qwen/Qwen3-4B-Instruct-2507"`, `timeout_seconds=300`.

## Driving it

Preconditions:
- `uv sync --dev` has run.
- For the example: `LLM_API_KEY` (and `LLM_MODEL`, `LLM_BASE_URL`), and either an All-Hands proxy `LLM_BASE_URL` matching `llm-proxy.<env>.all-hands.dev` or `CRITIC_SERVER_URL`, `CRITIC_API_KEY`, `CRITIC_MODEL_NAME`.

- **Critic results, display, rule critics, API key handling, chat template (`S12.critic-result`, `S12.critic-display`, `S12.rule-critics`, `S12.api-key-handling`, `S12.chat-template`).**
  ```sh
  uv run pytest tests/sdk/critic -q
  ```
  All tests pass offline (the template test reads a fixture tokenizer config).
- **Evaluation mode and refinement decision (`S12.eval-mode`, `S12.refinement-config`, `S12.refinement-decision`, `S12.custom-refine-policy`, `S12.refinement-followup`).**
  ```sh
  uv run pytest tests/sdk/agent/test_iterative_refinement.py tests/sdk/agent/test_action_batch.py -q
  ```
  The tests pass; `test_finalize_emits_followup_on_refinement` shows the follow-up user message.
- **Critic from settings (`S12.settings-critic`).**
  ```sh
  uv run pytest tests/sdk/test_settings.py -q -k critic
  ```
  7 tests pass.
- **Live critic-driven refinement (`S12.result-on-events`, `S12.api-evaluate`, `S12.api-followup-prompt`, `S12.end-to-end-refinement`), untested, blocked without a critic service.** Needs a real LLM and a reachable critic endpoint.
  ```sh
  uv run python examples/01_standalone_sdk/34_critic_example.py
  ```
  The script raises unless the conversation FINISHES, `greeting.txt` matches, and exactly one refinement was recorded; it prints `Completed 1 critic-driven refinement.` and `EXAMPLE_COST`.

## Gotchas

- Example 34 raises `ValueError` at start if neither the All-Hands proxy base URL nor all three `CRITIC_*` env vars are set. Its `SingleRefinementCritic` forces `should_refine=True`, so the refinement count is deterministic regardless of score.
- `APIBasedCritic` downloads `tokenizer_config.json` for `tokenizer_name` from `huggingface.co` on first use and caches it in `~/.cache/chat_templates/`; without network and without that cache, evaluation fails, the error is logged and `critic_result` stays `None` (the run continues, so refinement silently never triggers).
- Without `iterative_refinement` the critic only annotates events; it never changes control flow.
- Refinement is checked only for a `FinishAction`; an agent that ends with a plain message gets a `critic_result` on the `MessageEvent` but no follow-up.
- `CriticResult.success` uses a fixed 0.5 threshold, independent of `IterativeRefinementConfig.success_threshold` (default 0.6).
- `mode="all_actions"` makes one HTTP call per action and is much slower.
- Example 31 (`31_iterative_refinement.py`) is a user-written refinement loop with a second LLM, not the critic; example 54 (goal completion loop) is a separate mechanism in `conversation/goal/`. Neither belongs here.
- `34_critic_example.py` is not in `_EXCLUDED_EXAMPLES`, so it runs on the `test-examples` label and needs the critic credentials there.
