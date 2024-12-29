import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="reviews.rollei.de",
    )
# agent.create_run(
#     name_agent_for_test="Rollei [DE]",
#     agent_id="20090",
#     url='https://www.rollei.de/collections/',
#     next_func=ProcessRun.frontpage.name,
#     new_parser=False,
#     breakers=10000,
#     curl=False
# )
# agent.create_frontpage(
#     cats_xpath='//a[contains(@class, "card-link")]',
#     name_xpath='text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//a[@class="m-articleWidget__link" and contains(@href, "https://24.hu/tech/")]',
#     name_title="title",
#     name_title_xpath='text()',
#     url_xpath='@href',
#     prod_rev="reviews",
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
