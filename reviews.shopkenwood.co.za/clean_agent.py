with open("reviews.shopkenwood.co.za/new_reviews.shopkenwood.co.za.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("reviews.shopkenwood.co.za/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )
