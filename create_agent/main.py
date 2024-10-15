import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.delamar.de",
    )
agent.create_run(
    name_agent_for_test="Delamar [DE]",
    agent_id="18019",
    url='https://www.delamar.de/testberichte/',
    next_func=ProcessRun.revlist.name,
    new_parser=True,
    breakers=0,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//li[contains(., "Thema’s")]/ul//a',
#     name_xpath='.//text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//article[@class]/a|//article[@class]/p[@class="m-b-0"]/a',
    name_title="title",
    name_title_xpath='.//text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//a[@rel="next"]/@href',
)
agent.create_review(
    date_xpath='//meta[@name="date"]/@content',
    author_xpath='//div[contains(@class, "author")]/div[contains(., "Von")]/text()',
    author_url_xpath='',
    grade_overall_xpath='//span[@class="rating_number"]/text()', #count(//span[contains(@class, "fa-star-half")]), count(//span[@class="fa fa-star"])
    pros_xpath='//ul[@class="pro"]/li',
    cons_xpath='//ul[@class="contra"]/li',
    summary_xpath='//p[@class="article_teaser"]//text()',
    conclusion_xpath='//div[contains(@class, "fazit")]/p//text()',
    excerpt_with_concl_xpath='',
    excerpt_xpath='//div[@class="row"]/div/p[not(@class)]//text()'
)
