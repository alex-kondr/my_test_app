from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.slrlounge.com/camera/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "gb-headline-text")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review |', '').split(' | ')[0].split(' Preview –')[0].replace(' Test', '').replace('Review:', '').replace(' Review', '').split(' REVIEW: ')[-1].split(' review: ')[-1].strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = 'Tech'

    product.url = data.xpath('//a[regexp:test(@href, "amzn|adorama|bhphotovideo")]/@href').string()
    if not product.url:
        product.url = context['url']

    cats = data.xpath('//a[contains(@class, "gb-button-5d91b971") and not(regexp:test(., "Reviews|News|Best"))]/text()').strings()
    if cats:
        product.category = '|'.join(cats)

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//p[contains(@class, "gb-headline-text")]/a/text()').string()
    author_url = data.xpath('//p[contains(@class, "gb-headline-text")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//h3[contains(., "Pros")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' -+.')
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//h3[regexp:test(., "Cons$| Cons$|Cons ") and not(contains(., "Pros"))]/following-sibling::*[1]/li')
    if not cons:
        con = data.xpath('//h3[regexp:test(., "Cons$| Cons$|Cons ") and contains(., "Pros")]/following-sibling::*[2]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' -+.')
        review.add_property(type='cons', value=con)

    summary = data.xpath('(//div[@class="entry-content"]/p)[1]/em//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2[regexp:test(., "Conclusion|Verdict")]|//h3[regexp:test(., "final", "i")])/following-sibling::p[not(.//strong[text()="B&H" or text()="Adorama" or text()="Amazon"] or regexp:test(., "Article written by:|Pre-Order the"))]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('â€¢', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2[regexp:test(., "Conclusion|Verdict")]|//h3[regexp:test(., "final", "i")])[1]/preceding-sibling::p[not(.//strong[text()="B&H" or text()="Adorama" or text()="Amazon"] or regexp:test(., "Article written by:|Pre-Order the"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]/p[not(.//strong[text()="B&H" or text()="Adorama" or text()="Amazon"] or regexp:test(., "Article written by:|Pre-Order the"))]//text()').string(multiple=True)

    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')

        excerpt = excerpt.replace('â€¢', '').strip()
        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
