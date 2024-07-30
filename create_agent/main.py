import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm


name_agent = input("Name agent: ")
url = input("url: ")
next_func = input("Next func: ")
curl = bool(input("curl?: "))
breakers = input("Breakers?: ")
new_parser = bool(input("New parser?: "))

agent = AgentForm(name_agent)
agent.create_run(url=url, next_func=next_func, curl=curl, breakers=breakers, new_parser=new_parser)
agent.funcs.get(next_func)()