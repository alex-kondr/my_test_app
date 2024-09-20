import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.tomshw.it",
    )
# agent.create_run(
#     name_agent_for_test="Tom's hardware - IT",
#     agent_id="3326",
#     url="https://www.tomshw.it/tag/hardware",
#     next_func=ProcessRun.revlist.name,
#     new_parser=True,
#     breakers=10000,
#     curl=False
# )
# agent.create_frontpage(
#     cats_xpath='(//ul[@class="flex flex-col"])[1]//a',
#     name_xpath='text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//div[@class="flex flex-col justify-center text-start space-y-1"]',
#     name_title="title",
#     name_title_xpath='a/text()',
#     url_xpath='a/@href',
#     prod_rev="review",
#     next_url_xpath='//a[@rel="next"]/@href',
# )
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content',
    author_xpath='//a[regexp:test(@class, "^text-red-600")]/text()',
    author_url_xpath='//a[regexp:test(@class, "^text-red-600")]/@href',
    grade_overall_xpath='',
    pros_xpath='',
    cons_xpath='',
    summary_xpath='//p[contains(@class, "italic")]//text()',
    conclusion_xpath='',
    excerpt_with_concl_xpath='',
    excerpt_xpath='//div[contains(@class, "p-4")]/p[not(@class or @style)]//text()'
)
