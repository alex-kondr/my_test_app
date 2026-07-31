import sys
import os
import asyncio

from sqlalchemy import select


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from product_test.functions import upload_code
import product_test.list_of_agents as agents
from models import AgentModel, async_session, Status


agent = agents.KENWOOD_ZA


with open("reviews.shopkenwood.co.za/new_reviews.shopkenwood.co.za.py", "r", encoding="utf-8") as file:
    agent_code = file.read()

agent_code = agent_code.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )

upload_code(agent, agent_code, run=True)


async def change_statuc_agent():
    async with async_session() as db:
        result = await db.execute(
            select(AgentModel).filter_by(agent_id=str(agent))
        )
        agent_db = result.scalar_one()
        agent_db.status = Status.running
        await db.commit()


asyncio.run(change_statuc_agent())