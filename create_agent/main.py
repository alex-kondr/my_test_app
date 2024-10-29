import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.firstpost.com",
    )
# agent.create_run(
#     name_agent_for_test="Tech 2 [IN]",
#     agent_id="19682",
#     url='https://api-mt.firstpost.com/nodeapi/v1/mfp/get-article-list?count=50&fields=images%2Cdisplay_headline%2Cweburl_r%2Cpost_type%2Cgallery%2Cstory_id%2Cvideo_type%2Ccreated_at%2Cupdated_at&filter=%7B%22categories.slug%22%3A%22reviews%22%7D&offset=0&section=category&sectionCount=7&sectionFilter=%7B%22categories.slug%22%3A%22reviews%22%7D&sortBy=updated_at&subSection=reviews',
#     next_func=ProcessRun.revlist.name,
#     new_parser=False,
#     breakers=6000,
#     curl=True
# )
# agent.create_frontpage(
#     cats_xpath='//li[contains(., "Thema’s")]/ul//a',
#     name_xpath='.//text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//div[contains(@class, "sub-cat-list")]',
#     name_title="title",
#     name_title_xpath='p/text()',
#     url_xpath='a/@href',
#     prod_rev="review",
#     next_url_xpath='//link[@rel="next"]/@href',
# )
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content',
    author_xpath='//div[@class="art-dtls-info"]/a/text()',
    author_url_xpath='//div[@class="art-dtls-info"]/a/@href',
    grade_overall_xpath='//p[contains(., "Rating:")]/text()[regexp:test(., "\d.?\d?/\d")]',
    pros_xpath='//p[strong[contains(., "Pros")]]/text()',
    cons_xpath='//p[strong[contains(., "Cons")]]/text()',
    summary_xpath='//span[@class="less-cont"]//text()',
    conclusion_xpath='//p[strong[contains(., "Verdict")]]/text()|//p[strong[contains(., "Verdict")]]/following-sibling::p//text()',
    excerpt_with_concl_xpath='//p[strong[contains(., "Verdict")]]/preceding-sibling::p[not(strong[regexp:test(., "Pros|Cons|Rating")])]//text()[not(contains(., "Review:"))]',
    excerpt_xpath='//div[contains(@class, "content")]/p[not(strong[regexp:test(., "Pros|Cons|Rating")])]//text()[not(contains(., "Review:"))]'
)
