with open("review.canadianreviewer.com/new_review.canadianreviewer.com.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.canadianreviewer.com/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
