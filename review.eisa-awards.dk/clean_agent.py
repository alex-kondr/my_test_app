with open("review.eisa-awards.dk/new_review.eisa-awards.dk.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.eisa-awards.dk/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
