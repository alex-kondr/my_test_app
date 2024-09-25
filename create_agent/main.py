import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.thetotalsite.it",
    )
# agent.create_run(
#     name_agent_for_test="thetotalsite.it [IT]",
#     agent_id="12819",
#     url="https://www.mumsnet.com/h/reviews",
#     next_func=ProcessRun.revlist.name,
#     new_parser=False,
#     breakers=False,
#     curl=False
# )
# agent.create_frontpage(
#     cats_xpath='(//ul[@class="flex flex-col"])[1]//a',
#     name_xpath='text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//h2[@class="post-title entry-title"]/a',
#     name_title="title",
#     name_title_xpath='text()',
#     url_xpath='@href',
#     prod_rev="review",
#     next_url_xpath='',
# )
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content',
    author_xpath='//div[@class="post-inner group"]//a[@rel="author"]/text()',
    author_url_xpath='//div[@class="post-inner group"]//a[@rel="author"]/@href',
    grade_overall_xpath='//div[regexp:test(normalize-space(.), "\d+\.?\d? ?/ ?\d+$") and contains(., "Globale")]//text()',
    pros_xpath='//div[not(@class or @id) and contains(., "Pro e contro")]/following-sibling::div[not(@class or @id) and regexp:test(normalize-space(.), "^\+")]',
    cons_xpath='//div[not(@class or @id) and contains(., "Pro e contro")]/following-sibling::div[not(@class or @id) and regexp:test(normalize-space(.), "^–")]',
    summary_xpath='//div[@align="center"]//font[@size="3"]//text()',
    conclusion_xpath='',
    excerpt_with_concl_xpath='',
    excerpt_xpath='//div[not(@class or @id or @align or regexp:test(normalize-space(.), "\d+\.?\d? ?/ ?\d+$"))]/span[@style="color: black"]//text()'
)
