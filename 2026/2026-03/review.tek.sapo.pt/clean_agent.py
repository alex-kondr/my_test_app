with open("review.tek.sapo.pt/new_review.tek.sapo.pt.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.tek.sapo.pt/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
