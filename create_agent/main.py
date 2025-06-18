import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="19496"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://soundvisionreview.com/',
    next_func=ProcessRun.frontpage.name,
    new_parser=False,
    breakers=0,
    # curl=True
)
agent.create_frontpage(
    cats_xpath='//ul[@id="menu-category-menu"]/li',
    name_xpath='text()',
    url_xpath='@href'
)
agent.create_revlist(
    revs_xpath='//h3[contains(@class, "title")]/a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//link[@rel="next"]/@href',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content',
    author_xpath='//text()',
    author_url_xpath='/@href',
    grade_overall_xpath='//text()',
    pros_xpath='/li',
    cons_xpath='/li',
    summary_xpath='//text()',
    conclusion_xpath='//text()',
    excerpt_with_concl_xpath='//text()',
    excerpt_xpath='//text()'
)
