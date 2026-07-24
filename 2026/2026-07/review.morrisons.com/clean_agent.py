import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from product_test.functions import upload_code
import product_test.list_of_agents as agents


agent = agents.MORRISONS_UK


with open("review.morrisons.com/new_review.morrisons.com.py", "r", encoding="utf-8") as file:
    agent_code = file.read()


# with open("review.senses.se/agent.py", "w", encoding="utf-8") as file:
#     file.write(agent.replace(
#             "(data: Response, context: dict[str, str], session: Session)",
#             "(data, context, session)"
#         ).replace(
#             "(context: dict[str, str], session: Session)",
#             "(context, session)"
#         )
#     )

agent_code = agent_code.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )

upload_code(agent, agent_code)