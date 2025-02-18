from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.popsci.com/category/gear/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[contains(@class, "tag-list-item")]/a')
    if cats:
        for cat in cats:
            context['cat'] = context.get('cat', '') + '|' + cat.xpath('text()').string()
            url = cat.xpath('@href').string()
            session.queue(Request(url), process_catlist, dict(context))
    else:
        context['cat'] = context['cat'].strip('|')

        process_revlist(data, context, session)


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "post-content")]')
    for rev in revs:
        title = rev.xpath('.//span[contains(@class, "desktop")]/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    if 'The best' in context['title'] or ('The' in context['title'] and 'greatest' in context['title']):
        process_reviews(data, context, session)
        return

    product = Product()
    product.name = context['title']
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = context['cat']

    product.url = data.xpath('//a[contains(@class, "product-card-link")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@name="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    authors = data.xpath('//p[contains(@class, "item-author")]//a')
    for author in authors:
        author = author.xpath('text()').string()
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//p[contains(., "Pros")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[contains(., "Cons")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "article-dek font-secondary")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "verdict", "i")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "verdict", "i")]/preceding-sibling::p[not(regexp:test(., "Pros|Cons"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="content-wrapper"]/p[not(regexp:test(., "Pros|Cons"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    revs = data.xpath('//h3[@class="wp-block-heading" and a]')
    if not revs:
        revs = data.xpath('//h3[@class="wp-block-heading" and not(contains(., "More deals"))]')

    for i, rev in enumerate(revs, start=1):
        product = Product()
        product.name = rev.xpath('.//text()').string(multiple=True).replace('Best overall:', '').strip()
        product.ssid = product.name.strip().lower().replace(' ', '-')
        product.category = context['cat']

        product.url = rev.xpath('following-sibling::button[count(preceding-sibling::h3[@class="wp-block-heading" and a]) = {}]/a[contains(@class, "product-button-link")]/@href'.format(i)).string()
        if not product.url:
            product.url = context['url']

        review = Review()
        review.type = 'pro'
        review.url = context['url']
        review.ssid = product.ssid
        review.title = rev.xpath('.//text()').string(multiple=True)

        date = data.xpath('//meta[@name="article:published_time"]/@content').string()
        if date:
            review.date = date.split('T')[0]

        authors = data.xpath('//p[contains(@class, "item-author")]//a')
        for author in authors:
            author = author.xpath('text()').string()
            review.authors.append(Person(name=author, ssid=author))

        pros = data.xpath('following-sibling::div[count(preceding-sibling::h3[@class="wp-block-heading" and a]) = {}]/div[h4[contains(., "Pros")]]//li'.format(i))
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            review.add_property(type='pros', value=pro)

        cons = data.xpath('following-sibling::div[count(preceding-sibling::h3[@class="wp-block-heading" and a]) = {}]/div[h4[contains(., "Cons")]]//li'.format(i))
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            review.add_property(type='cons', value=con)

        conclusion = rev.xpath('following-sibling::p[count(preceding-sibling::h3[@class="wp-block-heading" and a]) = {}][not(contains(., "Specs")) and contains(., "Why it made the cut")]/text()'.format(i)).string()
        if conclusion:
            review.add_property(type='conclusion', value=conclusion)

        excerpt = rev.xpath('following-sibling::p[count(preceding-sibling::h3[@class="wp-block-heading" and a]) = {}][not(contains(., "Specs") or contains(., "Why it made the cut"))]//text()'.format(i)).string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
