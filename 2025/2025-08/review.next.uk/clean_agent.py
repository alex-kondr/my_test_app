with open("review.next.uk/new_review.next.uk.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.next.uk/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
