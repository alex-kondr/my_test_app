with open("review.turtlebeach.com/new_review.turtlebeach.com.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.turtlebeach.com/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
