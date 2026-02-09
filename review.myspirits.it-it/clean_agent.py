with open("review.myspirits.it-it/new_review.myspirits.it-it.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.myspirits.it-it/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
