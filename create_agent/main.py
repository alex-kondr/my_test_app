import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.computable.nl",
    )
agent.create_run(
    name_agent_for_test="Computable [NL]",
    agent_id="17632",
    url='https://www.computable.nl/',
    next_func=ProcessRun.frontpage.name,
    new_parser=False,
    breakers=3000,
    curl=False
)
agent.create_frontpage(
    cats_xpath='//li[contains(., "Thema’s")]/ul//a',
    name_xpath='.//text()',
    url_xpath='@href'
)
agent.create_revlist(
    revs_xpath='(//h3|//h2)[@class="entry-title"]/a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//link[@rel="next"]/@href',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content',
    author_xpath='//a[contains(@class, "entry-author-name")]/text()',
    author_url_xpath='//a[contains(@class, "entry-author-name")]/@href',
    grade_overall_xpath='',
    pros_xpath='',
    cons_xpath='',
    summary_xpath='(//div[@class="entry-content"]/p)[1]/strong//text()',
    conclusion_xpath='',
    excerpt_with_concl_xpath='',
    excerpt_xpath='(//div[@class="entry-content"]/p|//div[@class="entry-content"]/h5)//text()'
)
