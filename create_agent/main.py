import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="16512"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://gamecritics.com/reviews',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=7000,
    # curl=True
)
# agent.create_frontpage(
#     cats_xpath='//ul/li//a[contains(., " Reviews") and not(contains(., "All Reviews"))]',
#     name_xpath='text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//h3[contains(@class, "title")]//a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//a[contains(@class, "next")]/@href',
)
agent.create_review(
    date_xpath='//time/@datetime',
    author_xpath='//span[@class="entry-author"]/a/text()',
    author_url_xpath='//span[@class="entry-author"]/a/@href',
    grade_overall_xpath='//p[contains(., "Rating")]/text()',
    pros_xpath='',
    cons_xpath='',
    summary_xpath='//h2[@class="wp-block-heading"]//text()',
    conclusion_xpath='(//p[contains(., "Disclosures")]|//p[contains(., "Disclosures")]/following-sibling::p)//text()[not(contains(., ":"))]',
    excerpt_with_concl_xpath='',
    excerpt_xpath='///p[count(preceding-sibling::hr)=1]//text()'
)
