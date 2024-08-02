import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm


name_agent = input("Name agent: ")
name_agent_for_test = input("Name agent for test: ")
agent_id = input("agent_id: ")

agent = AgentForm(name=name_agent, name_agent_for_test=name_agent_for_test, agent_id=agent_id)
agent.create_run()