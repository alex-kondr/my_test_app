import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.digiarena.e15.cz",
    )
agent.create_run(
    name_agent_for_test="Digiarena e15 [CZ]",
    agent_id="17951",
    url='http://digiarena.e15.cz/testy',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=10000,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//li[contains(., "Thema’s")]/ul//a',
#     name_xpath='.//text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//h2[@class="ar-title"]/a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//div[@class="load-more-wrapper"]/a/@href',
)
agent.create_review(
    date_xpath='//span[contains(@class, "article__date")]/text()',
    author_xpath='//meta[@name="author"]/@content',
    author_url_xpath='',
    grade_overall_xpath='//div[@class="review-rating"]//text()',
    pros_xpath='//div[contains(@class, "review-block-plus")]/div[@class="items"]/div',
    cons_xpath='//div[contains(@class, "review-block-minus")]/div[@class="items"]/div',
    summary_xpath='',
    conclusion_xpath='//h2[contains(., "Závěr")]/following-sibling::p[not(contains(., "Specifikace"))]//text()',
    excerpt_with_concl_xpath='//h2[contains(., "Závěr")]/preceding-sibling::p//text()',
    excerpt_xpath='//div[@class="article__body"]/p[not(contains(., "Specifikace"))]//text()'
)
