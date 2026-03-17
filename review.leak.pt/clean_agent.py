with open("review.leak.pt/new_review.leak.pt.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.leak.pt/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
