with open("review.wheelsforwomen.ie/new_review.wheelsforwomen.ie.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.wheelsforwomen.ie/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
