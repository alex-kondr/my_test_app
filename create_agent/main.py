import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="19304"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://www.trailrunmag.com/category/shoe-reviews/',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=0,
    # curl=True
)
# agent.create_frontpage(
#     cats_xpath='//',
#     name_xpath='text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//h3[@class="h3"]/a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//link[@rel="next"]/@href',
)
agent.create_review(
    date_xpath='//',
    author_xpath='//',
    author_url_xpath='//',
    grade_overall_xpath='//',
    pros_xpath='//',
    cons_xpath='//',
    summary_xpath='//',
    conclusion_xpath='//',
    excerpt_with_concl_xpath='//',
    excerpt_xpath='//'
)
