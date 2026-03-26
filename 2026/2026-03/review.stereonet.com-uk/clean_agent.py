with open("review.stereonet.com-uk/new_review.stereonet.com-uk.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.stereonet.com-uk/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
