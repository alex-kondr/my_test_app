import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm


name_agent = input("Name agent: ")

agent = AgentForm(name_agent)
agent.create_run()