from agent import *
from models.products import *


XCAT = ['Tester', 'DMZ Rekommenderar', 'Artikel', 'Toppklass', 'Nyheter', 'Jämförande', 'Jämförande test', 'Topphändelser', 'Reportage']


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.datormagazin.se/kategori/artikel/tester/', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h2[contains(@class, "post-title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if title and url:
            session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].split('Test:')[-1].split(':')[-1].replace('GODLIKE', '').strip()
    product.url = context['url']
    product.category = 'Technik'

    ssid = data.xpath('//article/@id').string()
    if ssid:
        product.ssid = ssid.replace('post-', '')
    else:
        product.ssid = product.url.rstrip('/').split('/')[-1]

    category = data.xpath('//a[@rel="category"]/text()').string()
    if category and category not in XCAT:
        product.category = category.replace('test', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "post-author")]/a/text()').string()
    author_url = data.xpath('//span[contains(@class, "post-author")]/a/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="dmz-rv__badge-num"]/text()').string()
    if grade_overall and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=6.0))

    pros = data.xpath('//*[contains(@class, "dmz-rv__list--pros")]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//div[contains(p/text(), "För")]/p[contains(@class, "text")]//text()').string(multiple=True)
        if pros:
            pros = pros.strip(' +-*.:;•,–')
            if len(pros) > 1:
                review.add_property(type='pros', value=pros)

    cons = data.xpath('//*[contains(@class, "dmz-rv__list--cons")]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//div[contains(p/text(), "Emot")]/p[contains(@class, "text")]//text()').string(multiple=True)
        if cons:
            cons = cons.strip(' +-*.:;•,–')
            if len(cons) > 1:
                review.add_property(type='cons', value=cons)

    award = data.xpath('//img[@class="dmz-rv__award"]/@src').string()
    if not award:
        award = data.xpath('//a[contains(@href, "_toppklass_")]/@href').string()
    if not award:
        award = data.xpath('//img[contains(@src, "_rek_")]/@src').string()

    if award:
        review.add_property(type='awards', value=dict(image_src=award))

    summary = data.xpath('//div[contains(@class, "entry-content")]/h2/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@class="dmz-rv__rec"]/p[@class="dmz-rv__text"]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "post-content")]/p//text()[not(contains(., "SPECIFIKATIONER"))]').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)