from .llm_service import LLMService
import requests
import json
import re


llm = LLMService()


def query_bank_by_sql(sql):
    param = {"queryBankBySQL": sql}
    url = 'http://180.184.80.35:8081/saas/test/queryBankBySQL'
    try:
        # 发送 GET 请求
        response = requests.get(url, params=param)
        # 检查请求是否成功
        response.raise_for_status()
        return response.json()  # 返回响应的 JSON 数据
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None


class SQLQueryGenerator:
    def __init__(self):
        self.llm = LLMService()  # 假设 LLMService 已定义并可用
        self.table_info = """
        ## 表结构信息：
        表名：user_bank_test
        表描述：user_bank_test表是银行储蓄账户表，存储用户的银行信息
        字段列表：
        - user_id：用户唯一标识符，示例：U040, U057, U129
        - name：用户姓名，示例：蔡红, 张三, 李四
        - gender：用户性别，示例：女, 男
        - account_number：10位数字银行账户编码，示例：1468035792, 3289650147
        - account_type：存款账户类型，示例：定期存款, 活期存款
        - opening_date：账户开户日期（YYYY-MM-DD格式），示例：2024-07-15, 2025-03-01
        - current_balance：账户当前余额（保留两位小数），示例：14500.55, 32890.00
        - currency_type：国际标准货币代码，示例：CNY（人民币）, USD（美元）
        - annual_interest_rate：年化利率百分比，示例：1.4%, 2.75%
        - last_transaction_date：最近资金变动日期（YYYY-MM-DD格式），示例：2025-01-15, 2024-12-05
        - status：账户使用状态，示例：活跃, 冻结, 注销
        """

    def generate_and_execute_sql(self, user_input: str) -> dict:
        """
        根据用户输入生成 SQL 查询语句并执行。
        :param user_input: 用户的自然语言描述，例如“查询所有女性用户”
        :return: 查询结果（JSON 格式）或错误信息
        """
        # 构造完整的 prompt
        base_prompt = f"""
        请根据以下信息生成MySQL查询语句：
        用户输入的自然语言描述：
        {user_input}
        {self.table_info}
        ##输出要求：
        只输出查询语句，不做其他额外字符串输出，输出的查询语句格式如下,以```sql字符串开头，以```结尾：
        ```sql
        查询语句
        ```
        ##示例：
        用户输入的自然语言描述：
        “查询所有女性用户”
        输出
        ```sql
        SELECT * FROM user_bank_test WHERE gender=‘女’;
        ```
        """
        answer = self.llm.call(base_prompt)
        sql_string = self.extract_sql(answer)
        repsonse = self.query_bank_by_sql(sql_string)
        return repsonse

    def extract_sql(self, sql_string):
        # 正则表达式提取 SQL 语句
        pattern = r'```sql\n(.*?)\n```'
        match = re.search(pattern, sql_string, re.DOTALL)
        if match:
            return match.group(1).strip()  # 返回提取的 SQL 语句并去除前后空白
        else:
            return None  # 若未找到则返回 None

    def query_bank_by_sql(self, sql: str) -> dict:
        param = {"queryBankBySQL": sql}
        url = 'http://180.184.80.35:8081/saas/test/queryBankBySQL'
        try:
            response = requests.get(url, params=param)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            return None