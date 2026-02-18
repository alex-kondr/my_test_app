from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://cse.google.com/cse/element/v1?rsz=filtered_cse&num=10&hl=uk&source=gcsc&start=0&cselibv=f71e4ed980f4c082&cx=0099769ad8b6d3d5e&q=review&safe=off&cse_tok=AEXjvhLUAa2A0yJD_IIRrKZM40wm%3A1771415353767&exp=cc%2Capo&fexp=121538238%2C121538239%2C73152292%2C73152290&callback=google.search.cse.api12566&rurl=https%3A%2F%2Fwww.latercera.com%2Fsearch%2F%3Fq%3Dreview'), process_revlist, dict())


def process_revlist(data, context, session):
    try:
        revs_json = simplejson.loads('{' + data.content.split('({')[-1].strip('( ;)'))
    except:
        return

    current_page = revs_json.get('cursor', {}).get('currentPageIndex', 0)
    if current_page < context.get('page', 0):
        return

    revs = revs_json.get('results', [])
    for rev in revs:
        title = rev.get('title')
        url = rev.get('url')

        if 'reseña' in title.lower() or 'review' in title.lower():
            session.queue(Request(url), process_review, dict(url=url))


    offset = context.get('offset', 0) + 10
    next_page = context.get('page', 0) + 1
    next_url = 'https://cse.google.com/cse/element/v1?rsz=filtered_cse&num=10&hl=uk&source=gcsc&start=' + str(offset) + '&cselibv=f71e4ed980f4c082&cx=0099769ad8b6d3d5e&q=review&safe=off&cse_tok=AEXjvhLUAa2A0yJD_IIRrKZM40wm%3A1771415353767&exp=cc%2Capo&fexp=121538238%2C121538239%2C73152292%2C73152290&callback=google.search.cse.api12566&rurl=https%3A%2F%2Fwww.latercera.com%2Fsearch%2F%3Fq%3Dreview'
    session.queue(Request(next_url), process_revlist, dict(offset=offset, page=next_page))


def process_review(data, context, session):
    title = data.xpath('//div[contains(@class, "article")]/h1[contains(@class, "title")]//text()').string(multiple=True)

    product = Product()
    product.name = title.replace('Reseña | ', '').replace('Review |', '').replace('Review| ', '').replace('Review: ', '').replace('Review ', '').replace(u'\L', '').replace(u' ', '').strip(' |')
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
