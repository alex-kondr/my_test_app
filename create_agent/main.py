import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.dolce-gusto.es",
    )
agent.create_run(
    name_agent_for_test="dolce-gusto.es",
    agent_id="19202",
    url='https://www.dolce-gusto.es/',
    next_func=ProcessRun.frontpage.name,
    new_parser=False,
    breakers=False,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//li[contains(., "Thema’s")]/ul//a',
#     name_xpath='.//text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//h2//a[@href and text()]',
#     name_title="title",
#     name_title_xpath='text()',
#     url_xpath='@href',
#     prod_rev="review",
#     next_url_xpath='//link[@rel="next"]/@href',
# )
# agent.create_review(
#     date_xpath='//meta[@property="article:modified_time"]/@content',
#     author_xpath='//div[contains(@class, "authors")]//a[@rel="author"]/text()',
#     author_url_xpath='//div[contains(@class, "authors")]//a[@rel="author"]/@href',
#     grade_overall_xpath='//span[contains(., "Rating:")]/text()',
#     pros_xpath='//ul[@class="pros"]/li',
#     cons_xpath='//ul[@class="cons"]/li',
#     summary_xpath='//div[@class="flex justify-between"]//p//text()',
#     conclusion_xpath='//h2[@id="h-conclusions" or regexp:test(., "conclusion", "i")]/following::p[not(preceding::div[@class="mb-8 relative"])]',
#     excerpt_with_concl_xpath='//h2[@id="h-conclusions" or regexp:test(., "conclusion", "i")]/preceding::body/p//text()',
#     excerpt_xpath='//body/p//text()'
# )
