from agent import *
from models.products import *
import simplejson


URLS = ['https://www.latercera.com/pf/api/v3/content/fetch/story-feed-sections-fetch?query={%22feedOffset%22:offset,%22feedSize%22:12,%22fromComponent%22:%22result-list%22,%22includeSections%22:%22/mouse%22}&d=1098&mxId=00000000&_website=la-tercera', 'https://www.latercera.com/pf/api/v3/content/fetch/story-feed-sections-fetch?query={%22feedOffset%22:offset,%22feedSize%22:12,%22fromComponent%22:%22result-list%22,%22includeSections%22:%22/tecnologia%22}&d=1098&mxId=00000000&_website=la-tercera']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    for url in URLS:
        session.queue(Request(url.replace('offset', '0')), process_revlist, dict(cat_url=url))


def process_revlist(data, context, session):
    try:
        revs_json = simplejson.loads(data.content)
    except:
        return

    revs = revs_json.get('content_elements', [])
    for rev in revs:
        title = rev.get('headlines', {}).get('basic')
        url = 'https://www.latercera.com' + rev.get('websites', {}).get('la-tercera', {}).get('website_url')

        if 'reseña' in title.lower() or 'review' in title.lower():
            session.queue(Request(url), process_review, dict(url=url))

    offset = revs_json.get('next')
    if offset:
        session.queue(Request(context['cat_url'].replace('offset', str(offset))), process_revlist, dict(context))


def process_review(data, context, session):
    title = data.xpath('//div[contains(@class, "article")]/h1[contains(@class, "title")]//text()').string(multiple=True)

    product = Product()
    product.name = title.replace('Review del ', '').replace('Preview | ', '').replace('Reseña | ', '').replace('Review |', '').replace('Review| ', '').replace('Review: ', '').replace('Review ', '').replace(u'\L', '').replace(u' ', '').replace('Testament: ', '').strip(' |')
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('review-', '')
    product.category = data.xpath('//div[contains(@class, "heading")]/span[contains(@class, "section__name")]//text()').string(multiple=True)

    review = Review()
    review.type = 'pro'
    review.title = title.replace(u'\L', '').replace(u' ', '').strip()
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "author")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "author")]/@href').string()
    if not author:
        author = data.xpath('//meta[@name="author"]/@content').string()

    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//p[contains(., "A favor (Pros)")]/following-sibling::p[contains(., "✅")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;:✅')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[contains(., "En contra (Contras)")]/following-sibling::p[contains(., "❌")]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;:❌')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[contains(@class, "subtitle") and not(contains(., "⭐"))]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Veredict", "i")]/following-sibling::p[contains(@class, "article-body") and not(contains(., "*Los precios de los") or contains(., "⭐") or contains(., "✅") or contains(., "❌") or contains(., "(Pros)") or contains(., "(Contras)"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h4[regexp:test(., "conclusión", "i")]/following-sibling::p[contains(@class, "article-body") and not(contains(., "*Los precios de los") or contains(., "⭐") or contains(., "✅") or contains(., "❌") or contains(., "(Pros)") or contains(., "(Contras)"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Vale la pena")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Veredict", "i")]/preceding-sibling::p[contains(@class, "article-body") and not(contains(., "*Los precios de los") or contains(., "⭐") or contains(., "✅") or contains(., "❌") or contains(., "(Pros)") or contains(., "(Contras)"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h4[regexp:test(., "conclusión", "i")]/preceding-sibling::p[contains(@class, "article-body") and not(contains(., "*Los precios de los") or contains(., "⭐") or contains(., "✅") or contains(., "❌") or contains(., "(Pros)") or contains(., "(Contras)"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Vale la pena")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div/p[contains(@class, "article-body") and not(contains(., "*Los precios de los") or contains(., "⭐") or contains(., "✅") or contains(., "❌") or contains(., "(Pros)") or contains(., "(Contras)"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
