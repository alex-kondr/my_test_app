from agent import *
from models.products import *
import re


XCAT = ["Aktuality"]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request("http://www.ddworld.cz/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//ul[@class='menutop']/li[@class='parent']")
    for cat in cats:
        name = cat.xpath("span/a/text()").string()
        url = cat.xpath("span/a/@href").string()
        
        if name not in XCAT:
            cats2 = cat.xpath("ul/li")
            
            if not cats2:
                session.queue(Request(url), process_revlist, dict(cat=name))
                
            for cat2 in cats2:
                cat2_name = cat2.xpath("span/a/text()").string()
                url = cat2.xpath("span/a/@href").string()
                cats3 = cat2.xpath("ul/li")
                
                if not cats3:
                    session.queue(Request(url), process_revlist, dict(cat=name+'|'+cat2_name))
                    
                for cat3 in cats3:
                    cat3_name = cat3.xpath("span/a/text()").string()
                    url = cat3.xpath("span/a/@href").string()
                    session.queue(Request(url), process_revlist, dict(cat=name+'|'+cat2_name+'|'+cat3_name))


def process_revlist(data, context, session):
    revs = data.xpath("//a[contains(@name, 'article_')]")
    for rev in revs:
        ssid = rev.xpath("@name").string().split('_')[-1]
        name = rev.xpath("following-sibling::table[1]//td[@class='contentheading']/a/text()").string()
        url = rev.xpath("following-sibling::table[1]//td[@class='contentheading']/a/@href").string()
        if url:
            session.queue(Request(url), process_review, dict(context, url=url, name=name, ssid=ssid))

    next_url = data.xpath("//a[@title='Následující']/@href").string()
    if next_url:
        session.queue(Request(next_url.replace('+', '')), process_revlist, context)


def process_review(data, context, session):
    product = Product()
    product.name = context["name"].split("– TEST a RECENZE")[0].split("Recenze:")[-1].split("TEST: ")[-1]
    product.url = context["url"]
    product.ssid = context["ssid"]
    product.category = context["cat"]

    review = Review()
    review.type = "pro"
    review.title = context["name"]
    review.url = product.url
    review.date = data.xpath("//td[@class='createdate']//text()").string(multiple=True).split(',')[-1].strip()
    review.ssid = product.ssid

    author = data.xpath("//span[@class='small']//a")
    if author:
        name = author[0].xpath("text()").string()
        url = author[0].xpath("@href").string(multiple=True)
        if name and url:
            ssid = re.search("user=\d+", url).group().split("user=")[-1]
            review.authors.append(Person(name=name, ssid=ssid, profile_url=url))

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
        review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

    next_url = ''
    pages = data.xpath("//table[@class='contenttoc']//a")
    for i, page in enumerate(pages):
        url = page.xpath("@href").string()
        title = page.xpath("descendant::text()").string(multiple=True)
        if title:
            title += " - Page " + str(i + 1)
        if url and title:
            review.properties.append(ReviewProperty(type="pages", value={"url": url, "title": title}))
            next_url = url

    if next_url:
        session.do(Request(next_url, use="curl"), process_review_next, dict(review=review, product=product))

    product.reviews.append(review)

    if product.reviews:
        session.emit(product)


def process_review_next(data, context, session):
    review = context["review"]
    conclusion = data.xpath("//div[@id='content-area']//font/text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[@id='content-area']//p[normalize-space(text()|font/text())]//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//table[@class='contentpaneopen']//tr//div//font/text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//table[@class='contentpaneopen']//tr//p//font/text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//table[@class='contentpaneopen']//tr//p//span/text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//p//font//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//p//span//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div//font//text()").string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type="conclusion", value=conclusion))
