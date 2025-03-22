import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="reviews.fotokoch.de",
    )
agent.create_run(
    name_agent_for_test="Fotokoch [DE]",
    agent_id="20182",
    url='https://www.fotokoch.de/index.html',
    next_func=ProcessRun.prodlist.name,
    new_parser=False,
    breakers=4000,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//div[@class="categories__single"]',
#     name_xpath='div[@class="categories__single-title"]/p/text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//div[@class="product-card-base"]',
#     name_title="name",
#     name_title_xpath='h2[contains(@class, "title")]//text()',
#     url_xpath='a/@href',
#     prod_rev="product",
#     next_url_xpath='',
# )
# agent.create_review(
#     date_xpath='//meta[@name="article:published_time"]/@content',
#     author_xpath='//span[@class="author"]/a/text()',
#     author_url_xpath='//span[@class="author"]/a/@href',
#     grade_overall_xpath='//div[@class="review_rating"]/@data-value',
#     pros_xpath='',
#     cons_xpath='',
#     summary_xpath='//p[@class="strapline"]//text()',
#     conclusion_xpath='sonlu',
#     excerpt_with_concl_xpath='...',
#     excerpt_xpath='//div[contains(@class, "article_body_conten")]/p[not(preceding-sibling::hr)]//text()'
# )
