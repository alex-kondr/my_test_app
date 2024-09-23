from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.tomshw.it/cerca?keyword=Recensione'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="flex flex-col justify-center text-start space-y-1"]')
    for rev in revs:
        title = rev.xpath('a/text()').string()
        cat = rev.xpath('.//a[@class="hover:underline text-red-500"]/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url, use='curl'), process_review, dict(title=title, cat=cat, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('|')[0].split("– Recensione")[0].split("Recensione ")[-1].split("Test ")[-1].split(',')[0].strip()
    product.ssid = context['url'].split('/')[-1].replace('-test-recensione', '').replace('-recensione', '')

    product.category = context['cat'].replace('Review', '').strip()
    if not product.category:
        product.category = 'Tech'

    product.url = data.xpath('//a[@class="shortcode_button primary"]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(., "su Amazon")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[regexp:test(@class, "^text-red-600")]/text()').string()
    author_url = data.xpath('//a[regexp:test(@class, "^text-red-600")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//svg[contains(@class, "text-red-500")])')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//h3[text()="Pro"]/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('//p[strong[contains(., "PRO")]]/following-sibling::ul[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.lstrip(' +-').strip(' .')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//h3[text()="Contro"]/following-sibling::ul[1]/li')
    if not cons:
        cons = data.xpath('//p[strong[contains(., "CONTRO")]]/following-sibling::ul[1]/li')

    for con in cons:
        con = con.xpath('.//text()'). string(multiple=True)
        if con:
            con = con.lstrip(' +-').strip(' .')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[contains(@class, "italic")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(@id, "verdetto") or contains(@id, "conclusioni") or contains(., "Verdetto") or contains(., "Conclusioni")]/following-sibling::p[not(@style or contains(@class, "text") or contains(@class, "font"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[text()="Commento"]/following-sibling::div[1]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2[contains(@id, "verdetto") or contains(@id, "conclusioni") or contains(., "Verdetto") or contains(., "Conclusioni")])[1]/preceding-sibling::p[not(@style or strong[contains(., "PRO")] or strong[contains(., "CONTRO")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div/p[not(@style or contains(@class, "text") or contains(@class, "font") or strong[contains(., "PRO")] or strong[contains(., "CONTRO")])]//text()').string(multiple=True)

    if excerpt:

        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
