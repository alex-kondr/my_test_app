import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm


agent = AgentForm(
    name="reviews.meilleur-robot-tondeuse.fr",
    )
agent.create_run(
    name_agent_for_test="Meilleur Robot Rondeuse [FR]",
    agent_id="20202",
    url="https://www.meilleur-robot-tondeuse.fr/",
    next_func="frontpage",
    new_parser=False,
    breakers=False,
    curl=False
)
agent.create_frontpage(
    cats_xpath='(//ul[@class="sub-menu"])[1]//a',
    name_xpath='.//text()',
    url_xpath='@href'
)
# agent.create_revlist(
#     revs_xpath='//div[contains(@class, "testOverviewPart")]',
#     name_title="title",
#     name_title_xpath='div[@class="testOverviewFac"]//text()',
#     url_xpath='a/@href',
#     prod_rev="review",
#     next_url_xpath='//a[img[@alt="eine Seite vor"]]/@href',
# )
agent.create_review(
    date_xpath='meta[@property="article:published_time"]/@content',
    author_xpath='//span[@class="author-name"]/text()',
    grade_overall_xpath='//span[@class="review-total-box"]/text()',
    pros_xpath='//div[@class="su-service" and contains(., "Avantages")]//li',
    cons_xpath='//div[@class="su-service" and contains(., "Inconvénients")]/following-sibling::div[@class="su-service"]//li',
    summary_xpath='',
    conclusion_xpath='//h2[contains(., "Conclusion")]/following-sibling::p//text()',
    excerpt_with_concl_xpath='//h2[contains(., "Conclusion")]/preceding-sibling::p//text()',
    excerpt_xpath='//div[@itemprop="text"]/p//text()'
)
