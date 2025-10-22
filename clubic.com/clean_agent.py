with open("clubic.com/new_clubic.com.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("clubic.com/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
