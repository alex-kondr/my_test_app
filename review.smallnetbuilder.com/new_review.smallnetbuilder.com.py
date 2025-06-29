from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.smallnetbuilder.com/wireless/wireless-reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('Product Guide')[0].replace(' Reviewed', '').split(' Review')[0].split(' Retest')[0].strip()
    product.ssid = context['url'].split('/')[-2]
    product.category = 'Wireless'

    product.url = data.xpath('//a[contains(@href, "https://www.amazon.com/")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="twitter:data1"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//tr[contains(., "Pros")]/td[not(contains(., "Pros"))]//text()')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//tr[contains(., "Cons")]/td[not(contains(., "Cons"))]//text()')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[@id="conclusion" or normalize-space(text())="Conclusion"]/following-sibling::p[not(a[contains(@href, "https://www.amazon.com/")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(., "Closing Thoughts")]/following-sibling::p[not(@class)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//tr[contains(., "Summary")]/td[not(contains(., "Summary"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[@id="conclusion" or normalize-space(text())="Conclusion"]/preceding-sibling::p[not(a[contains(@href, "https://www.amazon.com/")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h3[contains(., "Closing Thoughts")]/preceding-sibling::p[not(@class or a[contains(@href, "https://www.amazon.com/")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body/p[not(a[contains(@href, "https://www.amazon.com/")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
