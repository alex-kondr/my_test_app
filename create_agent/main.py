import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="20158"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='hhttps://www.koffermarkt.com/',
    next_func=ProcessRun.frontpage.name,
    new_parser=True,
    breakers=0,
    # curl=True
)
# agent.create_frontpage(
#     cats_xpath='//li[contains(., "Reviews")]/ul/li[contains(@class, "group/category")]',
#     name_xpath='a/text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//a[@class="stretched-link"]',
#     name_title="title",
#     name_title_xpath='.//text()',
#     url_xpath='@href',
#     prod_rev="review",
#     next_url_xpath='//a[@rel="next"]/@href',
# )
# agent.create_review(
#     date_xpath='//p[img[contains(@src, "/authors/")]]/text()',
#     author_xpath='//p[img[contains(@src, "/authors/")]]/img/@title',
#     author_url_xpath='',
#     grade_overall_xpath='//div[p[contains(., "SCORE")]]/p[not(contains(., "SCORE"))]/text()',
#     pros_xpath='//ul[contains(@class, "ul_pro")]/li',
#     cons_xpath='//ul[contains(@class, "ul_contra ")]/li',
#     summary_xpath='//h2[contains(@class, "h1")]/span/text()',
#     conclusion_xpath='//div[contains(@class, "fazit")]//text()',
#     excerpt_with_concl_xpath='.//text()',
#     excerpt_xpath='//div[not(.//p[contains(., "SCORE")] or contains(@class, "fazit"))]/p[not(@class)]//text()'
# )
