import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="19713"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://www.storedj.com.au/',
    next_func=ProcessRun.frontpage.name,
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
#     revs_xpath='//div[p[@data-testid="meta-label"]]',
#     name_title="title",
#     name_title_xpath='p/text()',
#     url_xpath='a/@href',
#     prod_rev="review",
#     next_url_xpath='//link[@rel="next"]/@href',
# )
# agent.create_review(
#     date_xpath='//meta[@property="article:published_time"]/@content',
#     author_xpath='//a[contains(@href, "https://www.clubic.com/auteur/")]/text()',
#     author_url_xpath='//a[contains(@href, "https://www.clubic.com/auteur/")]/@href',
#     grade_overall_xpath='//span[contains(@class, "mod-dark")]/text()',
#     pros_xpath='(//div[contains(., "Les plus")]/following-sibling::ul)[1]/li',
#     cons_xpath='(//div[contains(., "Les moins")]/following-sibling::ul)[1]/li',
#     summary_xpath='//div[contains(@class, "row")]/div/p/strong//text()',
#     conclusion_xpath='//div[div[contains(., "Conclusion")]]/following-sibling::div/div/p//text()',
#     excerpt_with_concl_xpath='',
#     excerpt_xpath='//div[contains(@class, "row")]/div/p[not(strong)]//text()'
# )
