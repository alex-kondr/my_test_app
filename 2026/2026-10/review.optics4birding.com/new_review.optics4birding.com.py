from agent import *
from models.products import *
import time
import random


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:157.0) Gecko/20100101 Firefox/157.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Alt-Used: optics4birding.com' -H 'Connection: keep-alive' -H 'Cookie: localization=US; cart_currency=USD; _shopify_essential=:AaEV-N8KAAEA-otWj1pJJNDJd6xl6n97ew-hhztnyBiiAqpE_0TOLnPIk-9jia9WWIHXBVloieKRXMDZ-R0nwZAGyBU:; _shopify_analytics=:AaEV-N83AAEAT0UqreVbo-OuF96PbKGiVSjJ5jj1RKgRDoAqS22wysBDViwb0FBxXuMa6i6sOUk-TQxLGGz_Gj3ykuw:; _shopify_marketing=:AaEV-N83AAEAZmHSsjfGCDNEx3GEYHdZ2tw7EswsNYH_YJxx6RPbdg1w_NCqFkIy_GxwKA8mFv8uuRZmrbA1fYs0ypQ:' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers'"""


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
    session.queue(Request('https://optics4birding.com/pages/expert-reviews', force_charset='utf-8', use='curl', options=OPTIONS, max_age=0), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(3, 10))

    cats = data.xpath('//div[@class="expert-review"]')
    for cat in cats:
        cat_name = cat.xpath('.//h2/text()').string()

        revs = cat.xpath('.//a')
        for rev in revs:
            title = rev.xpath('.//h3/text()').string()
            url = rev.xpath('@href').string()
            session.queue(Request(url, force_charset='utf-8', use='curl', options=OPTIONS, max_age=0), process_review, dict(cat=cat_name, title=title, url=url))

# no next page


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(3, 10))

    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-review', '')
    product.category = context['cat'].replace('Featured Reviews', 'Optics').replace('Reviews', '').strip()

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