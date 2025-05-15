import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="18352"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://www.theverge.com/reviews/',
    next_func=ProcessRun.catlist.name,
    new_parser=False,
    breakers=3000,
    # curl=True
)
# agent.create_frontpage(
#     cats_xpath='//ul/li//a[contains(., " Reviews") and not(contains(., "All Reviews"))]',
#     name_xpath='text()',
#     url_xpath='@href'
# )
# agent.create_revlist(
#     revs_xpath='//a[contains(@class, "comments-link")]',
#     name_title="title",
#     name_title_xpath='text()',
#     url_xpath='@href',
#     prod_rev="review",
#     next_url_xpath='//a[@rel="next"]/@href',
# )
# agent.create_review(
#     date_xpath='//meta[@property="article:published_time"]/@content',
#     author_xpath='//a[contains(@href, "https://www.theverge.com/authors/")]/text()',
#     author_url_xpath='//a[contains(@href, "https://www.theverge.com/authors/")]/@href',
#     grade_overall_xpath='//div[contains(@class, "scorecard ")]/div/div[p[contains(., "Verge Score")]]/p[not(contains(., "Verge Score"))]//text()',
#     pros_xpath='//h4[contains(., "The Good")]/following-sibling::ul[1]/li',
#     cons_xpath='//h4[contains(., "The Bad")]/following-sibling::ul[1]/li',
#     summary_xpath='//div[@class=""]/p[contains(@class, "dangerously")]//text()',
#     conclusion_xpath='//',
#     excerpt_with_concl_xpath='.',
#     excerpt_xpath='//div[contains(@class, "body-component")]/p[not(.//em[regexp:test(., "Photography by|Update, ")])]//text()'
# )
