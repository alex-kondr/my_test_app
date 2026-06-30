from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://gpstracklog.com/our-gps-reviews', use='curl', force_charset='utf-8',), process_revlist, dict())


def process_revlist(data, context, session):
    cats = data.xpath('//div[@class="entry-content"]/h2')
    for cat in cats:
        cat_name = cat.xpath('text()').string()

        revs = cat.xpath('(following-sibling::*)[1]/li/a[1]')
        for rev in revs:
            name = rev.xpath('text()').string()
            url = rev.xpath('@href').string().split('#')[0]
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(cat=cat_name, name=name, url=url))

    # no next page


def process_review(data, context, session):
    if data.xpath('//h1[contains(., "Not Found, Error 404")]'):
        return

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '')
    product.category = context['cat'].replace(' reviews', '').strip()

    imgs = data.xpath('//img[contains(@src,"wp-content/uploads")]')
    for img in imgs:
        img_url = img.xpath('@src').string()
        alt = img.xpath('@alt').string()
        product.add_property(type='image', value=dict(src=img_url, alt=alt))

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[contains(@class, "title")]/text()').string()
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('(//h3[contains(em, " pros")]/following-sibling::*)[1]/li')
    if not pros:
        pros = data.xpath('(//p[contains(span, " pros")]/following-sibling::ul)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(em, " cons")]/following-sibling::*)[1]/li')
    if not cons:
        cons = data.xpath('(//p[contains(em, " cons")]/following-sibling::ul)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p[not(preceding-sibling::h2[contains(., "More")] or preceding-sibling::p[contains(.//strong, "More")] or contains(.//strong, "More"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p[not(preceding-sibling::h2[contains(., "More")] or preceding-sibling::p[contains(.//strong, "More")] or contains(.//strong, "More"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(.//strong, "Conclusion")]/following-sibling::p[not(preceding-sibling::h2[contains(., "More")] or preceding-sibling::p[contains(.//strong, "More")] or contains(.//strong, "More"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p[not(contains(strong, "UPDATE:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p[not(contains(strong, "UPDATE:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(.//strong, "Conclusion")]/preceding-sibling::p[not(contains(strong, "UPDATE:") or preceding-sibling::p[contains(span, " pros") or contains(em, " cons")] or contains(em, " cons") or contains(span, " pros"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]/p[not(contains(strong, "UPDATE:") or preceding-sibling::h2[contains(., "More")] or preceding-sibling::p[contains(.//strong, "More")] or contains(.//strong, "More"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
