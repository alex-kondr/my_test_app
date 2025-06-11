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
    session.queue(Request('https://www.hardwareonline.dk/Artikel/GetArtikler?page=1&kategori=', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs_json = simplejson.loads(data.content).get('artikler', {})

    revs = revs_json.get('results', [])
    for rev in revs:
        title = rev.get('overskrift')
        ssid = str(rev.get('id'))
        cat = rev.get('kategori')
        date = rev.get('publish_Dato')
        url = 'https://www.hardwareonline.dk/artikler/' + ssid
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, ssid=ssid, cat=cat, date=date, url=url))

    page = revs_json.get('currentPage', 0)
    page_cnt = revs_json.get('pageCount', 0)
    if page < page_cnt:
        next_url = 'https://www.hardwareonline.dk/Artikel/GetArtikler?page={}&kategori='.format(page + 1)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('Test af ', '').split(' - ')[0].split(' – ')[0].strip()
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = context['cat'] or "Tech"

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    if context['date']:
        review.date = context['date'].split('T')[0]

    author = data.xpath('//a[contains(@href, "https://www.hardwareonline.dk/profil/")]/text()').string()
    author_url = data.xpath('//a[contains(@href, "https://www.hardwareonline.dk/profil/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].split('-')[0]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('(//h3[regexp:test(normalize-space(text()), "^Plusser:|^Fordele")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//h1[contains(., "Plusser")]/following-sibling::text()[(preceding::h1)[last()][contains(., "Plusser")]][normalize-space(.)]')
        for pro in pros:
            pro = pro.string(multiple=True)
            if pro:
                pro = pro.strip(' +-*.;•–')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[regexp:test(normalize-space(text()), "^Minuser:|^Ulemper")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//h1[contains(., "Minuser")]/following-sibling::text()[(preceding::h1)[last()][contains(., "Minuser")]][normalize-space(.)]')
        for con in cons:
            con = con.string(multiple=True)
            if con:
                con = con.strip(' +-*.;•–')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

    conclusion = data.xpath('(//h3[contains(., "Konklusion")])[last()]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Konklusion")]/preceding-sibling::p[string-length(.)>10]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body/p[string-length(.)>10]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="svar-text"]/node()[not(self::table or .//a[contains(@href, "https://www.pricerunner.dk")])][string-length(.)>10]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
