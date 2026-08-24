from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.macworld.com/reviews', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h3//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].replace('O6 review:', '').replace('Lab tested: ', '').split(' Preview :')[0].split(' Preview:')[0].split(' Preview -')[0].split(' Preview –')[0].split(' Review:')[0].split(' Reviewed ')[0].split(' review: ')[0].split(' preview: ')[0].split(' tested: ')[0].split(' benchmarks: ')[0].replace('Preview ', '').replace('Review ', '').replace('Reviewed ', '').replace('Review: ', '').replace(' review', '').replace(' Review', '').replace(' preview', '').replace('Tested: ', '').strip()
    product.ssid = context['url'].split('/')[-2]

    product.url = data.xpath('//a[contains(., "View Deal")]/@href').string()
    if not product.url:
        product.url = context['url']

    category = data.xpath('(//ol[@itemprop="breadcrumb"]//a)[last()][not(regexp:test(., "Home|Review"))]/text()').string()
    if category:
        product.category = category.strip(' /')
    else:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//span[@class="posted-on"]/text()').string()
    if date:
        review.date = date.split(' am ')[0].split(' pm ')[0].strip().rsplit(' ', 1)[0].strip()

    author_url = data.xpath('(//span[@class="author vcard"]|//div[@class="author__name"])/a/@href').string()
    author = data.xpath('(//span[@class="author vcard"]|//div[@class="author__name"]/a)//text()').string()
    if not author:
        author = data.xpath('//div[@class="author__name"]/text()').string()

    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="starRating"]/@style').string()
    if grade_overall:
        grade_overall = float(grade_overall.split()[-1].strip(' :;'))
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//div[h3[contains(., "Pros")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[h3[contains(., "Cons")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="subheadline"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@class, "content")]/p[preceding::h2[regexp:test(., "Should You Buy|Conclusion|Verdict|Should you use", "i")] and not(regexp:test(., "^\$\d+|Check out the"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(., "Our Verdict")]/following-sibling::p[not(regexp:test(., "Price When Reviewed|This value will show the geolocated|Best Pricing Today"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//body/p[not(regexp:test(., "^\$\d+|Check out the") or preceding::h2[regexp:test(., "Should You Buy|Conclusion|Verdict", "i")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content")]/p[not(regexp:test(., "^\$\d+|Check out the") or preceding::h2[regexp:test(., "Should You Buy|Conclusion|Verdict|Should you use", "i")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
