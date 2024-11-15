import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.miekofishing.se",
    )
# agent.create_run(
#     name_agent_for_test="Mieko Fishing [SE]",
#     agent_id="19729",
#     url='https://www.miekofishing.se/',
#     next_func=ProcessRun.frontpage.name,
#     new_parser=False,
#     breakers=10000,
#     curl=True
# )
# agent.create_frontpage(
#     cats_xpath='//li[@class="li0 has-ul"]',
#     name_xpath='(a|span)//text()',
#     url_xpath=''
# )
# agent.create_revlist(
#     revs_xpath='//h2[contains(@class, "product-title")]/a',
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
