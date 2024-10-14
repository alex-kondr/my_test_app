from agent import *
from models.products import *


def process_frontpage(data, context, session):
    for cat in data.xpath("//li[@id='menu-item-6129']/ul/li/a"):
        url = cat.xpath("@href").string()
        category = cat.xpath("descendant::text()").string(multiple=True)
        if url and category:
            category = re_search_once("^(.*) Reviews$", category)
            if category:
                session.queue(Request(url), process_revlist, dict(category=category))


def process_revlist(data, context, session):
    for rev in data.xpath("//div[@class='entry-body']"):
        url = rev.xpath(".//h3[@class='g1-alpha g1-alpha-1st entry-title' or @class='g1-gamma g1-gamma-1st entry-title']//a//@href").string()
        title = rev.xpath(".//h3[@class='g1-alpha g1-alpha-1st entry-title' or @class='g1-gamma g1-gamma-1st entry-title']//a/text()").string()
        if url and title:
            name = re_search_once('^(.*) [Rr]eview', title) or title
            ssid = rev.xpath("preceding-sibling::article/@class").string().split('post-')[1].split()[0]

            if name:
                session.queue(Request(url), process_review, dict(context, url=url, title=title, name=name, ssid=ssid))

    nexturl = data.xpath("//a/@data-g1-next-page-url").string()
    if nexturl:
        session.queue(Request(nexturl), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = context['category']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath("//time[@itemprop='datePublished']/@datetime").string().split('T')[0]

    author = data.xpath("//span[@itemprop='author']//strong/text()").string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath("//b[contains(text(), 'Value')]//ancestor::p//following-sibling::p//text()").string(multiple=True)
    if not(summary):
        summary = data.xpath("//p[contains(text(), 'Overall…')]//text()").string(multiple=True)
    if not(summary):
        summary = data.xpath("//em[contains(text(), 'Overall')]//ancestor::p//text()").string(multiple=True)
    if not(summary):
        summary = data.xpath("//h4[contains(text(), 'Value')]//following-sibling::p[1]//text()").string(multiple=True)
    if not(summary):
        summary = data.xpath("//strong[contains(text(), 'Overall')]//ancestor::p//text()").string(multiple=True)
    if not(summary):
        summary = data.xpath("//strong[contains(text(), 'Value')]//ancestor::p//following-sibling::p//text()").string(multiple=True)
    if summary:
        if not("Overall Rating" in summary) and not("Overall Combined Rating" in summary):
            review.add_property(type='summary', value=summary)

    excerpt = data.xpath("//div[@itemprop='articleBody']//p//text()[not(parent::strong or parent::b or parent::em)]").string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')
        review.add_property(type='excerpt', value=excerpt)

    score = data.xpath("//strong[regexp:test(text(), 'Overall Combined Rating|Overall Rating')]//text()").string(multiple=True)
    if score:
        name = score.split(' – ')[0]
        score = score.split(' – ')[-1].split('%')[0]
        if "o" in score:
            score = score.replace('o', '0')
        review.grades.append(Grade(name=name, type='overall', value=float(score), best=100.0))

    if excerpt or summary:
        product.reviews.append(review)
        session.emit(product)


def run(context, session):
    session.browser.agent = "Mozilla/6.0"
    session.queue(Request('http://www.sirshanksalot.com/'), process_frontpage, {})
