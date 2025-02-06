import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.bordspeler.nl",
    )
# agent.create_run(
#     name_agent_for_test="Bordspeler.nl [NL]",
#     agent_id="19950",
#     url='https://bordspeler.nl/category/op-reis/',
#     next_func=ProcessRun.revlist.name,
#     new_parser=False,
#     breakers=False,
#     curl=False
# )
# agent.create_frontpage(
#     cats_xpath='//div[contains(@class, "category-card-category-card")]',
#     name_xpath='span/text()',
#     url_xpath='a/@href'
# )
# agent.create_revlist(
#     revs_xpath='//h4[@class="elementor-post__title"]/a',
#     name_title="title",
#     name_title_xpath='text()',
#     url_xpath='@href',
#     prod_rev="review",
#     next_url_xpath='//a[@class="page-numbers next"]/@href',
# )
agent.create_review(
    date_xpath='//span[contains(@class, "item--type-date")]/text()',
    author_xpath='//span[contains(@class, "item--type-author")]/text()',
    author_url_xpath='',
    grade_overall_xpath='',
    pros_xpath='',
    cons_xpath='',
    summary_xpath='',
    conclusion_xpath='//h2[contains(., "Ten slotte")]/following-sibling::p[not(@style)]//text()',
    excerpt_with_concl_xpath='//h2[contains(., "Ten slotte")]/preceding-sibling::p[not(@style)]//text()',
    excerpt_xpath='//div[contains(@class, "post-content")]//p[not(@style)]//text()'
)
