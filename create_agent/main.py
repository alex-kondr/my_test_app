import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.mumsnet.uk",
    )
agent.create_run(
    name_agent_for_test="Mumsnet [UK]",
    agent_id="12363",
    url="https://www.mumsnet.com/h/reviews",
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=False,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='(//ul[@class="flex flex-col"])[1]//a',
#     name_xpath='text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//div[contains(@class, "flex pt-6")]/div[p]',
    name_title="title",
    name_title_xpath='p[contains(@class, "font-bold")]/text()',
    url_xpath='a/@href',
    prod_rev="review",
    next_url_xpath='',
)
# agent.create_review(
#     date_xpath='//meta[contains(@property, "published_time")]/@content',
#     author_xpath='//a[contains(@href, ",autor,")]',
#     author_url_xpath='',
#     grade_overall_xpath='',
#     pros_xpath='',
#     cons_xpath='',
#     summary_xpath='',
#     conclusion_xpath='',
#     excerpt_with_concl_xpath='',
#     excerpt_xpath='//div[@class="VXd-"]/p'
# )
