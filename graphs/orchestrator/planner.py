from graphs.supervisor import run_plan


def run_planner(user_input: str, skill: dict, project_context: dict):
    return run_plan(user_input, skill, project_context)
