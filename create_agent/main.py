import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="4607"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://www.otto.de/',
    next_func=ProcessRun.frontpage.name,
    new_parser=True,
    breakers=10000,
    # curl=True
)
agent.create_frontpage(
    cats_xpath='//ul[contains(@class, "global-navigation")]/li[contains(@class, "item-element")]//a',
    name_xpath='.//text()',
    url_xpath='@href'
)
agent.create_revlist(
    revs_xpath='//a[@class="find_tile__productLink"]',
    name_title="name",
    name_title_xpath='.//p[contains(@class, "find_tile__name")]/text()',
    url_xpath='@href',
    prod_rev="product",
    next_url_xpath='//a[span[@class="next-link"]]/@href',
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
