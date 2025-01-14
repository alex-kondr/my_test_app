from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://pctuning.cz/'), process_catlist, dict())
    session.queue(Request('https://pctuning.cz/story/software'), process_revlist, dict(cat="Software"))


def process_catlist(data, context, session):
    cats = data.xpath('(//div[span[contains(., "Hardware")]])[1]//ul[@class="header-menu__drawer-list"]//a')
    for cat in cats:
        name = "Hardware" + '|' + cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="un-card-headline"]//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Test ', '').replace(' v testu', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat'].replace(', ', '/')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    rev_json = data.xpath('''//script[contains(., "datePublished")]/text()''').string()
    if rev_json:
        rev_json = simplejson.loads(rev_json)

        date = rev_json.get('datePublished')
        if date:
            review.date = date.split('T')[0]

    author = data.xpath('//p[@class="post-header-info__name"]//a/text()').string()
    author_url = data.xpath('//p[@class="post-header-info__name"]//a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review-box__rating"]//div/@data-rating').string()
    if grade_overall:
        grade_overall = float(grade_overall) / 10
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    pros = data.xpath('//div[contains(@class, "proscons-pros")]//span[@class="un-list-item__text-secondary"]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "proscons-cons")]//span[@class="un-list-item__text-secondary"]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="post-body"]//p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@class="review-box__verdict"]/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    context['excerpt'] = data.xpath('//body/p//text()').string(multiple=True)

    next_url = data.xpath('//a[span[contains(., "Další")] and not(@disabled)]/@href').string()
    if next_url:
        page = 1
        title = data.xpath('//a[contains(@class, "post-chapters__item--active")]/text()').string() + ' - Pagina ' + str(page)
        review.add_property(type='pages', value=dict(title=title, url=review.url))

        session.do(Request(next_url), process_review_next, dict(context, product=product, review=review, url=next_url, page=page + 1))

    else:
        context['product'] = product
        context['review'] = review
        process_review_next(data, context, session)


def process_review_next(data, context, session):
    review = context['review']

    page = context.get('page', 1)
    if page > 1:
        title = data.xpath('//a[contains(@class, "post-chapters__item--active")]/text()').string() + ' - Pagina ' + str(page)
        review.add_property(type='pages', value=dict(title=title, url=context['url']))

        grade_overall = data.xpath('//div[@class="review-box__rating"]//div/@data-rating').string()
        if grade_overall:
            grade_overall = float(grade_overall) / 10
            review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

        pros = data.xpath('//div[contains(@class, "proscons-pros")]//span[@class="un-list-item__text-secondary"]')
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            review.add_property(type='pros', value=pro)

        cons = data.xpath('//div[contains(@class, "proscons-cons")]//span[@class="un-list-item__text-secondary"]')
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            review.add_property(type='cons', value=con)

        if 'verdikt' in title:
            conclusion = data.xpath('//body/p//text()').string(multiple=True)
        else:
            conclusion = data.xpath('//div[@class="review-box__verdict"]/p//text()').string(multiple=True)

            excerpt = data.xpath('//body/p//text()').string(multiple=True)
            if excerpt:
                context['excerpt'] += " " + excerpt

        if conclusion:
            context['conclusion'] = conclusion
            review.add_property(type='conclusion', value=conclusion)

    next_url = data.xpath('//a[span[contains(., "Další")] and not(@disabled)]/@href').string()
    if next_url:
        session.do(Request(next_url), process_review_next, dict(context, review=review, url=next_url, page=page + 1))

    elif context['excerpt']:
        if context.get('conclusion'):
            context['excerpt'] = context['excerpt'].replace(context['conclusion'], '').strip()

        review.add_property(type="excerpt", value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)