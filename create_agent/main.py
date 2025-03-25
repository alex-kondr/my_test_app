import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="19052"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='http://www.pointgphone.com/tests-android/',
    next_func=ProcessRun.catlist.name,
    new_parser=True,
    breakers=None,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//div[@class="categories__single"]',
#     name_xpath='div[@class="categories__single-title"]/p/text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//a[@class="post-link"]',
    name_title="title",
    name_title_xpath='h2/text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//link[@rel="next"]/@href',
)
# agent.create_review(
#     date_xpath='//meta[@property="article:published_time"]/@content',
#     author_xpath='//a[@class="author-name"]/text()',
#     author_url_xpath='//a[@class="author-name"]/@href',
#     grade_overall_xpath='',
#     pros_xpath='',
#     cons_xpath='',
#     summary_xpath='',
#     conclusion_xpath='//h3[contains(., "Fazit")]/following-sibling::p//text()',
#     excerpt_with_concl_xpath='//h3[contains(., "Fazit")]/preceding-sibling::p//text()',
#     excerpt_xpath='//div[@class="entry"]/p//text()'
# )
