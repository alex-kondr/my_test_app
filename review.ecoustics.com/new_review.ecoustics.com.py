from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request("https://www.ecoustics.com/reviews", use='curl', force_charset='utf-8'), process_prodlist, dict())


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[contains(@class, "main-blog")]//div[contains(@class, "art-title")]')
    for prod in prods:
        title = prod.xpath("h2/text()").string()
        url = prod.xpath("a/@href").string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(., "Next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].split(' Review')[0]
    product.ssid = context['url'].split('/')[-2].replace('-review', '')

    product.url = data.xpath('//a[contains(., " at Amazon")]/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('//a[contains(@class, "post-cat-link")]//text()[not(contains(., "Review"))]').string()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "author-name")]//text()').string(multiple=True)
    author_url = data.xpath('//span[contains(@class, "author-name")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grades = data.xpath('//p[span[@class="score"]]')
    for grade in grades:
        grade_name = grade.xpath('text()').string(multiple=True)
        grade_val = grade.xpath('span[@class="score"]/text()').string()
        if grade_name and grade_val:
            grade_val = grade_val.count('★')
            if float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('(//h3[contains(., "Pros:")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(., "Cons:")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//span[contains(@class, "post-excerpt")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "The Bottom Line")]/following-sibling::p[not(regexp:test(., "\* Performance is highly|For more information:") or span[@class="score"])]//text()[not(preceding-sibling::*[1][self::figcaption])]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "The Bottom Line")]/preceding-sibling::p//text()[not(preceding-sibling::*[1][self::figcaption])]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "post-body")]/p[not(regexp:test(., "\* Performance is highly|For more information:") or span[@class="score"])]//text()[not(preceding-sibling::*[1][self::figcaption])]').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
