import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm


agent = AgentForm(
    name="review.inside-digital.de",
    )
# agent.create_run(
    # name_agent_for_test="inside-digital.de",
    # agent_id="16797"
#     url="https://www.inside-digital.de/thema/test",
#     next_func="revlist",
#     new_parser=False,
#     breakers="10000",
#     curl=False
# )
# agent.create_revlist(
#     revs_xpath="",
#     name_title="title",
#     name_title_xpath='div[contains(@class, "td-module-title")]//a/text()',
#     url_xpath='div[contains(@class, "td-module-title")]//a/@href',
#     prod_rev="review",
#     next_url_xpath='//link[@rel="next"]/@href',
# )
agent.create_review(
    date_xpath='//meta[@itemprop="datePublished"]/@content',
    author_xpath='//span[@class="fn"]/a/text()', # '//span[@class="fn"]/a/@href'
    grade_overall_xpath="",
    pros_xpath="",
    cons_xpath="",
    summary_xpath="",
    conclusion_xpath="",
    excerpt_with_concl_xpath="",
    excerpt_xpath=""
)
