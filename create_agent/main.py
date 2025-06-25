import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun, TypeAgent


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="11878"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://fotovilag.hu/content/index/cat/2',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=0,
    # curl=True
)
# agent.create_frontpage(
#     cats_xpath='(//li[a[contains(., "Testy")]])[1]/ul/li[not(contains(@class, "nested"))]/a[not(img)]',
#     name_xpath='text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//div[contains(@class, "content-list")]',
    name_title=TypeAgent.review.value,
    name_title_xpath='h2/text()',
    url_xpath='.//a/@href',
    prod_rev=TypeAgent.review.name,
    next_url_xpath='//li[@title="kovetkezo"]/a/@href',
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
