import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="reviews.vg247.com",
    )
agent.create_run(
    name_agent_for_test="VG247 [EN]",
    agent_id="20142",
    url='https://www.vg247.com/archive/reviews',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=3000,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//div[@class="categories__single"]',
#     name_xpath='div[@class="categories__single-title"]/p/text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//h2[@class="archive__title"]/a',
    name_title="title",
    name_title_xpath='/text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//a[span[@aria-label="Next page"]]/@href',
)
agent.create_review(
    date_xpath='//meta[@name="article:published_time"]/@content',
    author_xpath='//span[@class="author"]/a/text()',
    author_url_xpath='//span[@class="author"]/a/@href',
    grade_overall_xpath='//div[@class="review_rating"]/@data-value',
    pros_xpath='',
    cons_xpath='',
    summary_xpath='//p[@class="strapline"]//text()',
    conclusion_xpath='sonlu',
    excerpt_with_concl_xpath='...',
    excerpt_xpath='//div[contains(@class, "article_body_conten")]/p[not(preceding-sibling::hr)]//text()'
)
