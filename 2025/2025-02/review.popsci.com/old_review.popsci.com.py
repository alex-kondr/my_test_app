from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request("https://www.popsci.com/category/gear/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//a[@aria-current="page"]/following-sibling::div//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="LatestArticles-content"]//a[@class="PostItem-link"]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(context, url=url))
    
    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    try:
        prods = data.xpath("//tr[@class='ProductTable-product']")
        if prods:
            process_reviews(data, context, session)
            return

        title = data.xpath('//h1//text()').string()

        product = Product()
        product.name = title
        product.url = context["url"]
        product.ssid = context["url"].split('/')[-2]
        product.category = context["cat"]

        review = Review()
        review.type = 'pro'
        review.title = title
        review.url = product.url
        review.ssid = product.ssid

        date = data.xpath("//span[@class='Article-dateTime']/text()").string()
        if date:
            review.date = date.split(' ', 1)[-1].rsplit(' ', 2)[0].replace('Published', '')

        author = data.xpath("//a[@rel='author']").first()
        if author:
            name = author.xpath("text()").string()
            url = author.xpath("@href").string()
            review.authors.append(Person(name=name, ssid=name, profile_url=url))

        summary = data.xpath("//p[@class='Article-excerpt']/text()").string()
        if summary:
            review.add_property(type='summary', value=summary)

        excerpt = data.xpath("//div[@class='Article-bodyText']/p//text()").string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)
            session.emit(product)
    except:
        return


def process_reviews(data, context, session):
    prods = data.xpath("//h3[@id][descendant::a]")
    for prod in prods:
        product = Product()
        product.name = prod.xpath(".//a//text()").string(multiple=True)
        product.ssid = product.name.strip().lower().replace(' ', '-')
        product.url = context["url"]
        product.category = context["cat"]

        review = Review()
        review.type = 'pro'
        review.title = data.xpath('//h1//text()').string()
        review.url = context["url"]
        review.ssid = product.ssid

        date = data.xpath("//span[@class='ArticleReviewAuthor-publishedTime']/text()").string()
        if date:
            review.date = date.replace('Published', '')

        excerpt = ""
        rev_info = prod.xpath("following-sibling::*")
        for item in rev_info:
            if item.xpath("self::p[strong[contains(., 'Why it made the cut')]]"):
                summary = item.xpath("text()").string(multiple=True)
                if summary:
                    if summary.startswith(':'):
                        summary = summary.split(':', 1)[-1].strip()
                    review.add_property(type='summary', value=summary)
            elif item.xpath("self::p[strong[text()='Pros']]"):
                pros = item.xpath("following-sibling::ul[1]/li/text()").strings()
                for pro in pros:
                    review.add_property(type='pros', value=pro)
            elif item.xpath("self::p[strong[text()='Cons']]"):
                cons = item.xpath("following-sibling::ul[1]/li/text()").strings()
                for con in cons:
                    review.add_property(type='cons', value=con)
            elif item.xpath("self::p[not(strong)]"):
                text = item.xpath("text()").string()
                if text:
                    excerpt += text
            elif item.xpath("self::*[regexp:test(local-name(), '^h\d')]"):
                break

        author = data.xpath("//a[@rel='author']").first()
        if author:
            name = author.xpath("text()").string()
            url = author.xpath("@href").string()
            review.authors.append(Person(name=name, ssid=name, profile_url=url))

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)
            session.emit(product)
