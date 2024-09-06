import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="reviews.techtest.org-de",
    )
agent.create_run(
    name_agent_for_test="Techtest [DE]",
    agent_id="20207",
    url="https://techtest.org/category/reviews/",
    next_func=ProcessRun.revlist,
    new_parser=False,
    breakers=3000,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//li[contains(@class, "submenu index category")]',
#     name_xpath='a/text()',
#     url_xpath=''
# )
agent.create_revlist(
    revs_xpath='//h3[contains(@class, "entry-title")]/a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//link[@rel="next"]/@href',
)
agent.create_review(
    date_xpath='//time/@datetime',
    author_xpath='//a[@class="tdb-author-name"]/text()',
    author_url_xpath='//a[@class="tdb-author-name"]/@href',
    grade_overall_xpath='//div[@class="score"]/text()',
    pros_xpath='//div[regexp:test(@class, "lets-review-block__pro$")]',
    cons_xpath='//div[regexp:test(@class, "lets-review-block__con$")]',
    summary_xpath='//div[@class="tdb-block-inner td-fix-index"]/p[not(preceding-sibling::div[@id="ez-toc-container"])]//text()',
    conclusion_xpath='//h2[contains(., "Fazit")]/following-sibling::p//text()',
    excerpt_with_concl_xpath='//h2[contains(., "Fazit")]/preceding-sibling::p[preceding-sibling::div[@id="ez-toc-container"]]//text()',
    excerpt_xpath=''
)
