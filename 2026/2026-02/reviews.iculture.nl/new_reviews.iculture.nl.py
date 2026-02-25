from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.iculture.nl/reviews/', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//ul[@class="categories"]/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('iCulture bekijkt:')[-1].split('Review: ')[-1].split('Getest: ')[-1].split(' (review)')[0].split('mini review:')[0].split(' (eerste ervaringen)')[0].split(' review:')[0].split('Mini-review: ')[-1].split('Videoreview: ')[-1].split('Review ', 1)[-1].split(' review', 1)[0].split('Praktijktest ')[-1].strip()
    product.ssid = data.xpath('//article[contains(@id, "post-")]/@id').string().split('-')[-1]
    product.category = context['cat']

    product.url = data.xpath('//a[contains(@rel, "sponsored") and not(contains(@href, "https://www.iculture.nl/"))]/@href').string()
    if not product.url:
        product.url = data.xpath('//div[@data-name="link-cards"]/a/@href').string()
    if not product.url:
        product.url = data.xpath('//div[contains(@class, "review__links")]/a/@href').string()
    if not product.url:
        product.url = context['url']

    manufacturer = data.xpath('//p[contains(., "Uitgever:")]//text()').string()
    if not manufacturer:
        manufacturer = data.xpath('//li[contains(., "Producent:")]/a/text()').string()
    if not manufacturer:
        manufacturer = data.xpath('//a[ancestor::p[contains(., "Fabrikant:")]][1]/text()').string()

    if manufacturer:
        product.manufacturer = manufacturer.split('"@type":"Brand","name":"')[-1].split('"}')[0]

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time[not(@class)]/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[time[not(@class)]]/span[contains(@class, "text")]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    rev_json = data.xpath('//script[contains(., "var dataLayer = ")]/text()').string()
    if rev_json:
        rev_json = simplejson.loads(rev_json.replace('var dataLayer = ', '').strip(' ;:'))

        if rev_json:
            if not date:
                date = rev_json[0].get('date-published') or rev_json[0].get('date')
                if date:
                    review.date = date.split('T')[0]

            if not author:
                author = rev_json[0].get('author')
                if author:
                    review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[@class="score"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[@class="pros"]/ul/li')
    if not pros:
        pros = data.xpath('(//p[contains(., "Pluspunten:")]/following-sibling::ul)[1]/li')
    if not pros:
        pros = data.xpath('(//h4[contains(., "Pluspunten")]/following-sibling::ul)[1]/li')
    if not pros:
        data.xpath('(//h4[contains(., "Positieve punten")]/following-sibling::ul)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;:')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="cons"]/ul/li')
    if not cons:
        cons = data.xpath('(//p[contains(., "Minpunten:")]/following-sibling::ul)[1]/li')
    if not cons:
        cons = data.xpath('(//h4[contains(., "Minpunten")]/following-sibling::ul)[1]/li')
    if not cons:
        cons = data.xpath('(//h4[contains(., "Negatieve punten")]/following-sibling::ul)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;:')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[header]/div[@class="mb-4"]/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2|//h3|//h4)[contains(@id, "conclusie") or contains(., "Conclusie")]/following-sibling::p[preceding-sibling::h2[1][contains(@id, "conclusie") or contains(., "Conclusie")] or preceding-sibling::h3[1][contains(@id, "conclusie") or contains(., "Conclusie")] or preceding-sibling::h4[1][contains(@id, "conclusie") or contains(., "Conclusie")]]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'â€�', '”').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(((//h2|//h3|//h4)[contains(@id, "conclusie") or contains(., "Conclusie")]/preceding-sibling::div//p|(//h2|//h3|//h4)[contains(@id, "conclusie") or contains(., "Conclusie")]/preceding-sibling::p)[not(@class or img[contains(@src, "favicon.chief.tools/")])]|//div[contains(@class, "excerpt")])[not((preceding::h2|preceding::h3|preceding::h4)[contains(@id, "conclusie") or regexp:test(., "Conclusie|Positieve punten|Negatieve punten", "i")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//body//p[not(@class or img[contains(@src, "favicon.chief.tools/")])]|//div[contains(@class, "excerpt")])[not((preceding::h2|preceding::h3|preceding::h4)[contains(@id, "conclusie") or regexp:test(., "Conclusie|Positieve punten|Negatieve punten", "i")])]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'â€�', '”').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
