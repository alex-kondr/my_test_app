import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun, TypeAgent


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="743"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://uk.pcmag.com/article/review',
    next_func=ProcessRun.frontpage.name,
    new_parser=False,
    breakers=10000,
    # curl=True
)
agent.create_frontpage(
    cats_xpath='//a[contains(@class, "title")]',
    name_xpath='text()',
    url_xpath='@href'
)
agent.create_revlist(
    revs_xpath='//div[@class="swiper-slide"]/a[not(img)]',
    name_title=TypeAgent.review.value,
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev=TypeAgent.review.name,
    next_url_xpath='//link[@rel="next"]/@href',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content',
    author_xpath='/text()',
    author_url_xpath='/@href',
    grade_overall_xpath='//text()',
    pros_xpath='/li',
    cons_xpath='/li',
    summary_xpath='//text()',
    conclusion_xpath='//text()',
    excerpt_with_concl_xpath='//text()',
    excerpt_xpath='//text()'
)
