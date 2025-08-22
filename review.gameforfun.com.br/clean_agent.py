with open("review.gameforfun.com.br/new_review.gameforfun.com.br.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("review.gameforfun.com.br/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(data, context, session)"
        )
    )
