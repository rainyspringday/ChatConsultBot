from src.core.config import Config


class PromptLibrary:
    PROMPTS = {
        "chat": open(Config.prompts_dir.joinpath("chat_prompt.txt")).read(),
        "analyze_state": open(Config.prompts_dir.joinpath("analyze_state_prompt.txt")).read(),
        "analyze_plan":open(Config.prompts_dir.joinpath("analyze_plan_prompt.txt")).read(),
    }

    @staticmethod
    def get(name: str | None = None) -> str | None:
        if name is None:
            return None
        return PromptLibrary.PROMPTS.get(name)