with open("gamesradar.com/new_gamesradar.com.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("gamesradar.com/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
