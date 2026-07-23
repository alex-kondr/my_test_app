with open("review.hifiheadphones.co.uk/new_review.hifiheadphones.co.uk.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.hifiheadphones.co.uk/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
