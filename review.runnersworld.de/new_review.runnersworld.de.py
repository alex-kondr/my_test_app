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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.runnersworld.de/ausruestung/', use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[contains(@class, "teaserHeader_teaser")]/div/a')
    for cat in cats:
        name = cat.xpath('.//text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name, cat_url=url))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[.//h3]')
    for rev in revs:
        title = rev.xpath('.//h3//text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    if revs:
        next_page = context.get('page', 1) + 1
        next_url = context['cat_url'] + 'seite/{}/'.format(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context, page=next_page))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace(' im Test', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-im-test', '')
    product.category = context['cat']

    product.url = data.xpath('//p[contains(., "Hier bestellen:")]/a/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//div[contains(., "Veröffentlicht am ")]/text()').string()
    if date:
        review.date = date.split(' am ')[-1]

    author = data.xpath('//a[contains(@class, "article-author")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "article-author")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//h3[contains(., "Vor- und Nachteile")]/following::p[contains(., "✅")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–✅')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–❌')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[h2]//div[contains(@class, "text_text")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Fazit")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)
# https://www.runnersworld.de/laufschuhe/hoka-ciele-x1-2-0-im-test/
    excerpt = data.xpath('//div[contains(@class, "article-text")]/div/p[not(contains(., "Hier bestellen:") or preceding::h3[contains(., "Fazit")])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
