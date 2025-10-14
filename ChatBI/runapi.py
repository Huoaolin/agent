from flask import Flask, request, jsonify
from scr.demo import SQLQueryGenerator


app = Flask(__name__)

# 初始化SQL查询生成器
generator = SQLQueryGenerator()


@app.route('/api/query', methods=['POST'])
def query_data():
    try:
        # 获取请求中的查询信息
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({
                'error': '请提供查询信息',
                'status': 'failed'
            }), 400

        query_text = data['query']

        # 生成并执行SQL查询
        result = generator.generate_and_execute_sql(query_text)

        # 返回查询结果
        return jsonify({
            'result': result
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'查询失败: {str(e)}',
            'status': 'failed'
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8004)