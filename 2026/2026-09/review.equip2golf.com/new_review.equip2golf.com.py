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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.equip2golf.com/category/reviews/'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//div[@class="post_header_title"]/h5/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//div[@class="pagination"]/p/a[@class="prev_button"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.category = 'Golf Equipment'

    product.ssid = data.xpath('//div[regexp:test(@id,"post-\d+") and .//p]/@id').string()
    if not product.ssid:
        product.ssid = product.url.split('/')[-2]

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath("//span[@class='post_info_date']//text()").string(multiple=True)

    excerpt = data.xpath('(//div[@class="post_header single"]/p[not(contains(., "Follow us on"))]|//div[@class="post_header single"]/table//td[@style="text-align: left;" and not(contains(., "Price:") or contains(., "Follow us on"))])//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'�', '').replace('â€¢', '•').replace('â€', '"').replace(u'Â', '').replace('â€™', "'").replace('Ã©', u'é').replace(u'Ã', u'à').replace('â€¦', '…').replace(u'\x9D', '').strip()
        if len(excerpt) > 10:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
