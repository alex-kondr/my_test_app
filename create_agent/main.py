import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="11910"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://logout.hu/cikkek/index.html',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=10000,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//ul[@class="menu"]//a',
#     name_xpath='text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//h4[@class="media-heading"]/a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//a[@rel="next"]/@href',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content',
    author_xpath='////a[@rel="author"]/span/text()',
    author_url_xpath='//a[@rel="author"]/@href',
    grade_overall_xpath='',
    pros_xpath='',
    cons_xpath='',
    summary_xpath='//p[@itemprop="description about"]//text()',
    conclusion_xpath='//h2[regexp:test(., "Végszó|Fnatic")]/following-sibling::p[@class="mgt0" or @class="mgt1"][not(s)]//text()',
    excerpt_with_concl_xpath='//h2[regexp:test(., "Végszó|Fnatic")]/preceding-sibling::p[@class="mgt0" or @class="mgt1"]//text()',
    excerpt_xpath='//div[contains(@class, "content-body")]/p[@class="mgt0" or @class="mgt1"]//text()'
)
