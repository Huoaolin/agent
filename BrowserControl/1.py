# # import asyncio
# # from src.agent import Agent

# # async def main():
# #     user_inputs = [
# #         "我要找 Tesla Model 3 的价格",
# #         "我想了解 iPhone 15 和 Galaxy S23 的信息",
# #         "我要某产品的截图"
# #     ]
# #     for user_input in user_inputs:
# #         print(f"\n处理输入: {user_input}")
# #         agent = Agent(user_input)
# #         results = await agent.run()
# #         print("结果:", results)

# # if __name__ == "__main__":
# #     asyncio.run(main())


# import asyncio
# import os
# import sys

# # 将项目路径添加到 sys.path，确保模块可以正确导入
# sys.path.append(os.path.abspath("./BrowseControl/src"))

# from src.agent import Agent

# async def main():
#     # 定义用户输入列表
#     user_inputs = [
#         "我要找 Tesla Model 3 的价格",
#         "我想了解 iPhone 15 和 Galaxy S23 的信息",
#         "我要某产品的截图"
#     ]

#     # 遍历每个用户输入并处理
#     for user_input in user_inputs:
#         print(f"\n处理输入: {user_input}")
#         # 实例化 Agent 并传入 user_input
#         agent = Agent(user_input)
#         # 运行任务并获取结果
#         results = await agent.run()
#         print("结果:", results)

# if __name__ == "__main__":
#     # 运行异步 main 函数
#     asyncio.run(main())