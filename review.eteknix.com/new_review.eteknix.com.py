from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.eteknix.com/', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[a[contains(text(), "Reviews")]]//ul//a[not(contains(., "All"))]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' Tested – ')[0].replace('Tested – ', '').replace('Was I Wrong? – ', '').split(' Re-Review – ')[0].split(' – ')[0].replace(' Re-Review!', '').replace(' Preview', '').replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if not date:
        date = data.xpath('//div[@class="entry-header"]/div/span[contains(@class, "date meta-item")]/text()').string()

    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "author-name")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "author-name")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    context['conclusion'] = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if context['conclusion']:
        context['conclusion'] = context['conclusion'].replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=context['conclusion'])

    context['excerpt'] = data.xpath('//div[contains(@class, "content")]/p//text()').string(multiple=True)

    context['product'] = product

    pages = data.xpath('//a[@class="post-page-numbers" and not(contains(., "Next page"))]')
    if pages:
        title = review.title + " - Pagina 1"
        review.add_property(type='pages', value=dict(title=title, url=review.url))

        for i, page in enumerate(pages, start=2):
            title = review.title + " - Pagina " + str(i)
            page_url = page.xpath('@href').string()
            review.add_property(type='pages', value=dict(title=title, url=page_url))

        session.do(Request(page_url, use='curl', force_charset='utf-8', max_age=0), process_review_last, dict(context, review=review, pages=True))

    else:
        context['review'] = review
        process_review_last(data, context, session)


def process_review_last(data, context, session):
    review = context['review']

    pros = data.xpath('//h2[contains(., "Pros")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.replace(u'\uFEFF', '').strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//h2[contains(., "Cons")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.replace(u'\uFEFF', '').strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if context.get('pages'):
        context['conclusion'] = data.xpath('//div[contains(@class, "content")]/p//text()').string(multiple=True)
        if context['conclusion']:
            context['conclusion'] = context['conclusion'].replace(u'\uFEFF', '').strip()
            review.add_property(type='conclusion', value=context['conclusion'])

    if context['excerpt']:
        context['excerpt'] = context['excerpt'].replace(u'\uFEFF', '').strip()

        if context['conclusion']:
            context['excerpt'] = context['excerpt'].replace(context['conclusion'], '').strip()

        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
