from datetime import datetime
from pathlib import Path
import shutil

from product_test import functions
from models import AgentModel, DBSession, Status


def move_agent_folder(agent: AgentModel):
    date_now = datetime.now()
    agent_done_path = Path(f"{date_now.year}/{date_now.month}")
    agent_done_path.mkdir(parents=True, exist_ok=True)

    agent_path = Path(agent.source_name)
    if not agent_path.exists():
        agent_path = Path(f"{agent.source_name} (BB)")

    if agent_path.exists():
        shutil.move(agent_path, agent_done_path / agent_path.name)


def get_done_agents():
    with DBSession() as db:
        agents = db.query(AgentModel).filter_by(done=True, status=Status.qc).all()
        for agent in agents:
            functions.post_edit_page_agent(agent, done=True)
            agent.status = Status.done
            move_agent_folder(agent)

        db.commit()


get_done_agents()
