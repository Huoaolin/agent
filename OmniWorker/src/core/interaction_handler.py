class InteractionHandler:
    def __init__(self, interactive: bool = False, input_func=None):
        """管理任务执行过程中的人工干预。

        历史实现会在每次步骤结果包含“失败”时直接调用 ``input()``，这会
        让自动化测试或无头环境永久阻塞。 现在允许通过 ``interactive``
        开关来选择是否启用人工干预，默认关闭，从而保证流水线可以在
        离线环境下顺畅运行。如需人工接入，可在初始化时传入
        ``interactive=True`` 以及自定义 ``input_func``。
        """

        self.interactive = interactive
        self._input = input_func or input

    def check_interaction(self, step: str, result: str) -> tuple[bool, str]:
        """
        检查用户是否需要中断任务并提供新输入。

        :param step: 当前步骤的描述。
        :param result: 当前步骤的执行结果。
        :return: 返回一个元组 (是否需要中断, 用户新输入)。
        """
        # 示例逻辑：模拟用户中断
        if self.interactive and "失败" in result:
            print(f"步骤 '{step}' 执行失败，是否需要调整？")
            new_input = self._input("请输入调整内容（或按回车继续）：")
            if new_input.strip():
                return True, new_input
        return False, ""

    def prompt_user(self, message: str) -> str:
        """
        提示用户输入。

        :param message: 提示信息。
        :return: 用户输入的内容。
        """
        if not self.interactive:
            return ""
        return self._input(message)