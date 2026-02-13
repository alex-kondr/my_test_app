with open("review.tomshw.it/new_review.tomshw.it.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.tomshw.it/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
