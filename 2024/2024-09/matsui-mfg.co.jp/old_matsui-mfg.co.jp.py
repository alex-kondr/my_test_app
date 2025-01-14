from agent import *
from models.products import *

X_CATS = ['金型関連製品']
URLS = ["https://matsui.net/lineup/dpd3-1/", "https://matsui.net/lineup/pmd/", "https://matsui.net/lineup/hd2/"]
X_URLS = ["https://matsui.net/lineup/fpd/", "https://matsui.net/lineup/dp/", "https://matsui.net/lineup/fd/", "https://matsui.net/lineup/sfd-ht/"]


def run(context, session):
    session.queue(Request("https://matsui.net/product/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//h3/span[@property="itemListElement"]//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        if name not in X_CATS:
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//li[@class="itemBox"]//a')
    for prod in prods:
        title = prod.xpath('@title').string()
        url = prod.xpath('@href').string()
        if url not in X_URLS:
            session.queue(Request(url), process_review, dict(context, title=title, url=url))


def process_review(data, context, session):
    product = Product()

    product.name = data.xpath('//a[@class="post post-lineup current-item"]/span//text()').string()
    product.url = context['url']
    product.category = context['cat']
    product.ssid = product.url.split('/')[-2]
    product.manufacturer = "Matsui"

    review = Review()

    review.type = "pro"
    review.ssid = product.ssid
    review.url = product.url

    title_content = data.xpath('//p[@class="productCopy"]//text()').string()
    if title_content:
        review.title = context['title'] + ' ' + title_content
    else:
        review.title = context['title']

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    summary = data.xpath('//p[@class="productDescription"]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//meta[@name="description"]/@content').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    pros = data.xpath('//h1[contains(@id, "の特長")]/following-sibling::p//strong/parent::*')
    if review.url == "https://matsui.net/lineup/hd-ad/":
        pros = data.xpath('//h1[contains(.//text(), "の特長")]/following-sibling::ol/li')
    if pros:
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True).split('. ')[-1]
            review.add_property(type="pros", value=pro)

    if not pros:
        pros = data.xpath('//h1[contains(.//text(), "の特長")]/following-sibling::h2[not(contains(@class, "SectionTit"))]')
        if pros and review.url != "https://matsui.net/lineup/ecobrid/":
            for pro in pros:
                pro = pro.xpath('.//text() | following-sibling::p[1]//text()').string(multiple=True).split('. ')[-1]
                review.add_property(type="pros", value=pro)

    if review.url in URLS:
        pros = data.xpath('//strong')
        for pro in pros:
            pro = pro.xpath('.//text() | following-sibling::text()[1]').string(multiple=True).split('. ')[-1]
            review.add_property(type="pros", value=pro)

    excerpt = data.xpath('//ol/li[not(.//strong)]//text()').string(multiple=True)
    if review.url == "https://matsui.net/lineup/dmz2/":
        excerpt = data.xpath('//p/span[contains(.//text(), "●")]//text() | //ol/li//text()').string(multiple=True)

    if review.url == "https://matsui.net/lineup/ecobrid/":
        excerpt = data.xpath('//p[not(@class)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
