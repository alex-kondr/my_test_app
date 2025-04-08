import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="17646"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://www.gameblog.fr/api/posts/load_more_posts/route/list_page/controller/components_controller/method/search_post_items/view_mode/full/sort_order/desc/offset/0/ppp/10/release_filter/a-venir/search_filters/Tech%2CHardware%20Tests%2Call%2Call%2C%2C%2C%2C%2C%2C%2C%2C%2C/limit/gameblog',
    next_func=ProcessRun.frontpage.name,
    new_parser=False,
    breakers=10000,
    curl=True
)
# agent.create_frontpage(
#     cats_xpath='//ul[@class="menu"]//a',
#     name_xpath='text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//div[@class="item-content-header"]',
    name_title="title",
    name_title_xpath='h2[@class="title"]/text()',
    url_xpath='a[contains(@class, "title")]/@href',
    prod_rev="review",
    next_url_xpath='',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content',
    author_xpath='//a[@class="name"]/text()',
    author_url_xpath='//a[@class="name"]/@href',
    grade_overall_xpath='0',
    pros_xpath='0',
    cons_xpath='0',
    summary_xpath='//p[@itemprop="description about"]//text()',
    conclusion_xpath='//h2[regexp:test(., "Végszó|Fnatic")]/following-sibling::p[@class="mgt0" or @class="mgt1"][not(s)]//text()',
    excerpt_with_concl_xpath='//h2[regexp:test(., "Végszó|Fnatic")]/preceding-sibling::p[@class="mgt0" or @class="mgt1"]//text()',
    excerpt_xpath='//div[contains(@class, "content-body")]/p[@class="mgt0" or @class="mgt1"]//text()'
)
