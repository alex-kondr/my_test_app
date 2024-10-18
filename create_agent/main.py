import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.androidinsider.ru",
    )
agent.create_run(
    name_agent_for_test="AndroidInsider[RU]",
    agent_id="18990",
    url='http://androidinsider.ru/',
    next_func=ProcessRun.frontpage.name,
    new_parser=False,
    breakers=5000,
    curl=True
)
# agent.create_frontpage(
#     cats_xpath='//li[contains(., "Thema’s")]/ul//a',
#     name_xpath='.//text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//a[@class="teaser__link"]',
#     name_title="title",
#     name_title_xpath='.//h3[contains(@class, "teaser__title")]//text()',
#     url_xpath='@href',
#     prod_rev="review",
#     next_url_xpath='//a[@title="More posts"]/@href',
# )
# agent.create_review(
#     date_xpath='//meta[@property="article:published_time"]/@content',
#     author_xpath='//meta[@name="author"]/@content',
#     author_url_xpath='',
#     grade_overall_xpath='//b[contains(., "Score:")]//text()',
#     pros_xpath='',
#     cons_xpath='',
#     summary_xpath='//p[@data-test-id="header-intro"]//text()',
#     conclusion_xpath='',
#     excerpt_with_concl_xpath='',
#     excerpt_xpath='//div[@class="paywall"]/p[not(contains(., "Geselecteerd door de redactie"))]//text()'
# )
