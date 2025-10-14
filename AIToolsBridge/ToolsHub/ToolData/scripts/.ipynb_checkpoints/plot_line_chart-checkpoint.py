import sys
import json
import pandas as pd
import matplotlib.pyplot as plt


def plot_line_chart(data: dict, output_path: str) -> dict:
    """
    根据输入的 JSON 数据绘制折线图，并保存为 PNG 文件。

    :param data: 包含绘图数据的字典，格式为 {"x": [x1, x2, ...], "y": [y1, y2, ...], "title": "图表标题"}
    :param output_path: 图表保存路径（包括文件名，如 "output/chart.png"）
    :return: 返回操作结果，格式为 {"status": "success"} 或 {"error": "错误信息"}
    """
    try:
        # 将输入数据转换为 DataFrame
        df = pd.DataFrame(data)

        # 绘制折线图
        df.plot(x='x', y='y', kind='line', title=data.get("title", "折线图"))

        # 保存图表为 PNG 文件
        plt.savefig(output_path)
        plt.close()  # 关闭图表，避免内存泄漏

        return {"status": "success", "output_path": output_path}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # 从命令行参数中获取输入
    try:
        # 解析 JSON 格式的输入
        input_data = json.loads(sys.argv[1])
        # output_path = sys.argv[2]  # 图表保存路径
        output_path = input_data.get("output_path")
        
        # 调用绘图函数
        result = plot_line_chart(input_data, output_path)

        # 返回结果
        print(json.dumps(result))
    except Exception as e:
        # 处理错误
        error_result = {"error": str(e)}
        print(json.dumps(error_result))