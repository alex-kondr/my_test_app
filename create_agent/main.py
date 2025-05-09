import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="6111"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='http://www.sztab.com/recenzje-1.html',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=0,
    # curl=True
)
# agent.create_frontpage(
#     cats_xpath='//li[contains(., "Reviews")]/ul/li[contains(@class, "group/category")]',
#     name_xpath='a/text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//h4[contains(@class, "title")]/a',
#     name_title="title",
#     name_title_xpath='text()',
#     url_xpath='@href',
#     prod_rev="review",
#     next_url_xpath='//a[@rel="next"]/@href',
# )
# agent.create_review(
#     date_xpath='//time/@datetime',
#     author_xpath='//a[contains(@href, "/autor/") and contains(@class, "link")]/text()',
#     author_url_xpath='//a[contains(@href, "/autor/") and contains(@class, "link")]/@href',
#     grade_overall_xpath='',
#     pros_xpath='//h3[regexp:test(., "positivos|prós")]/following-sibling::ul[1]/li',
#     cons_xpath='//h3[regexp:test(., "negativos|contras")]/following-sibling::ul[1]/li',
#     summary_xpath='//div[contains(@class, "tec--article__body")]/p[@dir="ltr"][1]//text()',
#     conclusion_xpath='//h2[contains(., "Vale a pena?")]/following-sibling::p[not(contains(., "Comente nas redes sociais do Voxel"))]//text()',
#     excerpt_with_concl_xpath='.//text()',
#     excerpt_xpath='//div[not(.//p[contains(., "SCORE")] or contains(@class, "fazit"))]/p[not(@class)]//text()'
# )
