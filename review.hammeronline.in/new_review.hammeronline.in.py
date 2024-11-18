from agent import *
from models.products import *
import simplejson
import re


def remove_emoji(string):
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


def run(context, session):
    session.queue(Request('https://hammeronline.in/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//a[@class="text-btns"]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@data-product-id]')
    for prod in prods:
        name = prod.xpath('.//div[contains(@class, "product__title ")]/text()').string()
        ean = prod.xpath('@data-product-id').string()
        url = prod.xpath('.//a[@class="grid-product__link"]/@href').string()

        revs_cnt = prod.xpath('.//span[contains(@class, "badge__text")]/text()').string()
        if revs_cnt and revs_cnt.split()[0].isdigit() and int(revs_cnt.split()[0]) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, ean=ean, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']
    product.manufacturer = 'Hammer'
    product.sku = data.xpath('//option[@selected="selected"]/@value').string()
    product.add_property(type='id.ean', value=context['ean'])

    revs_url = 'https://judge.me/reviews/reviews_for_widget?url=hammer-audio.myshopify.com&shop_domain=hammer-audio.myshopify.com&platform=shopify&page=1&per_page=5&product_id={ean}'.format(ean=context['ean'])
    session.do(Request(revs_url), process_reviews, dict(context, product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_data = simplejson.loads(data.content)

    revs = data.parse_fragment(revs_data.get('html')).xpath('//div[contains(@class, "reviews")]/div')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//span/@data-content').string()
        if date:
            review.date = date.split()[0]

        author = rev.xpath('.//span[contains(@class, "author")]//text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span/@data-score').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('@data-verified-buyer').string()
        if is_verified and is_verified == 'true':
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.xpath('.//b[contains(@class, "title")]//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[contains(@class, "body")]//text()').string(multiple=True)
        if title and excerpt:
            review.title = remove_emoji(title)
        elif not excerpt:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt)
            review.add_property(type='excerpt', value= excerpt)

            review.ssid = rev.xpath('@data-review-id').string()
            if not review.ssid:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    revs_cnt = revs_data.get('total_count')
    offset = context.get('offset', 0) + 5
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        next_url = 'https://judge.me/reviews/reviews_for_widget?url=hammer-audio.myshopify.com&shop_domain=hammer-audio.myshopify.com&platform=shopify&page={page}&per_page=5&product_id={ean}'.format(ean=context['ean'], page=next_page)
        session.do(Request(next_url), process_reviews, dict(context, product=product, offset=offset, page=next_page))
    else:
        session.emit(product)
