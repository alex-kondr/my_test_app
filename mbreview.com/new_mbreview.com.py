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
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.mbreview.com/', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    brands = data.xpath('//li[a[contains(text(), "Review ")]]/ul/li/a')
    for brand in brands:
        name = brand.xpath('text()').string()
        url = brand.xpath('@href').string()
        session.queue(Request(url, max_age=0), process_category, dict(brand=name))


def process_category(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="entry-content"]/ul/li/a/@href')
    for cat in cats:
        url = cat.string()
        session.queue(Request(url, max_age=0), process_revlist, dict(context))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' – ')[0].replace(': Physical Review', '').replace('New Review: ', '').replace('MBR Review: ', '').replace(': PCB Review', '').replace(' Test', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-3]
    product.category = 'Tech'
    product.manufacturer = context['brand']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[@class="entry-content"]//p[not(contains(., "Read more"))]//text()').string(multiple=True)
    # //div[@class="entry-content"]//p//text()[not(contains(., "Read more") or preceding::text()[contains(., "Reas more")])]
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
        
        
        
    else:
        print '!!!!!!!!!!!'
        print data.content
