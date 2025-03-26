import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="19925"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://unwiredforsound.com/',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=None,
    curl=False
)
agent.create_frontpage(
    cats_xpath='//ul[@class="menu"]//a',
    name_xpath='text()',
    url_xpath='@href'
)
agent.create_revlist(
    revs_xpath='//li[@class="lijst_archief"]/a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//link[@rel="next"]/@href',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content',
    author_xpath='//meta[@name="author"]/@content',
    author_url_xpath='',
    grade_overall_xpath='//div[@class="score"]/text()',
    pros_xpath='',
    cons_xpath='',
    summary_xpath='//p[contains(@class, "subtitle")]//text()',
    conclusion_xpath='',
    excerpt_with_concl_xpath='',
    excerpt_xpath='//div[contains(@id, "tekst_prom")]/a[@class="link_tekst"]//text()'
)
