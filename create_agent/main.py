import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun, TypeAgent


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="20176"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='http://www.nintendoworldreport.com/review?region=All&system=All&status=All&type=All',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=9000,
    # curl=False
)
# agent.create_frontpage(
#     cats_xpath='//li[a[contains(text(), "Review ")]]/ul/li/a',
#     name_xpath='text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//table[@id="results"]/tbody/tr[td]',
    name_title=TypeAgent.review.value,
    name_title_xpath='td/a/text()',
    url_xpath='td/a/@href',
    prod_rev=TypeAgent.review.name,
    next_url_xpath='//link[@rel="next"]/@href|//a[contains(@class, "next")]/@href',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content|//time/@datetime',
    author_xpath='/text()',
    author_url_xpath='/@href',
    grade_overall_xpath='//text()',
    pros_xpath='(//h3[contains(., "Pros")]/following-sibling::*)[1]/li',
    cons_xpath='(//h3[contains(., "Cons")]/following-sibling::*)[1]/li',
    summary_xpath='//div[h3[contains(text(), "Summary")]]/div//text()',
    conclusion_xpath='//h3[contains(., "Conclusion")]/following-sibling::p//text()',
    excerpt_with_concl_xpath='//h3[contains(., "Conclusion")]/preceding-sibling::p//text()',
    excerpt_xpath='//text()'
)
