# src/action_result.py
class ActionResult:
    def __init__(self, extracted_content=None, error=None, include_in_memory=True):
        self.extracted_content = extracted_content
        self.error = error
        self.include_in_memory = include_in_memory

    def __str__(self):
        if self.error:
            return f"Error: {self.error}"
        return self.extracted_content or "No content"