import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun, TypeAgent


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="18436"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://www.michelinman.com/auto/browse-tires/all-tires',
    next_func=ProcessRun.prodlist.name,
    new_parser=False,
    breakers=0,
    # curl=True
)
# agent.create_frontpage(
#     cats_xpath='//div[@class="cal_years"]/a/@href',
#     name_xpath='h3/text()',
#     url_xpath='a/@href'
# )
agent.create_revlist(
    revs_xpath='//div[@class="ds__card-body"]',
    name_title=TypeAgent.product.value,
    name_title_xpath='h2//span[contains(@class, "productName")]/text()',
    url_xpath='a/@href',
    prod_rev=TypeAgent.product.name,
    next_url_xpath='//link[@rel="next"]/@href',
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
