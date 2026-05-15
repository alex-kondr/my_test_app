from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://keyboardkings.com/category/resources/keyboard-reviews/", use='curl', max_age=0), process_revlist, dict(cat='Keyboards'))
    session.queue(Request("https://keyboardkings.com/category/resources/chair-reviews/", use='curl', max_age=0), process_revlist, dict(cat='Chairs'))
    session.queue(Request("https://keyboardkings.com/category/resources/keyboard-mice-reviews/", use='curl', max_age=0), process_revlist, dict(cat='Mice'))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="copy-container"]/p/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if title and 'Top ' not in title and 'review' in title.lower() and url:
            session.queue(Request(url, use='curl', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Review', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = context['cat']

    product.url = data.xpath('//p[@class="has-background"]//a[contains(@href, "https://www.amazon.com/")]/@href').string()
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

    pros = data.xpath('//table[contains(thead/tr/th, "Pros")]/tbody/tr/td[1]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//table[contains(thead/tr/th[2], "Cons")]/tbody/tr/td[2]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(text(), "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(text(), "Final Thoughts")]/following-sibling::p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h3[contains(., "Final Thoughts")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@itemprop="articleBody"]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
