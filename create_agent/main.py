import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="20141"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://www.muycomputer.com/analisis/',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=10000,
    # curl=True
)
# agent.create_frontpage(
#     cats_xpath='//ul/li//a[contains(., " Reviews") and not(contains(., "All Reviews"))]',
#     name_xpath='text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//li[contains(@class, "infinite-post")]',
#     name_title="title",
#     name_title_xpath='.//h2/text()',
#     url_xpath='a/@href',
#     prod_rev="review",
#     next_url_xpath='//link[@rel="next"]/@href',
# )
# agent.create_review(
#     date_xpath='//meta[@property="article:published_time"]/@content',
#     author_xpath='//a[@rel="author"]/text()',
#     author_url_xpath='//a[@rel="author"]/@href',
#     grade_overall_xpath='//',
#     pros_xpath='//',
#     cons_xpath='//',
#     summary_xpath='',
#     conclusion_xpath='//',
#     excerpt_with_concl_xpath='.',
#     excerpt_xpath='//'
# )
