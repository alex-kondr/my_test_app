import sys
import os
import asyncio

from sqlalchemy import select


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from product_test.functions import upload_code
import product_test.list_of_agents as agents
from models import AgentModel, DBSession, Status


agent_id = agents.EUROGAMER


with open("eurogamer.net/new_eurogamer.net.py", "r", encoding="utf-8") as file:
    agent_code = file.read()

agent_code = agent_code.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )

upload_code(agent_id, agent_code, run=True)


def set_running_status_agent(agent_id):
    with DBSession() as db:
        agent = db.query(AgentModel).filter_by(agent_id=str(agent_id), status=Status.in_progress).one_or_none()
        if agent:
            agent.status = Status.running
            db.commit()


set_running_status_agent(agent_id)