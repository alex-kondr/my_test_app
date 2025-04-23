from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://thelitereview.com/reviews", use='curl', force_charset='utf-8'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath("//h2[@class='entry-title']/a")
    for prod in prods:
        title = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(title=title, url=url))

    next_url = data.xpath("//div[@class='nav-previous']//a/@href").string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict())


def process_product(data, context, session):
    product = Product()
    product.name = context['title'].split(' Preview')[0].split("Review")[0]
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = data.xpath("//a[@rel='category tag']//text()").string()

    product.url = data.xpath('//a[contains(., "Click Here")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath("//time[@class='entry-date published']/@datetime").string()
    if date:
        review.date = date.split("T")[0]

    author_name = data.xpath("//span[@class='author vcard']//text()").string(multiple=True)
    if author_name:
        review.authors.append(Person(name=author_name, ssid=author_name))

    summary = data.xpath('//h3[contains(., "Preface")]/following-sibling::p[count(preceding-sibling::h3)=1]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Summary")]/following-sibling::p[not(preceding-sibling::h3[contains(., "Where to Buy")])]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Summary")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body/p[not(preceding::h3[contains(., "Where to Buy")])]//text()').string(multiple=True)

    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary,'')

        if conclusion:
            excerpt = excerpt.replace(conclusion,'')

        excerpt = excerpt.strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
