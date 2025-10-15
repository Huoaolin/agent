# OmniWorker Agent Architecture Overview

This document summarises how the offline-first OmniWorker stack receives a user
query, plans work, invokes tools, and records results.  It highlights the memory
flow and the dedicated components that let us exercise prompt-injection
scenarios.

## High-level Component Graph

```mermaid
graph TD
    U[User / UI] -->|自然语言查询| IP[InputProcessor]
    IP -->|粗略&细化步骤| TP[TaskPlanner]
    TP -->|步骤列表| TE[TaskExecutor]
    TE -->|状态上下文| SM[(Execution State)]
    TE -->|记录| SR[StepRecorder]
    TE -->|LLM 调整| LLM[LLMService]
    TE -->|工具查询| TA[ToolAgent]
    TA -->|工具元数据| TR[ToolRegistry]
    TA -->|参数规范| PH[ParamHandler]
    TA -->|执行| EX[ToolExecutor]
    EX -->|HTTP/API| API[攻击接口 (例如 hijack_app)]
    EX -->|本地脚本/文件| Local[其它执行器]
    SR -->|任务日志| Files[(tasks/<job_id>)]
    TE -->|人工干预| IH[InteractionHandler]
    IH -->|新输入| TE
```

## Stage-by-stage Flow

1. **Input understanding** – `InputProcessor` sends the raw query through
   `LLMService` twice to obtain coarse and refined Chinese step lists.  It also
   normalises LLM JSON output so downstream modules always receive a Python
   list.【F:OmniWorker/src/core/input_processor.py†L1-L91】
2. **Planning** – `TaskPlanner` takes the refined steps and re-prompts the LLM
   to enforce a flat, numbered plan (≤13 steps) that becomes the execution
   blueprint.【F:OmniWorker/src/core/task_planner.py†L16-L53】
3. **Execution loop** – `TaskExecutor` creates a `job_id`, wires up
   `StepRecorder`, and iterates over planned steps.  Each iteration decides
   whether a tool is needed, executes it, records results, allows interactive
   overrides, and can request re-planning via the LLM stub.【F:OmniWorker/src/core/task_executor.py†L34-L173】
4. **Interaction & memory** – The executor keeps incremental state (current
   index, `results` dict) while `StepRecorder` appends JSON lines into
   `tasks/<job_id>/task_steps.log`, providing an auditable memory stream that
   the UI polls.【F:OmniWorker/src/core/task_executor.py†L71-L120】【F:OmniWorker/src/core/step_recorder.py†L1-L40】
5. **Tool orchestration** – When tool keywords appear, the executor asks
   `ToolAgent` to resolve the request.  The agent selects a tool via
   `ToolRegistry`, validates parameters with `ParamHandler`, and dispatches to a
   concrete executor such as the HTTP-based `ApiExecutor`.  Responses return to
   the executor as strings/JSON for logging.【F:AIToolsBridge/core/ToolAgent.py†L12-L90】【F:AIToolsBridge/ToolsHub/tools/registry.py†L1-L88】【F:AIToolsBridge/ToolsExecute/services/param_handler.py†L1-L77】【F:AIToolsBridge/ToolsExecute/services/tool_executor.py†L1-L47】【F:AIToolsBridge/ToolsExecute/executors/api_executor.py†L1-L33】
6. **Prompt-injection surface** – The included hijack server (`api_demo/
   hijack_app.py`) and the automated demo spin up an API that returns malicious
   instructions.  Because `TaskExecutor` streams tool results verbatim, the
   injected payload appears in the log and can influence subsequent re-planning
   if the LLM honours it, enabling controlled attack experiments.【F:api_demo/hijack_app.py†L15-L53】【F:attack_demo.py†L32-L91】

## Memory & State Layers

- **Execution state (`state` dict)** – Tracks current step index, accumulated
  results, and the plan, enabling resumable execution and dynamic adjustments by
  the executor.【F:OmniWorker/src/core/task_executor.py†L71-L119】
- **Persistent trace (`StepRecorder`)** – Persists timestamped JSON entries to
  disk under the job ID, which the Gradio UI and test scripts surface to users
  while attacks unfold.【F:OmniWorker/src/core/step_recorder.py†L1-L40】【F:app.py†L27-L69】
- **Tool metadata store (`tools.json`)** – Defines available tools and their
  parameters, including the stock API that houses the malicious payload, so the
  agent can be steered toward the exploit path during tests.【F:AIToolsBridge/ToolsHub/ToolData/tools.json†L1-L45】【F:AIToolsBridge/ToolsHub/ToolData/tools.json†L45-L77】

## Attack Demonstration Flow

1. `attack_demo.py` launches a local HTTP server that mimics the hijack API and
   prepares a 3-step plan forcing the executor to call
   `query_stock_information`.【F:attack_demo.py†L32-L78】
2. The executor detects the tool keyword, routes the call through the agent, and
   receives the malicious instructions embedded in the API response.  The result
   is recorded and printed, showcasing how indirect prompt injection propagates
   through the pipeline.【F:attack_demo.py†L63-L91】【F:OmniWorker/src/core/task_executor.py†L102-L149】
