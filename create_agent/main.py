import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.hotpoint.co.ke",
    )
agent.create_run(
    name_agent_for_test="Hotpoint [EN]",
    agent_id="19977",
    url='https://www.the-ambient.com/reviews/',
    next_func=ProcessRun.frontpage.name,
    new_parser=False,
    breakers=10000,
    curl=False
)
agent.create_frontpage(
    cats_xpath='//li[contains(@class, "nav-item dropdown header-menu-mega")]',
    name_xpath='text()',
    url_xpath='@href'
)
# agent.create_revlist(
#     revs_xpath='//div[contains(@class, "grid-card")]//h2[@class="is-title post-title"]/a',
#     name_title="title",
#     name_title_xpath='text()',
#     url_xpath='@href',
#     prod_rev="review",
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
