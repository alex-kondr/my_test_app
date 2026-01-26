from agent import *
from models.products import *
import simplejson


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: client_key=eb0d; aws-waf-token=33fe9b72-74e9-46c6-a49e-858ffff22840:CAoApbtVgdYIAAAA:TFy9DqjVclYTB4fXHJUtSSQ0/iYXoFn6oO3dw0iq1T2xU54nEXM4l+L5nougxjtgaRFiefvG4Bj/wz8nmK31EZk9Y2y5h0oaUDMVTmbsBaNuZPqzjyXeAqyj4tSSRZ4CCUsmFWPLzGj5FfL3YoEZscKbyVsi41uUpUv2d1/JQM9+/hUWnLmSYlk5+fxZLZQTpiQvDosRFjNDwzen; session_token.1755778179145597822=176ea96d25c5dcb613145601f8907f0a5867757e3ffa8c3e22261394e80b2c6e; country=ca; tkbl_session=e521f736-d9ea-410a-972a-12c05ed15051' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: cross-site' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers'"""


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.primecables.ca/", use='curl', options=OPTIONS), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@class="nav2020"]')
    for cat in cats:
        name = cat.xpath('a//text()').string()

        sub_cats = cat.xpath('div/div/dl')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('dt/a//text()').string()

            sub_cats1 = sub_cat.xpath('dd/ul/li')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('div[@class="category-name"]//text()').string()
                url = sub_cat1.xpath('a/@href').string()
                session.queue(Request(url, use='curl', options=OPTIONS), process_prodlist, dict(cat=name + "|" + sub_name + "|" + sub_name1))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-name-wrap"]/div')
    for prod in prods:
        name = prod.xpath('p[@v-else="v-else"]//text()').string()
        url = prod.xpath('a/@__href').string()

        if url:
            url = url.split("source_url('")[-1].rstrip("')\"")
            session.queue(Request(url, use='curl', options=OPTIONS), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//li[@class="next"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', options=OPTIONS), process_prodlist, dict(context))


def process_product(data, context, session):
    prod_json = data.xpath('//div/@data-origin-params').string()
    if not prod_json:
        return

    prod_content = simplejson.loads(prod_json)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = prod_content.get('id')
    product.sku = prod_content.get('sku')
    product.manufacturer = data.xpath('//span[@itemprop="brand"]//text()').string()

    mpn = data.xpath('//span[@itemprop="model"]//text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    revs_count = data.xpath('//meta[@itemprop="reviewCount"]/@content').string()
    if revs_count and int(revs_count) > 0:
        revs_url = product.url.replace('p-', 'reviews-')
        session.do(Request(revs_url, use='curl', options=OPTIONS), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//li[contains(@id, "review")]/parent::ul')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.date = rev.xpath('following::div[@class="review-date"][1]//text()').string()

        ssid = rev.xpath('li/@id').string()
        if ssid:
            review.ssid = ssid.split('review-')[-1]

        author = rev.xpath('following::div[@class="review-customer-name notranslate"][1]/p//span[@itemprop="author"]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('following-sibling::div[@class="review-num"][1]/span/text()').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.xpath('following::div[@class="review-thank notranslate"][1]/span//text()').string()
        if hlp_yes:
            hlp_yes = int(hlp_yes.split(' people')[0].split(' person')[0].lstrip('('))
            if hlp_yes > 0:
                review.add_property(type='helpful_votes', value=hlp_yes)

        is_verified = rev.xpath('following::div[@class="review-customer-sort notranslate"][1]/img/@src').string()
        if is_verified and 'verified-buyer' in is_verified:
            review.add_property(type='is_verified_buyer', value=True)
        else:
            continue

        excerpt = rev.xpath('following::div[@class="review-content-text"][1]/p//text()').string()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url and data.response_url != next_url:
        session.do(Request(next_url, use='curl', options=OPTIONS), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)

