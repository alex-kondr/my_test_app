import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.rockpapershotgun.com",
    )
agent.create_run(
    name_agent_for_test="Rock, Paper, Shotgun[US]",
    agent_id="19227",
    url='https://www.rockpapershotgun.com/reviews',
    next_func=ProcessRun.revlist.name,
    new_parser=True,
    breakers=10000,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//li[contains(., "Thema’s")]/ul//a',
#     name_xpath='.//text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//p[@class="title"]/a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//a[span[@aria-label="Next page"]]/@href',
)
agent.create_review(
    date_xpath='property="article:published_time"/@content',
    author_xpath='//span[@class="author"]/a/text()',
    author_url_xpath='//span[@class="author"]/a/@href',
    grade_overall_xpath='',
    pros_xpath='',
    cons_xpath='',
    summary_xpath='//p[@class="strapline"]//text()',
    conclusion_xpath='//div[contains(@class, "article_body_content")]/aside/text()',
    excerpt_with_concl_xpath='',
    excerpt_xpath='//div[contains(@class, "article_body_content")]/p//text()'
)
