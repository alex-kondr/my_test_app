from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.mirrorlessons.com/reviews/camera-reviews/', use='curl', force_charset='utf-8'), process_revlist, dict(cat='Mirrorless camera'))
    session.queue(Request('https://www.mirrorlessons.com/reviews/lens-reviews/', use='curl', force_charset='utf-8'), process_revlist, dict(cat='Mirrorless lens'))
    session.queue(Request('http://www.mirrorlessons.com/reviews/accessory-reviews/', use='curl', force_charset='utf-8'), process_revlist, dict(cat='Accessory'))


def process_revlist(data, context, session):
    revs = data.xpath('//ul[@class="lcp_catlist"]/li//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

# no next page


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' review – ')[0].replace('Review of the ', '').replace('Review of ', '').replace(' Review for ', '').replace('Hands-On with the ', '').replace(' Review', '').replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]//text()').string(multiple=True)
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//p[contains(., "What I like")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[contains(., "What I don’t like")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p[not(@style or regexp:test(., "What I like|What I don’t like") or starts-with(normalize-space(.), "["))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p[not(contains(., "Main Specs") or starts-with(normalize-space(.), "["))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]/p[not(@style or regexp:test(., "What I like|What I don’t like") or contains(., "Main Specs") or starts-with(normalize-space(.), "["))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
