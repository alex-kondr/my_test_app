from agent import *
from models.products import *


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.zeneszmagazin.hu/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[a[contains(., "Technika")]]//li[@title]/a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[span[contains(@class, "angle-right")]]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' – ')[0].replace(' - review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].split('-')[0]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//dd[@itemprop="author"]/span[@itemprop="name"]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath("//div[@itemprop='articleBody']/p[contains(., 'Összegzés')]/following-sibling::p[contains(@style, 'text')]//text()[not(contains(., '<br>'))]").string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@itemprop="articleBody"]/p[contains(., "Összegzés")]/preceding-sibling::p[contains(@style, "text")]//text()[not(contains(., "<br>"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@itemprop="articleBody"]/p[contains(@style, "text")]//text()[not(contains(., "<br>"))]').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\x9D', '').strip(' –')
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
