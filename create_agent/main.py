import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="19886"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://moviesgamesandtech.com/category/reviews/',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=6000,
    curl=True
)
# agent.create_frontpage(
#     cats_xpath='//div[@class="categories__single"]',
#     name_xpath='div[@class="categories__single-title"]/p/text()',
#     url_xpath='@href'
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
    author_xpath='//span[contains(@class, "post-author-name")]/a/text()',
    author_url_xpath='//span[contains(@class, "post-author-name")]/a/@href',
    grade_overall_xpath='//div[contains(@class, "review-final-score")]/text()',
    pros_xpath='(//p|//h4|//h5)[contains(., "Pros:")]/following-sibling::ul[1]/li',
    cons_xpath='(//p|//h4|//h5)[contains(., "Cons:")]/following-sibling::ul[1]/li',
    summary_xpath='',
    conclusion_xpath='//h2[regexp:test(., "Verdict|Final Thoughts")]/following-sibling::p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure", "i"))]//text()',
    excerpt_with_concl_xpath='//h2[regexp:test(., "Verdict|Final Thoughts")]/preceding-sibling::p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure", "i"))]//text()',
    excerpt_xpath='//div[contains(@class, "block-inner")]/p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure", "i"))]//text()'
)
