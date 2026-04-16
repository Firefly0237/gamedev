from . import art_agent, code_agent, config_agent


WORKERS = [code_agent, art_agent, config_agent]
ALL_SPECS = [worker.SPEC for worker in WORKERS]


def get_all_agents():
    return [worker.get_agent() for worker in WORKERS]
