from typing import Any
import agent

# Ми явно кажемо аналізатору: дивись у модуль agent і бери звідти клас Session
def run(context: Any, session: agent.Session) -> None: ...