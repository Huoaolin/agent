"""Minimal Gradio UI for driving the OmniWorker agent offline."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Tuple

import gradio as gr

from OmniWorker.src.core.input_processor import InputProcessor
from OmniWorker.src.core.interaction_handler import InteractionHandler
from OmniWorker.src.core.task_executor import TaskExecutor
from OmniWorker.src.core.task_planner import TaskPlanner


TASK_ROOT = Path("tasks")


def _read_log(path: Path) -> str:
    """Return the current contents of ``path`` if it exists."""

    if not path.exists():
        return "loading..."
    return path.read_text(encoding="utf-8").strip()


def process_query(query: str) -> Tuple[str, str, str]:
    """Parse, plan, and kick off asynchronous execution for ``query``."""

    processor = InputProcessor()
    coarse_steps = processor.process(query)

    planner = TaskPlanner()
    planned_steps = planner.plan(query, coarse_steps)

    interaction_handler = InteractionHandler()
    executor = TaskExecutor(logger=None, step_recorder=None, interaction_handler=interaction_handler)

    task_dir = TASK_ROOT / executor.job_id
    log_file = task_dir / "task_steps.log"
    task_dir.mkdir(parents=True, exist_ok=True)

    state = {"current_step": 0, "results": {}, "steps": planned_steps, "query": query}

    def run_executor() -> None:
        for payload in executor.execute(planned_steps, state):
            (task_dir / "results.json").write_text(payload, encoding="utf-8")
            message = json.loads(payload)
            if "final_result" in message:
                report = "# 任务报告\n" + message["final_result"]
                (task_dir / "final_report.md").write_text(report, encoding="utf-8")

    thread = threading.Thread(target=run_executor, daemon=True)
    thread.start()

    return str(log_file), "\n".join(planned_steps), str(task_dir)


def poll_log(log_path: str, task_dir: str):
    """Periodically called by Gradio to fetch new log output."""

    if not log_path or not task_dir:
        return "loading...", None

    log_file = Path(log_path)
    directory = Path(task_dir)

    full_log = _read_log(log_file)
    markdown_files = sorted(directory.glob("*.md"))
    return full_log, (str(markdown_files[0]) if markdown_files else None)


def create_interface() -> gr.Blocks:
    with gr.Blocks(title="任务处理与文件下载") as demo:
        with gr.Row():
            input_text = gr.Textbox(label="请输入任务（例如：生成国产电动汽车分析报告）")
            submit_btn = gr.Button("提交")

        with gr.Row():
            output_text = gr.Textbox(label="任务执行日志", lines=10, max_lines=20)
            steps_text = gr.Textbox(label="任务步骤", lines=10, max_lines=20)

        download_file = gr.File(label="下载结果文件")

        log_state = gr.State(value="")
        task_state = gr.State(value="")

        submit_btn.click(
            fn=process_query,
            inputs=[input_text],
            outputs=[log_state, steps_text, task_state],
        ).then(
            fn=poll_log,
            inputs=[log_state, task_state],
            outputs=[output_text, download_file],
            every=1,
        )

    return demo


if __name__ == "__main__":
    create_interface().launch(server_name="0.0.0.0", server_port=7862, debug=True)
