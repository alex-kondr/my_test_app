import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm


agent = AgentForm(
    name="reviews.drohnen.de",
    )
agent.create_run(
    name_agent_for_test="Drohnen [DE]",
    agent_id="20203",
    url="https://www.drohnen.de/category/testberichte/",
    next_func="revlist",
    new_parser=False,
    breakers=False,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='(//ul[@class="sub-menu"])[1]//a',
#     name_xpath='.//text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//h2[@class="entry-title"]/a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//a[@class="next page-numbers"]/@href',
)
agent.create_review(
    date_xpath='//span[@itemprop="datePublished"]/@datetime',
    author_xpath='//span[@itemprop="author"]//text()',
    grade_overall_xpath='//div[@class="final-score"]/text()',
    pros_xpath='//div[@class="pros-gardena"]//li',
    cons_xpath='//div[@class="cons-gardena"]//li',
    summary_xpath='//div[@class="review-long-summary"]/p/text()',
    conclusion_xpath='(//h2|//h3)[.//text()="Fazit"]/following-sibling::p//text()',
    excerpt_with_concl_xpath='(//h2|//h3)[.//text()="Fazit"]/preceding-sibling::p//text()',
    excerpt_xpath=''
)
