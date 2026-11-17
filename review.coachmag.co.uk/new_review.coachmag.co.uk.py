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
    session.queue(Request('https://www.coachweb.com/reviews'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    page = context.get('page', 1)
    active_page = data.xpath('//div[@class="flexi-pagination"]/span[@class="active"]/text()').string()
    if page != int(active_page):
        return

    revs = data.xpath('//a[@class="article-link" and .//div[@class="article-name"]]/parent::div')
    for rev in revs:
        title = rev.xpath('.//div[@class="article-name"]/text()').string()
        cat = rev.xpath('.//a[contains(@class, "category-link")]/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url), process_review, dict(title=title, cat=cat, url=url))

    next_url = 'https://www.coachweb.com/reviews/page/' + str(page+1)
    session.queue(Request(next_url), process_revlist, dict(page=page+1))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' Review: ')[0].replace(' Review', '').strip()
    product.ssid = context['url'].split('/')[-1].replace('-review', '')
    product.category = context['cat']

    product.url = data.xpath('//a[contains(@rel, "sponsored")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time[@class="relative-date"]/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "author") and contains(text(), "By")]/*/text()').string()
    author_url = data.xpath('//span[contains(@class, "author") and contains(text(), "By")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[contains(@class, "chunk rating")]/@aria-label').string()
    if grade_overall:
        grade_overall = grade_overall.replace('Rating:', '').split(' out of ')[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('(//h4[contains(., "For")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h4[contains(., "Against")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[h1[contains(@class, "title")]]/h2[not(@class)]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Worth It?")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[div[contains(@class, "verdict")]]/p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Worth It?")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="article-body"]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)