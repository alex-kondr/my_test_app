from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://stereonet.com/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h4/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    if revs:
        offset = context.get('offset', 0) + 17
        options = "--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0' -H 'Accept: */*' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'X-Requested-With: XMLHttpRequest' -H 'Alt-Used: stereonet.com' -H 'Connection: keep-alive' -H 'Referer: https://stereonet.com/reviews' -H 'Cookie: owa_v=cdh%3D%3E6fcecfda%7C%7C%7Cvid%3D%3E1721111560118767774%7C%7C%7Cfsts%3D%3E1721111560%7C%7C%7Cdsfs%3D%3E2%7C%7C%7Cnps%3D%3E6; owa_s=cdh%3D%3E6fcecfda%7C%7C%7Clast_req%3D%3E1721271990%7C%7C%7Csid%3D%3E1721271990517302212%7C%7C%7Cdsps%3D%3E1%7C%7C%7Creferer%3D%3E; merged_new_tracker=%7B%220%22%3A%22media%2Fcss%2Fbootstrap.min.css.map%22%2C%221%22%3A%22reviews%22%2C%222%22%3A%22page_templates%2Farticle_list_ajax%2Freviews%2F17%22%2C%22token%22%3A%225112cdd3c0d6a0a5c9917aed915c52c4836370ac4b9b2ee0ddd7e1541e4e668078ace2945007eb9fb9015ae91a092f8f%22%7D; geotargetlygeoconsent1740635347323cookie=geotargetlygeoconsent1740635347323cookie' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'Priority: u=0' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"
        next_url = 'https://www.stereonet.com/uk/page_templates/article_list_ajax/reviews/' + str(offset)
        session.queue(Request(next_url, use='curl', options=options, max_age=0), process_revlist, dict(offset=offset))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review of ', '').replace('Review: ', '').replace('REVIEW: ', '').replace(' Review', '').replace(' REVIEW', '').replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-review', '')
    product.category = 'Tech'
    product.manufacturer = data.xpath('//div[contains(@class, "brand")]/h2/a/text()').string()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[@class="postedDate"]/span/text()').string()
    if date:
        review.date = date.replace('Posted on', '').strip()

    author =data.xpath('//div[@class="textholder"]/h5/a/text()').string()
    author_url = data.xpath('//div[@class="textholder"]/h5/a/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[contains(@class, "summary")]/p[not(contains(., "Posted in") or contains(., "£"))]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2[contains(., "VERDICT") or contains(., "Verdict") or contains(., "verdict")]|//h3[contains(., "VERDICT") or contains(., "Verdict") or contains(., "verdict")])/following-sibling::p[not(contains(., "For more information") or contains(., "£"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2[contains(., "VERDICT") or contains(., "Verdict") or contains(., "verdict")]|//h3[contains(., "VERDICT") or contains(., "Verdict") or contains(., "verdict")])/preceding-sibling::p[not(contains(., "For more information") or contains(., "£"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="thumbnails"]/p[not(contains(., "For more information") or contains(., "£"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
