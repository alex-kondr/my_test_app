import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="17617"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://www.bestofrobots.fr/',
    next_func=ProcessRun.catlist.name,
    new_parser=False,
    breakers=3000,
    # curl=True
)
# agent.create_frontpage(
#     cats_xpath='//li[contains(., "Reviews")]/ul/li[contains(@class, "group/category")]',
#     name_xpath='a/text()',
#     url_xpath='@href'
# )
#  ul/li/a
#   text()
#   @href
# agent.create_revlist(
#     revs_xpath='//li[contains(., "Reviews")]/ul/li[contains(@class, "group/category")]',
#     name_title="title",
#     name_title_xpath='a/text()',
#     url_xpath='@href',
#     prod_rev="review",
#     next_url_xpath='//a[span[@aria-label="Próxima página"]]/@href',
# )
# agent.create_review(
#     date_xpath='//meta[@property="article:published_time"]/@content',
#     author_xpath='//span[@class="author"]/a/text()',
#     author_url_xpath='//span[@class="author"]/a/@href',
#     grade_overall_xpath='//div[@class="review_rating"]/@data-value',
#     pros_xpath='//td[font[@color="#169600"]]/ul/li',
#     cons_xpath='//td[font[@color="#E10000"]]/ul/li',
#     summary_xpath='//p[@class="strapline"]//text()',
#     conclusion_xpath='//h2[contains(., "Conclusão")]/following-sibling::p//text()',
#     excerpt_with_concl_xpath='//h2[contains(., "Conclusão")]/preceding-sibling::p//text()',
#     excerpt_xpath='//div[contains(@class, "body_content")]/p//text()'
# )
