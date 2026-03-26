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
    session.queue(Request('https://www.printershowcase.com/color-laser-printer-reviews.aspx'), process_catlist, dict(cat='Color Laser Printer|'))


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[contains(@id, "pageContent")]/a')
    for cat in cats:
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(context))


def process_revlist(data, context, session):
    strip_namespace(data)

    subcat_name = data.xpath('(//span[contains(@id, "breadcrumbContent")]/span)[last()]/text()').string()

    revs = data.xpath('//a[contains(@title, "See Review")]')
    for rev in revs:
        url = rev.xpath('@href').string().replace('/../../../', '/')
        session.queue(Request(url), process_review, dict(cat=context['cat']+subcat_name, url=url))


def process_review(data, context, session):
    strip_namespace(data)

    title = data.xpath('(//span[contains(@id, "breadcrumbContent")]/span)[last()]/text()').string()

    product = Product()
    product.name = title.split(' - ')[-1].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.aspx', '').replace('Review-', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    summary = data.xpath('//div[contains(@id, "htmlContent")]//td[contains(., "In Short:")]//text()[not(contains(., "In Short:"))]').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@id, "htmlContent")]//td[contains(., "The Bottom Line:")]//text()[not(contains(., "The Bottom Line:"))]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@id, "htmlContent")]//td[not(contains(., "The Bottom Line:") or contains(., "In Short:"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
