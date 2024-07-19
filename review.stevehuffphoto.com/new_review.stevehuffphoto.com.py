from agent import *
from models.products import *


XCAT = ['IN USE', 'News']


def run(context, session):
    session.queue(Request('https://www.stevehuffphoto.com/all-reviews/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//span[@style="font-size: 14pt;"]//a')
    for cat in cats:
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//p[not(@style)]//a')
    for rev in revs:
        title = rev.xpath('.//text()').string(multiple=True)
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review', '').replace('review','').strip()
    product.ssid = context['url'].split('/')[-2]

    product.url = data.xpath('//a[contains(@href, "bhpho.to") and (contains(., "You can buy") or contains(., "you can see that offer"))]/@href').string()
    if not product.url:
        product.url = context['url']

    cats = data.xpath('(//span[@class="entry-meta-categories"])[1]/a/text()').strings()
    if cats:
        product.category = '|'.join([cat.replace('Review', '').replace('review', '').strip() for cat in cats if cat.strip() not in XCAT])
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    review.authors.append(Person(name='Steve Huff', ssid='stevehuff'))

    pros = data.xpath('(//p[regexp:test(., "^PROS$")]/following-sibling::ol|//p[regexp:test(., "^PROS$")]/following-sibling::ul)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p[regexp:test(., "^CONS$")]/following-sibling::ol|//p[regexp:test(., "^CONS$")]/following-sibling::ul)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    conclusions = data.xpath('//p[.//strong[contains(., "Conclusion")]]/following-sibling::p[not(contains(., "Where to Buy") or contains(.//@href, "bhpho.to") or contains(., "You can also follow me"))]//text()').strings()
    if conclusions:
        conclusion = ' '.join([concl.strip() for concl in conclusions])
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[.//strong[contains(., "Conclusion")]]/preceding-sibling::p[not(.//span[@style="font-size: 14pt;"] or contains(., "By Steve Huff") or contains(., "specs:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(contains(., "Where to Buy") or contains(.//@href, "bhpho.to") or contains(., "You can also follow me") or .//span[@style="font-size: 14pt;"] or contains(., "By Steve Huff") or contains(., "specs:") or .//span[contains(., "PROS") or contains(., "CONS")])]//text()').string(multiple=True)

    if excerpt:
        for concl in conclusions:
            excerpt = excerpt.replace(concl.strip(), '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
