import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from create_agent.agent import AgentForm, ProcessRun, TypeAgent


agent = AgentForm(
    # name="reviews.fotokoch.de",
    agent_id="3305"
    )
agent.create_run(
    # name_agent_for_test="Fotokoch [DE]",
    # agent_id="20182",
    url='https://api.mobil.se/api/v1/article/?orderBy=published&htmlText=1&query=visibility_status:P%20AND%20published:[*%20NOW]%20AND%20NOT%20hidefromfp_time:[*%20NOW]%20AND%20(tag%3Aprodukttester%20OR%20tag%3A%22j%C3%A4mf%C3%B6rande%20tester%22)%20AND%20(tag%3Aapple%20OR%20tag%3Asamsung%20OR%20tag%3Axiaomi%20OR%20tag%3Agoogle%20OR%20tag%3Asony%20OR%20tag%3Amotorola%20OR%20tag%3Aoneplus%20OR%20tag%3Ahuawei%20OR%20tag%3Alenovo%20OR%20tag%3Anokia%20OR%20tag%3Anothing%20OR%20tag%3Aikea%20OR%20tag%3A%22andra%20tillverkare%22)%20AND%20(tag%3Asurfplatta%20OR%20tag%3Atelefon%20OR%20tag%3A%22h%C3%B6rlurar%20headset%22%20OR%20tag%3Ah%C3%B6gtalare%20OR%20tag%3A%22klockor%20armband%22%20OR%20tag%3A%22smarta%20hemmet%22%20OR%20tag%3Aoutdoor)&fields=*,-bodytext,-ai_*,-bodytextHTML&limit=280&site_id=2',
    next_func=ProcessRun.revlist.name,
    new_parser=False,
    breakers=0,
    # curl=True
)
# agent.create_frontpage(
#     cats_xpath='//p//a[contains(text(), "Reviews")]',
#     name_xpath='text()',
#     url_xpath='@href'
# )
agent.create_revlist(
    revs_xpath='//td/a[b]',
    name_title=TypeAgent.review.value,
    name_title_xpath='.//text()',
    url_xpath='@href',
    prod_rev=TypeAgent.review.name,
    next_url_xpath='//a[img[contains(@src, "arrow_right_green")]]/@href',
)
agent.create_review(
    date_xpath='//meta[@property="article:published_time"]/@content|//time/@datetime',
    author_xpath='/text()',
    author_url_xpath='/@href',
    grade_overall_xpath='//text()',
    pros_xpath='(//h3[contains(., "Pros")]/following-sibling::*)[1]/li',
    cons_xpath='(//h3[contains(., "Cons")]/following-sibling::*)[1]/li',
    summary_xpath='//text()',
    conclusion_xpath='//h3[contains(., "Conclusion")]/following-sibling::p//text()',
    excerpt_with_concl_xpath='//h3[contains(., "Conclusion")]/preceding-sibling::p//text()',
    excerpt_xpath='//text()'
)
