import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.attackofthefanboy.com",
    )
agent.create_run(
    name_agent_for_test="Attack of the Fanboy [US]",
    agent_id="19228",
    url='https://attackofthefanboy.com/category/reviews/',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=3000,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//li[contains(., "Thema’s")]/ul//a',
#     name_xpath='.//text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//a[contains(@class, "wp-block-gamurs-article-tile__link") and string-length(normalize-space(.)) > 1]',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//link[@rel="next"]/@href',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content',
    author_xpath='//a[contains(@class, "wp-block-gamurs-author-bio__name")]/text()',
    author_url_xpath='//a[contains(@class, "wp-block-gamurs-author-bio__name")]/@href',
    grade_overall_xpath='count(//div[contains(@class, "review-summary__star-rating")]//span[contains(@class, "star-filled")])',
    # count(//div[contains(@class, "review-summary__star-rating")]//span[contains(@class, "star-half")])
    pros_xpath='//div[contains(@class, "__pros-wrapper")]//li',
    cons_xpath='//div[contains(@class, "__cons-wrapper")]//li',
    summary_xpath='//div[contains(@class, "content--subtitle")]//text()',
    conclusion_xpath='//h3[regexp:test(., "verdict", "i")]/following-sibling::p//text()',
    excerpt_with_concl_xpath='//h3[regexp:test(., "verdict", "i")]/preceding-sibling::p//text()',
    excerpt_xpath='//div[contains(@class, "article-content")]/p//text()'
)
