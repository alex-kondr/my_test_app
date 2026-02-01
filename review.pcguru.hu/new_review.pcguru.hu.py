from agent import *
from models.products import *
import simplejson


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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.pcguru.hu/tesztek', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[h2]')
    for rev in revs:
        title = rev.xpath('h2/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    page_cnt = context.get('page_cnt')
    if not page_cnt:
        page_cnt = data.xpath('//li[contains(@class, "page-item")]/a[contains(@class, "last")]/@href').string()
        if page_cnt:
            page_cnt = int(page_cnt.split('?page=')[-1])

    if page_cnt:
        next_page = context.get('page', 1) + 1
        if next_page <= page_cnt:
            next_url = 'https://www.pcguru.hu/tesztek?page=' + str(next_page)
            session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(page_cnt=page_cnt, page=next_page))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' teszt ')[0].replace('', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Játékok'
    product.manufacturer = data.xpath('//div[@class="game-info"]/b[contains(text(), "Fejlesztő")]/following-sibling::p/text()').string()

    platforms = data.xpath('//div[@class="premier"]/p//text()').strings()
    if platforms:
        product.category += '|' + '/'.join([platform.strip() for platform in platforms])

    genre = data.xpath('//div[@class="game-info"]/b[contains(text(), "Műfaj")]/following-sibling::p/text()').string()
    if genre:
        product.category += '|' + genre

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    author = data.xpath('//a[contains(@href, "/profil/")]//text()').string()
    author_url = data.xpath('//a[contains(@href, "/profil/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    rev_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if rev_json:
        rev_json = simplejson.loads(rev_json)

        date = rev_json.get('datePublished')
        if date:
            review.date = date.split('T')[0]

        if not author:
            author = rev_json.get('author', {}).get('name')
            if author:
                review.authors.append(Person(name=author, ssid=author))

    if not review.date:
        date = data.xpath('//text()[contains(., "Dátum")]/following-sibling::b/text()').string()
        if date:
            review.date = date.split()[0]

    grade_overall = data.xpath('//span[@id="progress-text"]/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.replace('%', ''))
        if grade_overall > 0:
            review.grades.append(Grade(type='overall', value=grade_overall, best=100.0))

    pros = data.xpath('//div[div[contains(text(), "Pro")]]/p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[div[contains(text(), "Kontra")]]/p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[@class="news_lead"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[b[contains(text(), "Vélemény")]]/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//section[contains(@class, "content")]/p[not((em|i)[contains(text(), "A tesztkódot") or contains(text(), "A teszt szerzője")])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
