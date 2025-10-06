with open("review.vg-reloaded.com/new_review.vg-reloaded.com.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.vg-reloaded.com/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
