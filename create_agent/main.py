import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm


agent = AgentForm(
    name="reviews.haus.de",
    )
agent.create_run(
    name_agent_for_test="Haus [DE]",
    agent_id="20205",
    url="https://www.campgarden.de/cg/pages/69092/geraete",
    next_func="revlist",
    new_parser=False,
    breakers=False,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='(//ul[@class="sub-menu"])[1]//a',
#     name_xpath='.//text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//div[@class="Internal-block"]/div[@class="Internal-Name"]/a',
    name_title="title",
    name_title_xpath='',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='',
)
agent.create_review(
    date_xpath='//div[@class="Template-ARTIKEL-DATUM"]/text()',
    author_xpath='//meta[@name="author"]/@content',
    grade_overall_xpath='',
    pros_xpath='',
    cons_xpath='',
    summary_xpath='//p[@class="Template-INTRO"]//text()',
    conclusion_xpath='//h3[contains(., "Fazit")]/following-sibling::p[not(preceding-sibling::h4)]//text()',
    excerpt_with_concl_xpath='//h3[contains(., "Fazit")]/preceding-sibling::p[not(@class)]//text()',
    excerpt_xpath='//div[@class="COL-3-INNER Artikel"]/p[not(@class or preceding-sibling::h4)]//text()'
)
