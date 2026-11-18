from agent import *
from models.products import *


XCAT = ["Aktuality", "Software"]


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request("http://www.ddworld.cz/", use='curl'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath("//ul[@id='horiznav']/li[@class='parent']")
    for cat in cats:
        name = cat.xpath("span/a/text()").string()

        if name not in XCAT:
            cats1 = cat.xpath("ul/li")
            if cats1:
                for cat1 in cats1:
                    cat1_name = cat1.xpath("span/a/text()").string()

                    subcats = cat1.xpath("ul/li")
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.xpath("span/a/text()").string()
                            url = subcat.xpath("span/a/@href").string()
                            session.queue(Request(url, use='curl'), process_revlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                    else:
                        url = cat1.xpath("span/a/@href").string()
                        session.queue(Request(url, use='curl'), process_revlist, dict(cat=name+'|'+cat1_name))
            else:
                url = cat.xpath("span/a/@href").string()
                session.queue(Request(url, use='curl'), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//td[a[contains(@name, "article_")]]')
    for rev in revs:
        ssid = rev.xpath('a/@name').string().split('_')[-1]
        title = rev.xpath('.//a[@class="contentpagetitle"]/text()').string()
        url = rev.xpath('.//a[@class="contentpagetitle"]/@href').string()
        if url:
            session.queue(Request(url, use='curl'), process_review, dict(context, title=title, ssid=ssid, url=url))

    next_url = data.xpath("//a[contains(text(), 'Následující')]/@href").string()
    if next_url:
        session.queue(Request(next_url.strip('+ '), use='curl'), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context["title"].split("– TEST a RECENZE")[0].split("Recenze:")[-1].split("TEST: ")[-1].split(' – TEST')[0].split(' TEST ')[0].split(' – PREVIEW:')[0].split("-")[0].split(' – ')[0].strip()
    product.url = context["url"]
    product.ssid = context["ssid"]
    product.category = context["cat"]

    review = Review()
    review.type = "pro"
    review.title = context["title"]
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath("//td[@class='createdate']//text()").string()
    if date:
        review.date = date.split(',')[-1].strip()

    author = data.xpath('//meta[@name="author"]/@content').string()
    author_url = data.xpath("//span[@class='small']//a/@href").string()
    if author and author_url:
        author_ssid = author_url.split('user=')[-1].split('&')[0]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath("//div[@id='content-area']//p[normalize-space(text()|font/text())]//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//table[@class='contentpaneopen']//tr//div//font//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//table[@class='contentpaneopen']//tr//p//font//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//table[@class='contentpaneopen']//tr//p//span//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//p//font//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//p//span//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div//font//text()").string(multiple=True)

    context['excerpt'] = excerpt
    context['product'] = product

    pages = data.xpath('//table[@class="contenttoc"]//a')
    if pages:
        for i, page in enumerate(pages, start=1):
            url = page.xpath('@href').string()
            review.add_property(type='pages', value=dict(title=review.title + ' - page ' + str(i), url=url))

        context['pages'] = i
        session.do(Request(url, use='curl', max_age=0), process_review_next, dict(context, review=review, pages=True))

    else:
        context['pages'] = 1
        context['review'] = review
        process_review_next(data: Response, context: dict[str, str], session: Session)


def process_review_next(data: Response, context: dict[str, str], session: Session):
    review = context["review"]

    if context.get('pages'):
        conclusion = data.xpath('(//div[@id="content-area"]//ul[contains(., "Závěr a hodnocení") or contains(., "Shrnutí a závěr") or contains(., "Závěr")])[1]/following-sibling::p[normalize-space(text()|font/text())]//text()').string(multiple=True)
        if conclusion:
            excerpt = data.xpath('(//div[@id="content-area"]//ul[contains(., "Závěr a hodnocení") or contains(., "Shrnutí a závěr") or contains(., "Závěr")])[1]/preceding-sibling::p[normalize-space(text()|font/text())]//text()').string(multiple=True)
            review.add_property(type='conclusion', value=conclusion)

        else:
            excerpt = data.xpath("//div[@id='content-area']//p[normalize-space(text()|font/text())]//text()").string(multiple=True)
            if not excerpt:
                excerpt = data.xpath("//table[@class='contentpaneopen']//tr//div//font//text()").string(multiple=True)
            if not excerpt:
                excerpt = data.xpath("//table[@class='contentpaneopen']//tr//p//font//text()").string(multiple=True)
            if not excerpt:
                excerpt = data.xpath("//table[@class='contentpaneopen']//tr//p//span//text()").string(multiple=True)
            if not excerpt:
                excerpt = data.xpath("//p//font//text()").string(multiple=True)
            if not excerpt:
                excerpt = data.xpath("//p//span//text()").string(multiple=True)
            if not excerpt:
                excerpt = data.xpath("//div//font//text()").string(multiple=True)

        if excerpt:
            context['excerpt'] += ' ' + excerpt

    if context['excerpt']:
        review.add_property(type="excerpt", value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)