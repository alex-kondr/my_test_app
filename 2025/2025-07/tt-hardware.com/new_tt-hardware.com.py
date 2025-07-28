from agent import *
from models.products import *


XCAT = ['News', 'Jeux vidéo', 'Internet', 'Software']


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
    session.queue(Request('https://tt-hardware.com/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[@id="menu-composants-1"]/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('ul//a')
            if sub_cats:
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('text()').string()
                    url = sub_cat.xpath('@href').string()
                    session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name + '|' + sub_name))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h3[contains(@class, "entry-title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if 'les ' not in title.lower() and 'meilleurs ' not in title.lower():
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

#  no next page


def process_review(data, context, session):
    strip_namespace(data)

    if len(data.xpath('//div[@class="i2-pros"]//ul')) > 1:
        return

    product = Product()
    product.name = context['title'].replace('Test du ', '').replace('Review du ', '').split(':')[0].strip()
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat']

    product.url = data.xpath('//a[contains(@class, "aawp-button")]/@href').string()
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

    author = data.xpath('//div[contains(@class, "post-author-name")]/a/text()').string()
    author_url = data.xpath('//div[contains(@class, "post-author-name")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//*[contains(., "Note globale") and regexp:test(text(), "\d{1,2}/10")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.split()[-1].split('/')[0].replace(',', '.')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('(//h3[contains(text(), "Les +")]/following-sibling::*)[1]/li')
    if not pros:
        pros = data.xpath('//div[@class="i2-pros"]//ul/li')
    if not pros:
        pros = data.xpath('(//p[contains(., "Points forts")]/following-sibling::*)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(text(), "Les –")]/following-sibling::*)[1]/li')
    if not cons:
        cons = data.xpath('//div[@class="i2-cons"]//ul/li')
    if not cons:
        cons = data.xpath('(//p[contains(., "Points faibles")]/following-sibling::*)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h3[contains(text(), "Résumé ")]/following-sibling::p[not(preceding::*[regexp:test(., "Note globale|Les \+|Les –")] or regexp:test(., "Points forts|Points faibles"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(text(), "conclusion")]/following-sibling::p[not(preceding::*[regexp:test(., "Note globale|Les \+|Les –")] or regexp:test(., "Points forts|Points faibles"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(text(), "Résumé ")]/preceding-sibling::p[not(.//span[contains(@style, "text-decoration:")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(text(), "conclusion")]/preceding-sibling::p[not(.//span[contains(@style, "text-decoration:")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "post-content")]/p[not(.//span[contains(@style, "text-decoration:")] or preceding::*[regexp:test(., "Note globale|Les \+|Les –")] or regexp:test(., "Points forts|Points faibles"))]//text()').string(multiple=True)

    if excerpt and any([grade_overall, pros, cons, conclusion]):
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
