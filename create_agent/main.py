import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.slrlounge.com",
    )
agent.create_run(
    name_agent_for_test="SLR Lounge [US]",
    agent_id="19797",
    url='https://www.slrlounge.com/camera/',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=10000,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='//li[@class=""]/a',
#     name_xpath='text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//h3[contains(@class, "gb-headline-text")]/a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//link[@rel="next"]/@href',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content',
    author_xpath='//p[contains(@class, "gb-headline-text")]/a/text()',
    author_url_xpath='//p[contains(@class, "gb-headline-text")]/a/@href',
    grade_overall_xpath='!!!',
    pros_xpath='!!!',
    cons_xpath='!!!',
    summary_xpath='!!!',
    conclusion_xpath='//h2[contains(., "Conclusion")]/following-sibling::p[not(.//em or .//br)]//text()',
    excerpt_with_concl_xpath='//h2[contains(., "Conclusion")]/preceding-sibling::p//text()',
    excerpt_xpath='//div[@class="entry-content"]/p//text()'
)
