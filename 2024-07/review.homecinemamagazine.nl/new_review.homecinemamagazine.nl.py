from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://fwd.nl/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@class="channels-nav"]/li[@class=""]')
    for cat in cats:
        name = cat.xpath('.//a[contains(@class, "accent-color--")]//text()').string(multiple=True)
        url= cat.xpath('.//a[contains(., "Reviews")]/@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="card__body"]')
    for rev in revs:
        title = rev.xpath('.//h4[@class="card__title"]/text()').string()
        url = rev.xpath('.//a[@class="card__content"]/@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('De eerste reviews van de', '').replace('(Deel 2, uitgebreide review)', '').replace('Review en weggeef actie:', '').replace('Preview & unboxing', '').replace('Preview video:', '').replace('Eerste reviews', '').replace('Eerste review', '').replace('Review + Vlog:', '').replace('Hands-on review', '').replace('hands-on review', '').replace('Step-up review:', '').replace('Gadgettest:', '').replace('App review:', '').replace('App-review:', '').replace('Testpanel', '').replace('producten getest', '').replace('Preview:', '').replace('Review:', '').replace('Video:', '').replace('(video)', '').replace('(Magic Pen)', '').replace('Zomertest:', '').replace('Test:', '').replace('Review', '').replace('Nieuw:', '').replace('Update:', '').replace('reviews', '').replace('review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="author"]/@content').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="section--module--review__score"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[@class="section--module--review__pros-cons"]//div[contains(@class, " pros") or contains(@class, "pros ")]//li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="section--module--review__pros-cons"]//div[contains(@class, " cons") or contains(@class, "cons ")]//li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="intro__preview"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Samenvattend") or contains(., "Conclusie") or contains(., "conclusie")]/following-sibling::p[not(contains(., "Prijzen & Info"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Samenvattend") or contains(., "Conclusie") or contains(., "conclusie")]/preceding::div[@class="section__body"]/p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="section__body"]/p[not(contains(., "Prijzen & Info"))]//text()').string(multiple=True)

    if excerpt:

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
