with open("hi-fi.com.pl/new_hi-fi.com.pl.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("hi-fi.com.pl/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
