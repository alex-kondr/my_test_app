with open("review.pickr.au/new_review.pickr.au.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.pickr.au/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
