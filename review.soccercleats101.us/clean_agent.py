with open("review.soccercleats101.us/new_review.soccercleats101.us.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.soccercleats101.us/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
