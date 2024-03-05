from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.makeuseof.com/category/product-reviews/', use='curl'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h5[@class="display-card-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_review, dict(title=title, url=url))

    next_page = data.xpath('//a[contains(@class, "next")]')
    if next_page:
        next_page = context.get('page', 1) + 1
        session.queue(Request('https://www.makeuseof.com/category/product-reviews/' + str(next_page) + '/', use='curl'), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(':')[0].replace('Review', '').replace('review', '').strip()
    product.ssid = context['url'].split('/')[-2]

    product.category = data.xpath('//meta[@property="article:section"]/@content[not(contains(., "Reviews"))]').string()
    if not product.category:
        product.category = 'Technik'

    product.url = data.xpath('//div[@class="w-display-card-link"]/a/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.url = context['url']
    review.title = context['title']
    review.ssid = product.ssid

    date = data.xpath('//span[@class="meta_txt date"]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@class="meta_txt author"]/text()').string()
    author_url = data.xpath('//a[@class="meta_txt author"]/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="display-card-rating" or @class="raiting-number"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    summary = data.xpath('//p[@class="heading_excerpt"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    pros = data.xpath('//ul[@class="pro-list"]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    pros = data.xpath('//p[em[contains(., "Pros")]]')
    for pros_ in pros:
        pros_ = pros_.xpath('following-sibling::ul[1]/li')
        for pro in pros_:
            pro = pro.xpath('.//text()').string(multiple=True)
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="con-list"]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    cons = data.xpath('//p[em[contains(., "Cons")]]')
    for cons_ in cons:
        cons_ = cons_.xpath('following-sibling::ul[1]/li')
        for con in cons_:
            con = con.xpath('.//text()').string(multiple=True)
            review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Verdict") or contains(., "Conclusion")]/following-sibling::p[not(@class or .//small)]//text()').string(multiple=True)
    faqs = data.xpath('//h2[contains(., "FAQ")]/following-sibling::p[not(@class)]')
    if conclusion:
        for faq in faqs:
            faq = faq.xpath('.//text()').string(multiple=True)
            conclusion = conclusion.replace(faq, '')

        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Verdict") or contains(., "Conclusion")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="content-block-regular"]//p[not(@class or .//small)]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
