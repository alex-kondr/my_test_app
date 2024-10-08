import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.playfront.de",
    )
agent.create_run(
    name_agent_for_test="Playfront [DE]",
    agent_id="16946",
    url="https://playfront.de/category/reviews/",
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=False,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//ul[@class="menu"]/li[div]/a',
#     name_xpath='text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//h2[contains(@class, "post-title")]/a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//link[@rel="next"]/@href',
)
# agent.create_review(
#     date_xpath='//meta[@property="article:published_time"]/@content',
#     author_xpath='//a[contains(@href, "/author/")]/text()',
#     author_url_xpath='//a[contains(@href, "/author/")]/@href',
#     grade_overall_xpath='',
#     pros_xpath='',
#     cons_xpath='',
#     summary_xpath='',
#     conclusion_xpath='',
#     excerpt_with_concl_xpath='',
#     excerpt_xpath='//div[@itemprop="text"]/p//text()'
# )
