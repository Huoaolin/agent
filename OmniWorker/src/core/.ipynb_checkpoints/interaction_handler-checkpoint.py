class InteractionHandler:
    def __init__(self):
        """
        初始化交互处理器。
        """
        pass

    def check_interaction(self, step: str, result: str) -> tuple[bool, str]:
        """
        检查用户是否需要中断任务并提供新输入。

        :param step: 当前步骤的描述。
        :param result: 当前步骤的执行结果。
        :return: 返回一个元组 (是否需要中断, 用户新输入)。
        """
        # 示例逻辑：模拟用户中断
        if "失败" in result:
            print(f"步骤 '{step}' 执行失败，是否需要调整？")
            new_input = input("请输入调整内容（或按回车继续）：")
            if new_input.strip():
                return True, new_input
        return False, ""

    def prompt_user(self, message: str) -> str:
        """
        提示用户输入。

        :param message: 提示信息。
        :return: 用户输入的内容。
        """
        return input(message)