with open("review.rezensionen-fuer-millionen.de/new_review.rezensionen-fuer-millionen.de.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.rezensionen-fuer-millionen.de/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
