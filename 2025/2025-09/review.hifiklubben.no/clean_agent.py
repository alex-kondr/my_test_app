with open("review.hifiklubben.no/new_review.hifiklubben.no.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.hifiklubben.no/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
