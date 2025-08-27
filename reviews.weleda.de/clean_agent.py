with open("reviews.weleda.de/new_reviews.weleda.de.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("reviews.weleda.de/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
