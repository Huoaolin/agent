# tools/scripts/write_markdown.py

import sys
import json
import os

def write_markdown(input_data) -> str:
    """
    将 Markdown 内容写入文件并返回文件路径

    :param input_data: 输入的字典，包含 'jobID'（任务 ID）和可选的 'content'（Markdown 内容）
    :return: 文件路径或提示信息
    """
    job_id = input_data.get("jobID", "")
    if not job_id:
        raise ValueError("jobID is required")
    output_path = os.path.join("tasks", job_id, "report.md")
    content = input_data.get("input", None)

    if not content:
        markdown_string = """
# 这是一个标题
这是一个段落，包含一些 **加粗文本** 和 *斜体文本*。

- 列表项 1
- 列表项 2
- 列表项 3
"""
    else:
        markdown_string = content

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "a", encoding="utf-8") as file:
        file.write(markdown_string)

    return output_path

if __name__ == "__main__":
    try:
        input_data = json.loads(sys.argv[1])
        print("******DEBUG*******")
        print("******DEBUG*******")
        print("input_data", input_data)
        print("******DEBUG*******")
        print("******DEBUG*******")
        out = write_markdown(input_data)
        result = {"result": f"已将 Markdown 内容写入到 {out}"}
        # 设置 ensure_ascii=False，避免中文转义
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        error_result = {"error": str(e)}
        print(json.dumps(error_result, ensure_ascii=False))