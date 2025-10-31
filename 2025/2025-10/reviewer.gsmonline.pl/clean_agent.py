with open("reviewer.gsmonline.pl/new_reviewer.gsmonline.pl.py", "r", encoding="utf-8") as file:
    agent = file.read()


with open("reviewer.gsmonline.pl/agent.py", "w", encoding="utf-8") as file:
    file.write(agent.replace(
            "(data: Response, context: dict[str, str], session: Session)",
            "(data, context, session)"
        ).replace(
            "(context: dict[str, str], session: Session)",
            "(context, session)"
        )
    )




    # if not context.get('repeat') and not data.xpath('//div[@class="article-full"]//p'):
    #     time.sleep(600)
    #     session.do(Request(data.response_url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, repeat=True))
    #     return