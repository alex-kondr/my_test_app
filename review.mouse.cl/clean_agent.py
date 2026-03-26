with open("review.mouse.cl/new_review.mouse.cl.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.mouse.cl/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
