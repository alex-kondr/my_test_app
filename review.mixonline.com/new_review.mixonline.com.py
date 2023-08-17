from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.mixonline.com/technology/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    prods = data.xpath('//div[@class="col-8"]')
    for prod in prods:
        ssid = prod.xpath('preceding::article[1]/@id').string().split('-')[-1]
        title = prod.xpath('h2/text()').string()
        url = prod.xpath('a[@class="post-title"]/@href').string()
        session.queue(Request(url), process_product, dict(context, ssid=ssid, title=title, url=url))

    next_url = data.xpath('//a[@class="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_product(data, context, session):
    product = Product()
    product.name = context['title'].split('Review: ')[-1].split('Test: ')[-1].replace('Reviews', '').replace('Review', '').replace('Test ', '').replace('TEST ', '').split(' - ')[0].strip()
    product.category = data.xpath("//div[@class='col-12']/p/a[not(contains(., 'Review'))][last()]/text()").string()
    product.ssid = context['ssid']

    product.url = data.xpath('//section[@class="entry-content"]/following-sibling::p/a/@href').string()
    if not product.url:
        product.url = data.xpath('//td[strong[contains(text(), "COMPANY")]]/a/@href').string()
    if not product.url:
        product.url = context['url']

    manufacturer = data.xpath('//strong[contains(text(), "COMPANY") or contains(text(), "Company")]/following-sibling::text()[1]').string()
    if manufacturer:
        product.manufacturer = manufacturer.replace('•', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//p[@class="author-name"]/a').first()
    if not author:
        author = data.xpath('//a[@rel="author"]').first()
    if author:
        name = author.xpath('text()').string().replace('⋅', '').strip()
        url = author.xpath('@href').string()
        review.authors.append(Person(name=name, ssid=name, url=url))

    summary = data.xpath('//p[@class="excerpt"]/text()').string()
    if not summary:
        summary = data.xpath('//h1[@class="entry-title"]/following-sibling::p[not(@class)]/text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    pros = data.xpath('//strong[contains(text(), "PROS:")]/following-sibling::text()[1]').strings()
    if not pros:
        pros = data.xpath('//strong[contains(text(), "PRO:")]/following-sibling::text()').strings()
    if not pros:
        pros = data.xpath('//strong[contains(text(), "PROS:")]/parent::*/following-sibling::*/text()').strings()
    if not pros:
        pros = data.xpath('//strong[contains(text(), "PRO:")]/parent::*/following-sibling::*/text()').strings()
    if not pros:
        pros = data.xpath('//strong[contains(text(), "Pros:")]/following-sibling::text()').strings()
    if not pros:
        pros = data.xpath('//span[contains(., "PROS:")]/following-sibling::*/text()').strings()
    for pro in pros:
        pro = pro.replace('\n', '').replace('•', '').strip('.').strip()
        if not pro:
            break
        review.properties.append(ReviewProperty(type='pros', value=pro))

    cons = data.xpath('//strong[contains(text(), "CONS:")]/following-sibling::text()[1]').strings()
    if not cons:
        cons = data.xpath('//strong[contains(text(), "CON:")]/following-sibling::text()').strings()
    if not cons:
        cons = data.xpath('//strong[contains(text(), "CONS:")]/parent::*/following-sibling::*/text()').strings()
    if not cons:
        cons = data.xpath('//strong[contains(text(), "CON:")]/parent::*/following-sibling::*/text()').strings()
    if not cons:
        cons = data.xpath('//strong[contains(text(), "Cons:")]/following-sibling::text()').strings()
    if not cons:
        cons = data.xpath('//span[contains(., "CONS:")]/following-sibling::*/text()').strings()
    for con in cons:
        if 'None found' not in con:
            con = con.replace('\n', '').replace('•', '').strip('.').strip()
            review.properties.append(ReviewProperty(type='cons', value=con))

    conclusion = data.xpath('((//strong[contains(text(), "CONCLUSION") or contains(text(), "The Verdict")]/parent::*/following-sibling::p|//p[contains(text(), "And the Verdict?") or contains(text(), "Digital Conclusions")]/following-sibling::p)[not(@class) and not(@style) and not(a) and not(em) and not(strong)]//text()|//strong[contains(text(), "CONCLUSION") or contains(text(), "The Verdict")]/following-sibling::text())[not(contains(., "PRODUCT SUMMARY")) and not(contains(., "COMPANY:")) and not(contains(., "PRODUCT:")) and not(contains(., "PRICE:")) and not(contains(., "PROS:")) and not(contains(., "CONS:"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//td[strong[contains(text(), "TAKEAWAY")]]/text()').string()
    if conclusion:
        review.add_property(type='conclusion', value=conclusion.replace('“', '').replace('”', ''))

    if not data.xpath('//section[@class="entry-content"]/following-sibling::p'):
        return

    if conclusion:
        excerpt = data.xpath('//strong[contains(text(), "CONCLUSION") or contains(text(), "The Verdict")]/parent::*/preceding-sibling::p[not(@class) and not(@style) and not(a) and not(em) and not(strong)]//text()|//p[contains(text(), "And the Verdict?") or contains(text(), "Digital Conclusions")]/preceding-sibling::p[not(@class)]/text()').string(multiple=True)
    else:
        excerpt = data.xpath('(//strong[contains(., "PRODUCT SUMMARY") or contains(., "Product Summary")]/parent::*/preceding-sibling::p[not(@class) and not(@style) and not(a) and not(em) and not(strong)]//text()|//strong[contains(., "PRODUCT SUMMARY") or contains(., "Product Summary")]/parent::*/preceding-sibling::p[strong or a]/text())[not(contains(., "PRODUCT SUMMARY")) and not(contains(., "COMPANY:")) and not(contains(., "PRODUCT:")) and not(contains(., "PRICE:")) and not(contains(., "PROS:")) and not(contains(., "CONS:"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//section[@class="entry-content"]/following-sibling::p[not(@class) and not(@style) and not(span) and not(contains(text(), "•")) and not(strong) and not(em) and not(a)]//text()[not(contains(., "PRODUCT SUMMARY")) and not(contains(., "Product Summary")) and not(contains(., "COMPANY:")) and not(contains(., "PRODUCT:")) and not(contains(., "PRICE:")) and not(contains(., "Price:")) and not(contains(., "PROS:")) and not(contains(., "CONS:")) and not(contains(., "Contact:"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//section[@class="entry-content"]/following-sibling::p[not(@class) and not(@style) and not(span)]//text()[not(contains(., "PRODUCT SUMMARY")) and not(contains(., "COMPANY:")) and not(contains(., "PRODUCT:")) and not(contains(., "PRICE:")) and not(contains(., "PROS:")) and not(contains(., "CONS:"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//section[@class="entry-content"]/following-sibling::p[not(@class) and not(span/strong) and not(b) and not(a)]//text()[not(contains(., "PRODUCT SUMMARY")) and not(contains(., "COMPANY:")) and not(contains(., "PRODUCT:")) and not(contains(., "PRICE:")) and not(contains(., "Price:")) and not(contains(., "PROS:")) and not(contains(., "CONS:")) and not(contains(., "Contact:"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//section[@class="entry-content"]/following-sibling::p[not(@class)]//text()[not(contains(., "PRODUCT SUMMARY")) and not(contains(., "COMPANY:")) and not(contains(., "PRODUCT:")) and not(contains(., "PRICE:")) and not(contains(., "PROS:")) and not(contains(., "CONS:"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//section[@class="entry-content"]/following-sibling::p[contains(@class, "Body")]//text()[not(contains(., "PRODUCT SUMMARY")) and not(contains(., "COMPANY:")) and not(contains(., "PRODUCT:")) and not(contains(., "PRICE:")) and not(contains(., "PROS:")) and not(contains(., "CONS:"))]').string(multiple=True)

    if excerpt and summary:
        excerpt = excerpt.replace(summary, '')

    if excerpt:
        excerpt = excerpt.replace('', '').replace('PRODUCT SUMMARY', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
