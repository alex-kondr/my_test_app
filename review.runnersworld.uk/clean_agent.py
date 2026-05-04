with open("review.runnersworld.uk/new_review.runnersworld.uk.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.runnersworld.uk/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
