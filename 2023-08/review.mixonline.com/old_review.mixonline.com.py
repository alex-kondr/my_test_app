from agent import *
from models.products import *
import re
import simplejson


cats = ['MICROPHONE', 'Plug-in', 'DAW', 'MONITOR', 'AUDIO INTERFACE', 'EQUALIZER', 'MIC PREAMP', 'CONSOLE', 'WIRELESS SYSTEMS', 'REVERB', 'COMPRESSOR', 'LOUDSPEAKER']


def run(context, session):
    session.queue(Request('https://www.mixonline.com/technology/reviews', use="curl"), process_revlist, dict())


def process_revlist(data, context, session):
    for rev in data.xpath("//a[@class='post-title']"):
        url = rev.xpath("@href").string()
        title = rev.xpath("following-sibling::h2/text()").string(multiple=True)
        if url and title:
            session.queue(Request(url, use="curl"), process_review, dict(url=url, title=title))

    base_url = "https://www.mixonline.com/wp-admin/admin-ajax.php?id=archive&post_id=99&slug=reviews&canonical_url=https%%3A%%2F%%2Fwww.mixonline.com%%2Ftechnology%%2Freviews&posts_per_page=42&page=%d&offset=42&post_type=post&repeater=default&seo_start_page=2&theme_repeater=alm-archive.php&preloaded=false&preloaded_amount=0&category=reviews&order=DESC&orderby=date&action=alm_get_posts&query_type=standard"
    nexturl = base_url % (1)
    session.queue(Request(nexturl, use="curl"), process_nextpage, dict(context, page=1))


def process_nextpage(data, context, session):
    content = simplejson.loads(data.content)
    revs_html = data.parse_fragment(content['html'].replace("\\", ""))

    for rev in revs_html.xpath("//a[@class='post-title']"):
        url = rev.xpath("@href").string()
        title = rev.xpath("following-sibling::h2/text()").string(multiple=True)
        if url and title:
            session.queue(Request(url, use="curl"), process_review, dict(url=url, title=title))

    try:
        total = int(data.xpath("//div[contains(., 'totalpost')]/text()").string(multiple=True).replace("\n", "").replace("\t", "").split("\"totalposts\":")[-1].split(",")[0])
        if total - 42 * (context['page'] + 1) > 0:
            nexturl = "https://www.mixonline.com/wp-admin/admin-ajax.php?id=archive&post_id=99&slug=reviews&canonical_url=https%%3A%%2F%%2Fwww.mixonline.com%%2Ftechnology%%2Freviews&posts_per_page=42&page=%d&offset=42&post_type=post&repeater=default&seo_start_page=2&theme_repeater=alm-archive.php&preloaded=false&preloaded_amount=0&category=reviews&order=DESC&orderby=date&action=alm_get_posts&query_type=standard" % (context['page']+1)
            session.queue(Request(nexturl, use="curl"), process_nextpage, dict(context, page=context['page']+1))
    except ValueError:  # Last page doesn't have info
        pass


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.category = data.xpath("//div[@class='col-12']/p/a[not(contains(., 'Review'))][last()]/text()").string()
    product.manufacturer = data.xpath("//div[@id='main']//p[contains(., 'COMPANY') or contains(., 'Company')]/text()").string()
    product.ssid = context['url'].split("/")[-1]

    name = re_search_once("^Review: (.*)$", context['title'])
    if not name:
        name = re_search_once("^(.*) Review$", context['title'])
    if not name:
        name = re_search_once("^Field Test: (.*)$", context['title'])
    if not name:
        name = context['title']
    product.name = name

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = data.xpath("//div[@id='main']/article/@id").string()
    review.date = data.xpath("//time[@class='updated']/@datetime").string()

    author = data.xpath("//p[@class='byline vcard']/a").first()
    if author:
        name = author.xpath("text()").string()
        url = author.xpath("@href").string()
        review.authors.append(Person(name=name, ssid=name, url=url))

    conclusion = data.xpath("//div[@id='main']//p[contains(., 'Summary') or contains(., 'SUMMARY')]/preceding-sibling::p[1]/text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[@id='main']//h2//*[contains(., 'Summary') or contains(., 'SUMMARY')]/preceding::p[1]/text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[@id='main']//p[contains(., 'TRY THIS')]/following-sibling::p[1]//text()").string()
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    if not conclusion:
        excerpt = data.xpath("//div[@id='main']/section/following-sibling::p/text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    summary = data.xpath("//p[@class='excerpt']/text()").string()
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

    pros = data.xpath("//div[@id='main']//p[contains(., 'PROS') or contains(., 'Pros')]/text()").string()
    cons = data.xpath("//div[@id='main']//p[contains(., 'CONS') or contains(., 'Cons')]/text()").string()
    if pros and cons and pros == cons:  # Pros and Cons in some articles are made in a strange way
        pros_cons = data.xpath("//div[@id='main']//p[contains(., 'PROS') or contains(., 'Pros')]/text()")
        pros_cons = [pro_con.string() for pro_con in pros_cons if len(pro_con.string()) > 0]
        if len(pros_cons) > 2:
            pros = pros_cons[-2]
            cons = pros_cons[-1]

    if pros:
        review.add_property(type="pros", value=pros)

    if cons:
        review.add_property(type="cons", value=cons)

    tags = data.xpath("//p[@class='footer-tags tags']/a")
    for tag in tags:
        for cat in cats:
            if cat.lower() in tag.xpath("text()").string().lower():
                product.category = tag.xpath("text()").string()
                break

    product.reviews.append(review)
    session.emit(product)
