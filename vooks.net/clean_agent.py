with open("vooks.net/new_vooks.net.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("vooks.net/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
