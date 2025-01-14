from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.computable.nl/overzicht/community/4573221/reviews.html'), process_frontpage, {})


def process_frontpage(data, context, session):
    for p in data.xpath("//div[@class='articlelist']/a"):
        context['name'] = p.xpath(".//h2/text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next_page = data.xpath("//ul[@class='pagination']/li[@class='arrow']/a[@rel='next']/@href").string()
    if next_page:
        session.queue(Request(next_page), process_frontpage, {})


def process_product(data, context, session):
    product = Product()
    product.name = context['name'].split(': ')[0]
    product.url = context['url']
    product.category = data.xpath("//ul[@class='breadcrumbs']/li[a][last()]//text()[string-length(normalize-space(.))>0]").string()
    product.ssid = product.url.split('/')[-3]

    review = Review()
    review.title = context['name']
    review.ssid = product.ssid
    review.url = product.url
    review.type = 'pro'

    review.date = data.xpath("//div[@class='date-line']/text()").string()
    if review.date:
        review.date = (review.date.split('|')[0].strip())[:-6]

    user_data = data.xpath("//div[@class='date-line']/a").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = user.profile_url.split('/')[-2]
        review.authors.append(user)

    conclusion = data.xpath("//h2[@class='article-subtitle']/text()").string(multiple=True) or data.xpath("//div[@class='sc-body']/*[contains(.,'Conclusie')]/following-sibling::*/text()").string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    summary = data.xpath("//div[@class='sc-intro']//text()").string(multiple=True)
    if summary:
        summary = summary.strip()
        review.properties.append(ReviewProperty(type='summary', value=summary))

    excerpt = data.xpath("//div[@class='sc-body']//text()").string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').replace('Conclusie', '')
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    product.reviews.append(review)
    session.emit(product)
