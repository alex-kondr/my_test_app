import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="17726"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://digitalt.tv/kategori/anmeldelser/',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=0,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//ul[@class="menu"]//a',
#     name_xpath='text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//h3[@class="post-title"]/a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//link[@rel="next"]/@href',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content',
    author_xpath='//a[contains(@class, "author-name")]/text()',
    author_url_xpath='',
    grade_overall_xpath='1',
    pros_xpath='1',
    cons_xpath='1',
    summary_xpath='1',
    conclusion_xpath='1',
    excerpt_with_concl_xpath='1',
    excerpt_xpath='1'
)
