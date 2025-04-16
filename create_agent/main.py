import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="20152"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://www.reiterladen24.de/',
    next_func=ProcessRun.frontpage.name,
    new_parser=False,
    breakers=10000,
    # curl=True
)
# agent.create_frontpage(
#     cats_xpath='//ul[@class="menu"]//a',
#     name_xpath='text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='///div[@class="grid_post"]/h3/a',
#     name_title="title",
#     name_title_xpath='text()',
#     url_xpath='@href',
#     prod_rev="review",
#     next_url_xpath='//link[@rel="next"]/@href',
# )
# agent.create_review(
#     date_xpath='//div[@class="teaser"]//span[@class="dkDate"]/text()',
#     author_xpath='//div[@id="buch-autor"]//a[not(img)]/text()',
#     author_url_xpath='//div[@id="buch-autor"]//a[not(img)]/@href',
#     grade_overall_xpath='',
#     pros_xpath='',
#     cons_xpath='',
#     summary_xpath='//div[@class="teaser"]/p/text()',
#     conclusion_xpath='',
#     excerpt_with_concl_xpath='',
#     excerpt_xpath='//h3[@id]/following-sibling::p//text()'
# )
