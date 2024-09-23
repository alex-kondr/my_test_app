import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    name="review.all-nintendo.fr",
    )
agent.create_run(
    name_agent_for_test="All-Nintendo [FR]",
    agent_id="4902",
    url="https://www.all-nintendo.com/category/tests/",
    next_func=ProcessRun.revlist.name,
    new_parser=True,
    breakers=False,
    curl=False
)
# agent.create_frontpage(
#     cats_xpath='(//ul[@class="flex flex-col"])[1]//a',
#     name_xpath='text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//h2[@class="post-title"]/a',
    name_title="title",
    name_title_xpath='text()',
    url_xpath='@href',
    prod_rev="review",
    next_url_xpath='//link[@rel="next"]/@href',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content',
    author_xpath='//meta[@name="author"]/@content',
    author_url_xpath='',
    grade_overall_xpath='',
    pros_xpath='//p[contains(., "Les trucs cools du Jeu")]/following-sibling::ul[1]/li',
    cons_xpath='//p[contains(., "Les petits bémols")]/following-sibling::ul[1]/li',
    summary_xpath='',
    conclusion_xpath='//h2[regexp:test(., "conclusion", "i")]/following-sibling::p//text()',
    excerpt_with_concl_xpath='//h2[regexp:test(., "conclusion", "i")]/preceding-sibling::p[not(contains(., "Les trucs cools du Jeu") or contains(., "Les petits bémols") or contains(., "Q :"))]//text()',
    excerpt_xpath='//div[@itemprop="articleBody"]//p[not(contains(., "Les trucs cools du Jeu") or contains(., "Les petits bémols") or contains(., "Q :"))]//text()'
)
