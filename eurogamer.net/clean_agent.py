with open("eurogamer.net/new_eurogamer.net.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("eurogamer.net/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
