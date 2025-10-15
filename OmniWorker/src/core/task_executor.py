from __future__ import annotations

import json
import os
import re
import time
import uuid
from typing import Dict, Iterator, List

from ..core.interaction_handler import InteractionHandler
from ..core.step_recorder import StepRecorder
from ..services.llm_service import LLMService
from AIToolsBridge.core.ToolAgent import ToolAgent


class MockLogger:
    """Simple file-backed logger used during offline demos."""

    def __init__(self, log_file: str) -> None:
        self.log_file = log_file
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def error(self, message: str) -> None:
        print(f"[ERROR] {message}")
        with open(self.log_file, "a", encoding="utf-8") as handle:
            handle.write(f"[ERROR] {message}\n")

    def info(self, message: str) -> None:
        print(f"[INFO] {message}")
        with open(self.log_file, "a", encoding="utf-8") as handle:
            handle.write(f"[INFO] {message}\n")


class TaskExecutor:
    """Execute planned steps and stream intermediate results."""

    TOOL_KEYWORDS = ["工具", "tool", "调用", "api", "查询", "download", "写入", "保存"]

    def __init__(
        self,
        logger,
        step_recorder: StepRecorder | None,
        interaction_handler: InteractionHandler,
        *,
        max_steps: int = 20,
        llm: LLMService | None = None,
        tool_agent: ToolAgent | None = None,
    ) -> None:
        self.agent = tool_agent or ToolAgent(parser_type=os.getenv("TOOL_AGENT_PARSER", "rule_based"))
        self.job_id = str(uuid.uuid4())
        log_file_path = os.path.join("tasks", self.job_id, "task_steps.log")
        self.logger = logger or MockLogger(log_file_path)

        self.llm = llm or LLMService()
        self.interaction_handler = interaction_handler
        self.max_steps = max_steps
        self.step_count = 0

        self.step_recorder = step_recorder or StepRecorder(self.job_id)
        self.logger.info(f"Generated job_id: {self.job_id}")
        self.logger.info(f"Registered tools: {self.agent.list_tools()}")

    # ------------------------------------------------------------------
    # Core execution logic
    # ------------------------------------------------------------------
    def execute(self, steps: List[str], state: Dict) -> Iterator[str]:
        """Yield JSON strings describing progress for every step."""

        results = state.setdefault("results", {})
        current_step = state.get("current_step", 0)

        for idx, step in enumerate(steps[current_step:], start=current_step):
            if self.step_count >= self.max_steps:
                error_msg = f"已达到最大步骤限制 {self.max_steps}，任务中止"
                self.logger.error(error_msg)
                yield json.dumps({"error": error_msg, "step_index": idx, "step": step, "results": results}, ensure_ascii=False)
                return

            step_result = self._execute_single_step(step, results)
            self.step_count += 1

            state["current_step"] = idx + 1
            results[f"step_{idx + 1}"] = step_result
            state["results"] = results

            self.step_recorder.record(step, step_result)

            payload = {
                "step_index": idx,
                "step": step,
                "result": step_result,
                "results": results,
            }
            yield json.dumps(payload, ensure_ascii=False)

            steps = self.adjust_steps_based_on_result(steps, idx, step, step_result, results)
            steps, interrupted = self._handle_user_interaction(step, step_result, steps, idx, results)
            if interrupted:
                state["steps"] = steps
                break

        final_summary = self._summarise_results(results, state.get("query"))
        yield json.dumps({"final_result": final_summary, "results": results}, ensure_ascii=False)

    def _execute_single_step(self, step: str, previous_results: Dict) -> str:
        if self._needs_tool(step):
            result = self._execute_tool_step(step, previous_results)
        else:
            result = self._execute_direct_step(step, previous_results)
        self.logger.info(f"完成: {step} 结果: {result}")
        return result

    def _needs_tool(self, step: str) -> bool:
        step_lower = step.lower()
        return any(keyword in step_lower for keyword in self.TOOL_KEYWORDS)

    def _execute_direct_step(self, step: str, previous_results: Dict) -> str:
        known_keys = ", ".join(previous_results.keys()) if previous_results else "暂无上下文"
        return f"已根据现有信息完成步骤：{step}。参考上下文：{known_keys}"

    def _execute_tool_step(self, step: str, previous_results: Dict) -> str:
        print("  ****  尝试调用使用工具")
        try:
            start_time = time.time()
            query_with_context = (
                f"Job ID: {self.job_id}\n"
                f"已有结果：{json.dumps(previous_results, ensure_ascii=False)}\n"
                f"执行步骤：{step}"
            )
            result = self.agent.process_query(query_with_context)
            print(f"完成: {step} [耗时: {time.time() - start_time:.2f}s]")
            return self._normalise_tool_payload(result)
        except Exception as exc:
            self.logger.error(f"ToolAgent 执行失败: {exc}")
            return "工具执行失败"

    def _normalise_tool_payload(self, payload) -> str:
        if isinstance(payload, (dict, list)):
            try:
                return json.dumps(payload, ensure_ascii=False)
            except TypeError:
                pass
        return str(payload)

    def extract_json_list(self, raw_result: str) -> str:
        pattern = r"\{.*?\}"
        matches = re.findall(pattern, raw_result, re.DOTALL)
        if matches:
            candidate = matches[0]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                self.logger.error(f"提取的内容不是有效 JSON: {candidate}")
        else:
            self.logger.error(f"未能在 LLM 输出中提取 JSON 对象: {raw_result}")
        return json.dumps({})

    def _handle_user_interaction(self, step: str, result: str, steps: List[str], current_idx: int, previous_results: Dict):
        interrupt, new_input = self.interaction_handler.check_interaction(step, result)
        if interrupt:
            self.logger.info(f"用户中断任务，输入调整: {new_input}")
            adjusted_steps = self.adjust_steps(steps, current_idx, new_input, previous_results)
            return adjusted_steps, True
        return steps, False

    def adjust_steps(self, steps: List[str], current_idx: int, new_input: str, previous_results: Dict) -> List[str]:
        prompt = (
            f"基于以下已有结果：{json.dumps(previous_results, ensure_ascii=False)}\n"
            f"根据新输入 '{new_input}' 调整后续步骤: {steps[current_idx:]}"
        )
        return [item.strip() for item in self.llm.call(prompt).split("\n") if item.strip()]

    def adjust_steps_based_on_result(self, steps: List[str], current_idx: int, step: str, step_result: str, previous_results: Dict) -> List[str]:
        judge_prompt = (
            "根据以下信息，判断当前步骤的结果是否需要调整后续步骤。\n"
            f"当前步骤: '{step}'\n"
            f"当前步骤结果: '{step_result}'\n"
            f"已有结果: {json.dumps(previous_results, ensure_ascii=False)}\n"
            f"后续步骤: {json.dumps(steps[current_idx + 1:], ensure_ascii=False)}\n"
            "Guidelines:\n"
            "- 如果当前步骤结果表明后续步骤无法继续执行，返回 JSON {'adjust_needed': true}。\n"
            "- 如果当前步骤结果正常且后续步骤可以继续执行，返回 JSON {'adjust_needed': false}。\n"
            "- 返回结果必须是有效的 JSON 格式。\n"
        )

        judge_response = self.llm.call(judge_prompt)
        judge_json = self.extract_json_list(judge_response)
        try:
            judge_result = json.loads(judge_json)
            adjust_needed = judge_result.get("adjust_needed", False)
        except (json.JSONDecodeError, KeyError):
            self.logger.error(f"无法解析 LLM 判断结果: {judge_json}，默认需要调整")
            adjust_needed = True

        if adjust_needed:
            self.logger.info(f"根据步骤结果 '{step_result}' 调整后续步骤")
            adjust_prompt = (
                f"基于以下信息调整后续步骤：\n"
                f"当前步骤: '{step}'\n"
                f"当前步骤结果: '{step_result}'\n"
                f"已有结果: {json.dumps(previous_results, ensure_ascii=False)}\n"
                f"需要调整的后续步骤: {json.dumps(steps[current_idx + 1:], ensure_ascii=False)}\n"
                "请返回调整后的步骤列表，按行分隔，每行一个步骤。"
            )
            new_steps_response = self.llm.call(adjust_prompt)
            adjusted_steps = [s.strip() for s in new_steps_response.split("\n") if s.strip()]
            return steps[: current_idx + 1] + adjusted_steps
        self.logger.info("无需调整后续步骤")
        return steps

    def _summarise_results(self, results: Dict, query: str | None) -> str:
        ordered = [f"{key}: {value}" for key, value in results.items()]
        summary_lines = ["任务执行完成。", f"原始需求: {query or '未知'}"] + ordered
        return "\n".join(summary_lines)

