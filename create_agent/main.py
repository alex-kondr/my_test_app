import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.bouyguestelecom.fr",
    )
agent.create_run(
    name_agent_for_test="Bouygues Telecom [FR]",
    agent_id="19774",
    url='https://www.bouyguestelecom.fr/telephones-mobiles/',
    next_func=ProcessRun.prodlist.name,
    new_parser=False,
    breakers=10000,
    curl=True
)
# agent.create_frontpage(
#     cats_xpath='//li[contains(@class, "level0")]',
#     name_xpath='a/span/text()',
#     url_xpath='a/@href'
# )
agent.create_revlist(
    revs_xpath='//div[contains(@class, "has-text-centered product-card")]',
    name_title="name",
    name_title_xpath='.//p[contains(@class, "product-card-title")]/text()',
    url_xpath='a/@href',
    prod_rev="review",
    next_url_xpath='//a[@class="pagination-next"]/@href',
)
# agent.create_review(
#     date_xpath='//span[contains(@class, "item--type-date")]/text()',
#     author_xpath='//span[contains(@class, "item--type-author")]/text()',
#     author_url_xpath='',
#     grade_overall_xpath='',
#     pros_xpath='',
#     cons_xpath='',
#     summary_xpath='',
#     conclusion_xpath='//h2[contains(., "Ten slotte")]/following-sibling::p[not(@style)]//text()',
#     excerpt_with_concl_xpath='//h2[contains(., "Ten slotte")]/preceding-sibling::p[not(@style)]//text()',
#     excerpt_xpath='//div[contains(@class, "post-content")]//p[not(@style)]//text()'
# )
