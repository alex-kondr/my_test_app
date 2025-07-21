import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun, TypeAgent


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="3172"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://www.rakuten.co.jp/category/?l-id=top_normal_gmenu_d_list',
    next_func=ProcessRun.catlist.name,
    new_parser=True,
    breakers=10000,
    # curl=True
)
agent.create_frontpage(
    cats_xpath='//div[@class="gtc-genreUnit"]',
    name_xpath='a/div[contains(@class, "title")]/text()',
    url_xpath='@href'
)
agent.create_revlist(
    revs_xpath='//div[@data-id]',
    name_title=TypeAgent.product.value,
    name_title_xpath='.//h2[contains(@class, "title")]/a/text()',
    url_xpath='div/a[img]/@href',
    prod_rev=TypeAgent.product.name,
    next_url_xpath='//a[contains(@class, "nextPage")]/@href',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content|//time/@datetime',
    author_xpath='/text()',
    author_url_xpath='/@href',
    grade_overall_xpath='//text()',
    pros_xpath='/li',
    cons_xpath='/li',
    summary_xpath='//text()',
    conclusion_xpath='//text()',
    excerpt_with_concl_xpath='//text()',
    excerpt_xpath='//text()'
)
