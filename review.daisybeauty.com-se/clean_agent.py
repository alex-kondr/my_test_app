with open("review.daisybeauty.com-se/new_review.daisybeauty.com-se.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.daisybeauty.com-se/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
