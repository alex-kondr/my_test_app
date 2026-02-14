from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.tomshw.it/cerca?keyword=Recensione', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[h2 and p and a]')
    for rev in revs:
        title = rev.xpath('h2/text()').string()
        cat = rev.xpath('p[not(regexp:test(., "Recensione|Review|Sponsorizzato", "i"))]/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, cat=cat, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('Recensione |')[0].split('|')[0].split("– Recensione")[0].split("Recensione ")[-1].split("Test ")[-1].split(', recensione:')[0].split(' recensione')[0].replace(' - Recensione', '').replace('Recensioni ', '').replace(' Recensione', '').strip()
    product.ssid = context['url'].split('/')[-1].replace('-test-recensione', '').replace('-recensione', '')
    product.category = context['cat'] or 'Tecnologia'

    product.url = data.xpath('//a[@class="shortcode_button primary"]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(., "su Amazon")]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(@class, "button-v2-yellow")]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(@rel, "sponsored")]/@href').string()
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

    author = data.xpath('//p[contains(text(), "a cura di")]/span//text()').string(multiple=True)
    author_url = data.xpath('//p[span/a[contains(@href, "https://www.tomshw.it/author")]]//a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//div[contains(@class, "md:flex")]/svg[contains(@class, "text-red-500") and contains(@viewbox, "576")]) + count(//div[contains(@class, "md:flex")]/svg[contains(@class, "text-red-500") and contains(@viewbox, "536")]) div 2')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    if not grade_overall:
        grade_overall = data.xpath('//div[contains(@class, "rounded-full") and circle]/span/text()').string()
        if not grade_overall:
            grade_overall = data.xpath('//div[h2[contains(text(), "verdetto")]]/div[svg]/span/text()').string()

        if grade_overall:
            grade_overall = grade_overall.replace(',', '.').strip(' +-*.')
            if len(grade_overall) > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('(//h3[text()="Pro"]/following-sibling::ul)[1]/li')
    if not pros:
        pros = data.xpath('(//p[strong[contains(., "PRO")]]/following-sibling::ul)[1]/li')
    if not pros:
        pros = data.xpath('//li[contains(text(), "Pro")]/ul/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.lstrip(' +-').strip(' .')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[text()="Contro"]/following-sibling::ul)[1]/li')
    if not cons:
        cons = data.xpath('(//p[strong[contains(., "CONTRO")]]/following-sibling::ul)[1]/li')
    if not cons:
        cons = data.xpath('//li[contains(text(), "Contro")]/ul/li')

    for con in cons:
        con = con.xpath('.//text()'). string(multiple=True)
        if con:
            con = con.lstrip(' +-').strip(' .')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[div/h1]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(@id, "verdetto") or contains(@id, "conclusioni") or contains(., "Verdetto") or contains(., "Conclusioni")]/following-sibling::p[not(@style or contains(@class, "text") or contains(@class, "font"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[text()="Commento"]/following-sibling::div[1]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[h2[contains(., "verdetto")]]/following-sibling::div/div[@class="text-base italic"]//text()').string(multiple=True)

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
