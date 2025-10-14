from flask import Flask, request, jsonify
import tushare as ts
from typing import List, Optional
import pandas as pd

# 初始化 Flask 应用
app = Flask(__name__)

# 初始化 Tushare API
api_key = "c4ac6d72013888e05c812ae6776db5671fa0bdd2bdacfda6aba0d589"  # 替换为你的 Tushare API 密钥
ts.set_token(api_key)
pro = ts.pro_api()

class StockDataFetcher:
    @staticmethod
    def get_stock_data(
        stock_codes: List[str],
        start_date: str = "20230101",  # 默认开始日期
        end_date: str = "20230131",    # 默认结束日期
        fields: Optional[List[str]] = ["ts_code", "trade_date", "open", "close"],  # 默认字段
    ) -> pd.DataFrame:
        """
        获取指定股票代码在指定日期范围内的日线数据。

        :param stock_codes: 股票代码列表（例如 ['000001.SZ', '600000.SH']）。
        :param start_date: 开始日期（格式：'YYYYMMDD'），默认为 '20230101'。
        :param end_date: 结束日期（格式：'YYYYMMDD'），默认为 '20230131'。
        :param fields: 需要返回的字段列表（可选），默认为 ["ts_code", "trade_date", "open", "close"]。
        :return: 包含股票数据的 DataFrame。
        """
        # 将股票代码列表转换为逗号分隔的字符串
        ts_codes = ",".join(stock_codes)

        # 获取数据
        df = pro.daily(ts_code=ts_codes, start_date=start_date, end_date=end_date)

        # 如果指定了字段，则过滤 DataFrame
        if fields:
            df = df[fields]

        return df

@app.route('/stock-data', methods=['POST'])
def get_stock_data():
    """
    获取股票数据 API
    请求体格式：
    {
        "stock_codes": ["000001.SZ", "600000.SH"],  # 股票代码列表
        "start_date": "20230101",  # 开始日期（格式：YYYYMMDD，可选）
        "end_date": "20230131",    # 结束日期（格式：YYYYMMDD，可选）
        "fields": ["ts_code", "trade_date", "open", "close"]  # 可选字段列表
    }
    """
    # 获取请求体中的 JSON 数据
    data = request.get_json()

    # 检查必要字段
    if not data or 'stock_codes' not in data:
        return jsonify({"error": "Missing required field: 'stock_codes'"}), 400

    try:
        # 调用 StockDataFetcher 获取数据
        stock_codes = data['stock_codes']
        start_date = data.get('start_date', "20230101")  # 默认开始日期
        end_date = data.get('end_date', "20230131")      # 默认结束日期
        fields = data.get('fields', ["ts_code", "trade_date", "open", "close"])  # 默认字段

        df = StockDataFetcher.get_stock_data(stock_codes, start_date, end_date, fields)

        # 将 DataFrame 转换为 JSON 格式
        result = df.to_dict(orient='records')
        return jsonify({"data": result})
    except Exception as e:
        # 处理错误
        return jsonify({"error": str(e)}), 500


# 启动 Flask 应用
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8003)