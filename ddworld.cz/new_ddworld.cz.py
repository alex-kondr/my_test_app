from agent import *
from models.products import *


XCAT = ["Aktuality", "Software"]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request("http://www.ddworld.cz/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath("//ul[@class='menutop']/li[@class='parent']")
    for cat in cats:
        name = cat.xpath("span/a/text()").string()
        url = cat.xpath("span/a/@href").string()

        if name not in XCAT:
            cats2 = cat.xpath("ul/li")

            if cats2:
                for cat2 in cats2:
                    cat2_name = cat2.xpath("span/a/text()").string()
                    url = cat2.xpath("span/a/@href").string()
                    cats3 = cat2.xpath("ul/li")

                    if cats3:
                        for cat3 in cats3:
                            cat3_name = cat3.xpath("span/a/text()").string()
                            url = cat3.xpath("span/a/@href").string()
                            session.queue(Request(url), process_revlist, dict(cat=name+'|'+cat2_name+'|'+cat3_name))
                    else:
                        session.queue(Request(url), process_revlist, dict(cat=name+'|'+cat2_name))
            else:
                session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath("//a[contains(@name, 'article_')]")
    for rev in revs:
        ssid = rev.xpath("@name").string().split('_')[-1]
        title = rev.xpath("following-sibling::table[1]//td[@class='contentheading']/a/text()").string()
        url = rev.xpath("following-sibling::table[1]//td[@class='contentheading']/a/@href").string()
        if url:
            session.queue(Request(url), process_review, dict(context, url=url, title=title, ssid=ssid))

    next_url = data.xpath("//a[@title='Následující']/@href").string()
    if next_url:
        session.queue(Request(next_url.replace('+', '')), process_revlist, context)


def process_review(data, context, session):
    product = Product()
    product.name = context["title"].split("– TEST a RECENZE")[0].split("Recenze:")[-1].split("TEST: ")[-1]
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
    if author:
        review.authors.append(Person(name=author, ssid=author, url=author_url))

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

    next_url = data.xpath('//a[contains(text(), "Následující")]/@href').string()
    if next_url:
        review.add_property(type='pages', value=dict(title=review.title + ' - page 1', url=data.response_url))
        session.do(Request(next_url, use="curl"), process_review_next, dict(context, review=review, page=2))
    else:
        context['review'] = review
        context['page'] = 1
        process_review_next(data, context, session)


def process_review_next(data, context, session):
    review = context["review"]

    page = context['page']
    if page > 1:
        review.add_property(type='pages', value=dict(title=review.title + ' - page ' + str(page), url=data.response_url))

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

    next_url = data.xpath('//a[contains(text(), "Následující")]/@href').string()
    if next_url:
        session.do(Request(next_url, use="curl"), process_review_next, dict(context, review=review, page=page+1))
    elif context['excerpt']:
        review.properties.append(ReviewProperty(type="excerpt", value=context['excerpt']))

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
