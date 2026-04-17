with open("review.runnersworld.de/new_review.runnersworld.de.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.runnersworld.de/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
