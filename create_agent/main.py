import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.blackview.hk",
    )
agent.create_run(
    name_agent_for_test="Blackview.hk [HK]",
    agent_id="20062",
    url='https://store.blackview.hk',
    next_func=ProcessRun.frontpage.name,
    new_parser=False,
    breakers=False,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//li[contains(@class, "level0")]/a',
#     name_xpath='.//text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//h2[@class="tt-title prod-thumb-title-color"]/a',
#     name_title="name",
#     name_title_xpath='text()',
#     url_xpath='@href',
#     prod_rev="product",
#     next_url_xpath='//link[@rel="next"]/@href',
# )
# agent.create_review(
#     date_xpath='//meta[@property="article:published_time"]/@content',
#     author_xpath='//span[span[@class="by"]]/a[@rel="author"]/text()',
#     author_url_xpath='//span[span[@class="by"]]/a[@rel="author"]/@href',
#     grade_overall_xpath='count((//div[@class="full-stars"])[1]/i[@class="fa-solid fa-star"]) + count((//div[@class="full-stars"])[1]/i[@class="fa-solid fa-star"]) div 2',
#     pros_xpath='//div[@class="col" and .//h2[contains(., "Pros")]]/div/ul/li',
#     cons_xpath='//div[@class="col" and .//h2[contains(., "Cons")]]/div/ul/li',
#     summary_xpath='',
#     conclusion_xpath='//section[@class="review-summary"]/p//text()',
#     excerpt_with_concl_xpath='',
#     excerpt_xpath='//div[contains(@class, "post-content")]/p[not(contains(., "Read our guide"))]//text()'
# )
