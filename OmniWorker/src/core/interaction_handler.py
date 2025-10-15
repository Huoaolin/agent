class InteractionHandler:
    """Optional human-in-the-loop bridge used during execution."""

    def __init__(self, interactive: bool = False, input_func=None):
        self.interactive = interactive
        self._input = input_func or input

    def check_interaction(self, step: str, result: str) -> tuple[bool, str]:
        if self.interactive and "失败" in result:
            print(f"步骤 '{step}' 执行失败，是否需要调整？")
            new_input = self._input("请输入调整内容（或按回车继续）：")
            if new_input.strip():
                return True, new_input
        return False, ""

    def prompt_user(self, message: str) -> str:
        if not self.interactive:
            return ""
        return self._input(message)