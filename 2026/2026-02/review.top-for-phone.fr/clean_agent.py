with open("review.top-for-phone.fr/new_review.top-for-phone.fr.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.top-for-phone.fr/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
