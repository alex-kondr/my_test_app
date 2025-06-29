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
    session.queue(Request('https://optics4birding.com/pages/expert-reviews', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="expert-review"]')
    for cat in cats:
        cat_name = cat.xpath('.//h2/text()').string()

        revs = cat.xpath('.//a')
        for rev in revs:
            title = rev.xpath('.//h3/text()').string()
            url = rev.xpath('@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(cat=cat_name, title=title, url=url))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title']
    product.ssid = context['url'].split('/')[-1].replace('-review', '')
    product.category = context['cat'].replace('Featured Reviews', 'Optics').replace('Reviews', '').strip()

    product.url = data.xpath('//a[contains(@class, "expert-review")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    conclusion = data.xpath('//div[@id="conclusions"]/p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="Review Topics"]/div[@class and not(@id="conclusions")]//p[not(preceding-sibling::h2[contains(., "Conclusion")])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
