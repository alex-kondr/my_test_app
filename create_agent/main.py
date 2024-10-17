import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.biogamergirl.us",
    )
agent.create_run(
    name_agent_for_test="BioGamer Girl [US]",
    agent_id="18401",
    url='http://www.biogamergirl.com/search/label/Video%20Game%20Review',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=0,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//li[contains(., "Thema’s")]/ul//a',
#     name_xpath='.//text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//h3[contains(@class, "post-title")]/a',
    name_title="title",
    name_title_xpath='.//text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//a[@title="More posts"]/@href',
)
agent.create_review( # //div[contains(@id, "post-body")]/@id
    date_xpath='',
    author_xpath='',
    author_url_xpath='',
    grade_overall_xpath='//b[contains(., "Score:")]//text()',
    pros_xpath='',
    cons_xpath='',
    summary_xpath='',
    conclusion_xpath='',
    excerpt_with_concl_xpath='',
    excerpt_xpath='//div[contains(@class, "entry-content")]/text()|//div[contains(@class, "entry-content")]/b//text()'
)
