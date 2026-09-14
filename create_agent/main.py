import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun, TypeAgent


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="18605",
    new_agent=True
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://www.4tochki.ru/',
    next_func=ProcessRun.frontpage.name,
    new_parser=False,
    breakers=10000,
    # curl=False
)
agent.create_frontpage(
    cats_xpath='//ul[contains(@class, "js-main-nav")]//li[contains(@class, "has-dropdown")]',
    name_xpath='div/a//text()',
    url_xpath='a/@href'
)
agent.create_revlist(
    revs_xpath='//div[contains(@class, "item__middle") and div[contains(@class, "item__name")]]',
    name_title=TypeAgent.review.value,
    name_title_xpath='div[contains(@class, "item__name")]/a/text()',
    url_xpath='div[contains(@class, "item__name")]/a/@href',
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
