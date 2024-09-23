import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="gadzetomania.pl",
    )
# agent.create_run(
#     name_agent_for_test="gadzetomania [PL]",
#     agent_id="6276",
#     url="https://gadzetomania.pl/gadzety,temat,6008941124117121",
#     next_func=ProcessRun.revlist.name,
#     new_parser=False,
#     breakers=10000,
#     curl=False
# )
# agent.create_frontpage(
#     cats_xpath='(//ul[@class="flex flex-col"])[1]//a',
#     name_xpath='text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//h2/a',
#     name_title="title",
#     name_title_xpath='text()',
#     url_xpath='@href',
#     prod_rev="review",
#     next_url_xpath='//a[@rel="prev" and contains(@href, "strona=")]/@href',
# )
agent.create_review(
    date_xpath='//meta[contains(@property, "published_time")]/@content',
    author_xpath='//a[contains(@href, ",autor,")]',
    author_url_xpath='',
    grade_overall_xpath='',
    pros_xpath='',
    cons_xpath='',
    summary_xpath='',
    conclusion_xpath='',
    excerpt_with_concl_xpath='',
    excerpt_xpath='//div[@class="VXd-"]/p'
)
