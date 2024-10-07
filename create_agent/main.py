import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.sirshanksalot.com",
    )
# agent.create_run(
#     name_agent_for_test="SirShanksAlot",
#     agent_id="12676",
#     url="https://sirshanksalot.com/",
#     next_func=ProcessRun.frontpage.name,
#     new_parser=True,
#     breakers=False,
#     curl=False
# )
# agent.create_frontpage(
#     cats_xpath='//div[@id="primary-menu"]/ul/li',
#     name_xpath='a/text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//h2[contains(@class, "gb-headline-text")]/a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//link[@rel="next"]/@href',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content',
    author_xpath='//a[contains(@href, "/author/")]/text()',
    author_url_xpath='//a[contains(@href, "/author/")]/@href',
    grade_overall_xpath='',
    pros_xpath='',
    cons_xpath='',
    summary_xpath='',
    conclusion_xpath='',
    excerpt_with_concl_xpath='',
    excerpt_xpath='//div[@itemprop="text"]/p//text()'
)
