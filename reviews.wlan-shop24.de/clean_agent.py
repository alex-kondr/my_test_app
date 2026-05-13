with open("reviews.wlan-shop24.de/new_reviews.wlan-shop24.de.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("reviews.wlan-shop24.de/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
