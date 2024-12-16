import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.smarthomesounds.co.uk",
    )
agent.create_run(
    name_agent_for_test="Smart Home Sounds [UK]",
    agent_id="19946",
    url='https://www.smarthomesounds.co.uk/',
    next_func=ProcessRun.frontpage.name,
    new_parser=False,
    breakers=10000,
    curl=False
)
agent.create_frontpage(
    cats_xpath='//a[regexp:test(@class, "^level-0")]',
    name_xpath='.//text()',
    url_xpath='@href'
)
# agent.create_revlist(
#     revs_xpath='//div[@class="product-info"]/a',
#     name_title="name",
#     name_title_xpath='text()',
#     url_xpath='@href',
#     prod_rev="product",
#     next_url_xpath='//link[@rel="next"]/@href',
# )
# agent.create_review(
#     date_xpath='//meta[@property="article:published_time"]/@content',
#     author_xpath='//div[@class="art-dtls-info"]/a/text()',
#     author_url_xpath='//div[@class="art-dtls-info"]/a/@href',
#     grade_overall_xpath='//p[contains(., "Rating:")]/text()[regexp:test(., "\d.?\d?/\d")]',
#     pros_xpath='//p[strong[contains(., "Pros")]]/text()',
#     cons_xpath='//p[strong[contains(., "Cons")]]/text()',
#     summary_xpath='//span[@class="less-cont"]//text()',
#     conclusion_xpath='//p[strong[contains(., "Verdict")]]/text()|//p[strong[contains(., "Verdict")]]/following-sibling::p//text()',
#     excerpt_with_concl_xpath='//p[strong[contains(., "Verdict")]]/preceding-sibling::p[not(strong[regexp:test(., "Pros|Cons|Rating")])]//text()[not(contains(., "Review:"))]',
#     excerpt_xpath='//div[contains(@class, "content")]/p[not(strong[regexp:test(., "Pros|Cons|Rating")])]//text()[not(contains(., "Review:"))]'
# )
