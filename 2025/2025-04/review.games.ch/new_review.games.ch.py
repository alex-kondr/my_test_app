from agent import *
from models.products import *


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Referer: https://www.games.ch/artikel.html' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-User: ?1' -H 'Connection: keep-alive' -H 'Cookie: my=2h7c4tqbh5mutfc52i4r7cqseo; privacyOk=1808893675428'"""


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.games.ch', use='curl', force_charset='utf-8'), process_frontpage, dict())
    session.queue(Request('https://www.games.ch/artikel.html', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[li/a[contains(., "Alle Spiele")]]//li[not(contains(., "Alle Spiele")) and @class=""]/a')
    for cat in cats:
        name = cat.xpath('.//text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url + "artikel.html", use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.do(Request(url, use='curl', options=OPTIONS, force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    if data.xpath('//a[@itemprop="articleSection" and (@href="https://www.games.ch/swissgames/" or @href="https://www.games.ch/blizzard-entertainment/")]'):
        return

    product = Product()
    product.name = context['title'].split(' - ')[0].split(' – ')[0].split('- ')[0].split(' -')[0].replace('im Test', '').strip()
    product.url = context['url']
    product.ssid = product.name.lower().replace(': ', '-').replace(' :', '-').replace(':', '-').replace(' ', '-')

    product.category = context.get('cat')
    if not product.category:
        product.category = data.xpath('//span[contains(., "getestet auf")]/strong/text()').string()
    if not product.category:
        product.category = 'Technik'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[not(@class="meta")]/time/@datetime').string()
    if date:
        review.date = date.split()[0]

    authors = data.xpath('//div[not(@class="meta")]/time/following-sibling::span/a')
    for author in authors:
        author_name = author.xpath('text()').string()
        author_ssid = author.xpath('@href').string().split('/')[-2]
        review.authors.append(Person(name=author_name, ssid=author_ssid))

    grade_overall = data.xpath('//h3[contains(., "Bewertung")]/span/@content').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[@class="label"]')
    for grade in grades:
        grade_val, grade_name = grade.xpath('.//text()').string(multiple=True).split('%')
        review.grades.append(Grade(name=grade_name.strip(), value=float(grade_val), best=100.0))

    pros = data.xpath('//ul[@class="pro"]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro and len(pro) > 1:
            pro = pro.strip('+- ')
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="con"]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con and len(con) > 1:
            con = con.strip('+- ')
            review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Fazit")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        context['conclusion'] = conclusion
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Fazit")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="col8"]/p//text()').string(multiple=True)

    context['excerpt'] = excerpt

    next_url = data.xpath('//div[@id="pagination"]//li[span]/following-sibling::li/a/@href').string()
    if next_url:
        title = review.title + ' - Pagina 1'
        review.add_property(type='pages', value=dict(title=title, url=review.url))

        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_review_next, dict(context, product=product, review=review, url=next_url, page=2))

    else:
        context['product'] = product
        context['review'] = review
        process_review_next(data, context, session)


def process_review_next(data, context, session):
    review = context['review']

    page = context.get('page', 1)
    if page > 1:
        title = review.title + ' - Pagina ' + str(page)
        review.add_property(type='pages', value=dict(title=title, url=context['url']))

        conclusion = data.xpath('//h2[contains(., "Fazit")]/following-sibling::p//text()').string(multiple=True)
        if conclusion:
            context['conclusion'] = conclusion
            review.add_property(type='conclusion', value=conclusion)

        excerpt = data.xpath('//h2[contains(., "Fazit")]/preceding-sibling::p//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[@class="col8"]/p//text()').string(multiple=True)
        if excerpt:
            context['excerpt'] += " " + excerpt

    next_url = data.xpath('//div[@id="pagination"]//li[span]/following-sibling::li/a/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_review_next, dict(context, review=review, url=next_url, page=page + 1))

    elif context['excerpt']:
        if context.get('conclusion'):
            context['excerpt'] = context['excerpt'].replace(context['conclusion'], '').strip()

        review.add_property(type="excerpt", value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)