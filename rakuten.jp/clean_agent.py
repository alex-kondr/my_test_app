with open("rakuten.jp/new_rakuten.jp.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("rakuten.jp/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
