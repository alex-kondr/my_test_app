from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers=[SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.bit-tech.net/reviews/?page=1', use='curl', force_charset='utf-8'), process_revlist, {})


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath("//div[@class='articleinfo']/a")
    for rev in revs:
        title = rev.xpath(".//text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[contains(button/text(), "Next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    title = context['title'] or data.xpath("//h1[@class='heading']//text()").string()
    if not title:
        return # Empty article, sometimes happens

    product = Product()
    product.name = title.replace('Review', '').replace(' re-review', '').replace(' review', '').replace(' group test', '').replace(' Group Test', '').replace(' on test', '').replace(' Test', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-3].replace('-review', '')
    product.category = 'Tech'
    product.manufacturer = data.xpath("//div[@id='page_body']/p[contains(.,'Manufacturer')]/text()[not(self::strong)]").string()

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath("//p[@class='datetime']//text()").string()
    if date:
        review.date = date.split(' | ')[0].strip()

    author = data.xpath("//p[@class='author']/a//text()").string(multiple=True)
    author_url = data.xpath("//p[@class='author']/a/@href").string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//h1[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h1[contains(., "Conclusion")]/preceding-sibling::p[not(contains(strong, "Manufacturer:") or contains(strong, "(as reviewed):") or contains(strong, "Price:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="page_body"]//p[not(contains(strong, "Manufacturer:") or contains(strong, "(as reviewed):") or contains(strong, "Price:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@id='page_body']//text()").string(multiple=True)

    pages = data.xpath("(//select[@id='select_pages'])[1]/option")
    for page in pages:
        page_url = 'https://www.bit-tech.net' + page.xpath("@value").string().strip()
        page_title = page.xpath(".//text()").string().strip()
        review.add_property(type='pages', value=dict(url=page_url, title=page_title))

    if pages:
        session.do(Request(page_url), process_review_last, dict(context, product=product, review=review, excerpt=excerpt, pages=True))
    else:
        context['product'] = product
        context['review'] = review
        context['excerpt'] = excerpt
        process_review_last(data: Response, context: dict[str, str], session: Session)


def process_review_last(data: Response, context: dict[str, str], session: Session):
    review = context['review']

    pros = data.xpath("(//div[@id='page_body']/p[contains(.,'The Good')]/following-sibling::ul)[1]/li")
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–►…')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath("//div[@id='page_body']/p[contains(.,'The Not So Good')]/following-sibling::ul[1]/li")
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–►…')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if context.get('pages'):
        conclusion = data.xpath('//h1[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
        if conclusion:
            review.add_property(type='conclusion', value=conclusion)

        excerpt = data.xpath('//h1[contains(., "Conclusion")]/preceding-sibling::p[not(contains(strong, "Manufacturer:") or contains(strong, "(as reviewed):") or contains(strong, "Price:"))]//text()').string(multiple=True)
        if not conclusion and not excerpt:
            excerpt = data.xpath('//div[@id="page_body"]//p[not(contains(strong, "Manufacturer:") or contains(strong, "(as reviewed):") or contains(strong, "Price:"))]//text()').string(multiple=True)
            if not excerpt:
                excerpt = data.xpath("//div[@id='page_body']//text()").string(multiple=True)

            if excerpt:
                context['excerpt'] += ' ' + excerpt

    if context['excerpt']:
        excerpt = context['excerpt'].replace('<i>', '').replace('</i>', '').replace('<laughs>', '').replace('<pause>', '').replace('<Laughs>', '').replace('<cough>', '').replace('<coughs>', '').replace('<sputters>', '').replace('<ESSID>', '').replace('&#730;', '˚').replace('<ol>', '').replace('</ol>', '').replace('<li>', '').replace('&#65533;', '-').replace('&#8211;', '-').replace('&#8217;', "'").replace('<p>', '').replace('</b>', '').replace('<br>', '').replace('<center>', '').replace('<ul>', '').replace('</li>', '').replace('</ul>', '').replace('<u>', '').replace('</u>', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
