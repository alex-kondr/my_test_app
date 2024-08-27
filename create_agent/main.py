import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm


agent = AgentForm(
    name="reviews.jardins-loisirs.com-fr",
    )
agent.create_run(
    name_agent_for_test="Jardins-loisirs.com [FR]",
    agent_id="20201",
    url="https://www.jardins-loisirs.com/",
    next_func="frontpage",
    new_parser=False,
    breakers="10000",
    curl=False
)
# agent.create_revlist(
#     revs_xpath='//div[contains(@class, "testOverviewPart")]',
#     name_title="title",
#     name_title_xpath='div[@class="testOverviewFac"]//text()',
#     url_xpath='a/@href',
#     prod_rev="review",
#     next_url_xpath='//a[img[@alt="eine Seite vor"]]/@href',
# )
# agent.create_review(
#     date_xpath='//tr[contains(., "Datum")]/td[not(contains(., "Datum"))]/text()',
#     author_xpath='//tr[contains(., "Autor")]//a/text()',
#     grade_overall_xpath='//div[@class="testreviewContent"]//@alt',
#     pros_xpath="",
#     cons_xpath="",
#     summary_xpath='//p[@class="introduction"]//text()',
#     conclusion_xpath='//h3[contains(., "Fazit")]/following-sibling::text()',
#     excerpt_with_concl_xpath='//h3[contains(., "Fazit")]/preceding-sibling::p[not(@class)]//text()|//h3[contains(., "Fazit")]/preceding-sibling::text()',
#     excerpt_xpath='//div[@id="block-testbericht"]/p[not(@class)]|//div[@id="block-testbericht"]/text()'
# )
