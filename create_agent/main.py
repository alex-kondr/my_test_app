import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="reviews.coffeefriend.se",
    )
agent.create_run(
    name_agent_for_test="COFFEE FRIEND [SE]",
    agent_id="20105",
    url='https://www.coffeefriend.se/',
    next_func=ProcessRun.frontpage.name,
    new_parser=False,
    breakers=False,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//div[@class="categories__single"]',
#     name_xpath='div[@class="categories__single-title"]/p/text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//div[contains(@class, "post-content")]',
#     name_title="title",
#     name_title_xpath='.//span[contains(@class, "desktop")]/text()',
#     url_xpath='a/@href',
#     prod_rev="review",
#     next_url_xpath='//link[@rel="next"]/@href',
# )
# agent.create_review(
#     date_xpath='//meta[@name="article:published_time"]/@content',
#     author_xpath='//p[contains(@class, "item-author")]//a',
#     author_url_xpath='',
#     grade_overall_xpath='',
#     pros_xpath='pros',
#     cons_xpath='cons',
#     summary_xpath='summ',
#     conclusion_xpath='sonlu',
#     excerpt_with_concl_xpath='...',
#     excerpt_xpath='...'
# )
