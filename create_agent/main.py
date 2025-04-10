import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="19564"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://www.khaleejtimes.com/contentapi/v1/getcollectionstories/tech-reviews-reviews?page=1&records=10',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=10000,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//ul[@class="menu"]//a',
#     name_xpath='text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//h3[@class="post-title"]/a',
#     name_title="title",
#     name_title_xpath='text()',
#     url_xpath='@href',
#     prod_rev="review",
#     next_url_xpath='//link[@rel="next"]/@href',
# )
agent.create_review(
    date_xpath='//p[contains(., "Published:")]//text()',
    author_xpath='//div[contains(@class, "auther")]//li//a[@class=""]/text()',
    author_url_xpath='//div[contains(@class, "auther")]//li//a[@class=""]/@href',
    grade_overall_xpath='1',
    pros_xpath='//p[contains(., "Hits:")]/following-sibling::p[not(preceding-sibling::p[contains(., "Misses:")]) and starts-with(normalize-space(.), "-")]',
    cons_xpath='//p[contains(., "Misses:")]/following-sibling::p[starts-with(normalize-space(.), "-")]',
    summary_xpath='//div[@class="recent"]//p[contains(@class, "preamble")]//text()',
    conclusion_xpath='1',
    excerpt_with_concl_xpath='1',
    excerpt_xpath='//div[contains(@class, "inner")]/p[not(@class)]//text()'
)
