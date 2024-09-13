import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="reviews.cyberphoto.se",
    )
agent.create_run(
    name_agent_for_test="Cyberphoto [SE]",
    agent_id="3142",
    url="https://www.cyberphoto.se/",
    next_func=ProcessRun.frontpage.name,
    new_parser=True,
    breakers=10000,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='(//ul[@class="flex flex-col"])[1]//a',
#     name_xpath='text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='(//h1[@class="article-title"]|//h2[@class="brief-title"])/a',
#     name_title="title",
#     name_title_xpath='text()',
#     url_xpath='@href',
#     prod_rev="review",
#     next_url_xpath='',
# )
# agent.create_review(
#     date_xpath='//meta[@property="article:modified_time"]/@content',
#     author_xpath='//p[@class="article-author"]/a[@class="author"]/text()',
#     author_url_xpath='//p[@class="article-author"]/a[@class="author"]/@href',
#     grade_overall_xpath='',
#     pros_xpath='',
#     cons_xpath='',
#     summary_xpath='//div[@id="Introduction"]/p/strong/text()',
#     conclusion_xpath='',
#     excerpt_with_concl_xpath='',
#     excerpt_xpath='//div[@id="Introduction"]/p[not(strong)]//text()'
# )
