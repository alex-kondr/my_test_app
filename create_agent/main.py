import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.androidheadlines.com",
    )
agent.create_run(
    name_agent_for_test="AndroidHeadlines [US]",
    agent_id="19014",
    url='https://www.androidheadlines.com/category/reviews',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=5000,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//li[contains(., "Thema’s")]/ul//a',
#     name_xpath='.//text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//a[contains(@class, "post-holder")]',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//lin[@rel="next"]/@href',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content[contains(., "T")]',
    author_xpath='//div[@class="entry-meta-author-name"]//a/text()',
    author_url_xpath='//div[@class="entry-meta-author-name"]//a/@href',
    grade_overall_xpath='',
    pros_xpath='1',
    cons_xpath='1',
    summary_xpath='1',
    conclusion_xpath='1',
    excerpt_with_concl_xpath='1',
    excerpt_xpath='2'
)
