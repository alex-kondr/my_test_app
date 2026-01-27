with open("review.digimanie.cz/new_review.digimanie.cz.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.digimanie.cz/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
