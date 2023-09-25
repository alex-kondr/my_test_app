from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://gameguru.ru/articles/rubrics_review/'), process_revlist, {})


def process_revlist(data, context, session):
    revs = data.xpath("//div[@class='short-news']")
    for rev in revs:
        url = rev.xpath(".//a[@class='area-clickable']/@href").string()
        session.queue(Request(url), process_review, dict(url=url))

    nexturl = data.xpath("//a[contains(.,'Смотреть еще')]/@href").string()
    if nexturl:
        session.queue(Request(nexturl), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.ssid = context['url'].split('/')[-2]
    product.url = context['url']

    title = data.xpath("//li[@itemprop='itemListElement']/span[@itemprop='name']/text()").string(multiple=True)
    prod_name = ''
    if 'Обзор ' in title:
        prod_name = title.split('Обзор ', 1)[-1].split('.')[0]
    elif 'Превью ' in title:
        prod_name = title.split('Превью ', 1)[-1].split('.')[0]
    if prod_name:
        product.name = prod_name
    else:
        product.name = title.split(": Мини-обзор")[0]

    tags = data.xpath("//span[@itemprop='about']//text()")
    category = ''
    if tags:
        for tag in tags:
            if 'обзор' not in tag.string().lower():
                category = tag.string()
                break
    if category:
        product.category = 'Games|' + category
    else:
        product.category = 'Games'

    review = Review()
    review.title = title
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']
    review.date = data.xpath("//div[@class='news-date']/text()").string(multiple=True)

    author = data.xpath("//div[@class='name']/a").first()
    if author:
        a_name = author.xpath('.//text()').string(multiple=True)
        a_url = author.xpath('@href').string()
        a_ssid = author.xpath('@href').string().split('/')[-2]
        review.authors.append(Person(name=a_name, profile_url=a_url, ssid=a_ssid))

    summary = data.xpath("//p[1]//strong//text()").string(multiple=True)
    conclusion = data.xpath("//blockquote[@class='blockquote']//text()").string(multiple=True)
    excerpt = data.xpath("//p//text()").string(multiple=True)
    if summary:
        excerpt = excerpt.replace(summary, '')
        review.properties.append(ReviewProperty(type='summary', value=summary))
    if conclusion:
        excerpt = excerpt.replace(conclusion, '')
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
    else:
        excerpt = data.xpath("//body/text()").string(multiple=True)
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    if excerpt or summary or conclusion:
        product.reviews.append(review)
        session.emit(product)
