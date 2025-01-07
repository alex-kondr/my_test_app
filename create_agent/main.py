import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.spiceworks.com",
    )
agent.create_run(
    name_agent_for_test="spiceworks[US]",
    agent_id="19653",
    url='https://community.spiceworks.com/tag/product-reviews/l/latest.json?page=0&tags[]=product-reviews',
    next_func=ProcessRun.prodlist.name,
    new_parser=False,
    breakers=10000,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//body[span[@class="link-top-line"]]',
#     name_xpath='.//a[contains(@class, "title")]/text()',
#     url_xpath='.//a[contains(@class, "title")]/@href'
# )
# agent.create_revlist(
#     revs_xpath='//body[span[@class="link-top-line"]]',
#     name_title="name",
#     name_title_xpath='.//a[contains(@class, "title")]/text()',
#     url_xpath='.//a[contains(@class, "title")]/@href',
#     prod_rev="product",
#     next_url_xpath='//a[contains(@class, "next")]/@href',
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
