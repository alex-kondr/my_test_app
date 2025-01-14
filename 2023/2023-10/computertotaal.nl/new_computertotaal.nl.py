from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://id.nl/'), process_catlist, {})


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="flex flex-row justify-center items-center w-full"]/a')
    sub_cats = data.xpath('//div[@class="hidden navigation_navigation-sub-menu__V_oxX"]')
    for cat, sub_cat in zip(cats, sub_cats):
        name = cat.xpath('.//span/text()').string()

        sub_cats_ = sub_cat.xpath('.//div[contains(@class, "flex-1")]')
        for sub_cat in sub_cats_:
            sub_name = sub_cat.xpath('.//span/text()').string()
            sub_url = sub_cat.xpath('div/a/@href').string()

            sub_cats2 = sub_cat.xpath('.//li')
            for sub_cat2 in sub_cats2:
                sub_name2 = sub_cat2.xpath('.//div/text()').string()
                url = sub_cat2.xpath('a/@href').string()
                if sub_name2:
                    session.queue(Request(url + '?filter=Reviews&catid=47700387'), process_revlist, dict(cat=name + '|' + sub_name + '|' + sub_name2, url=url))

            session.queue(Request(sub_url + '?filter=Reviews&catid=47700387'), process_revlist, dict(cat=name + '|' + sub_name, url=sub_url))


def process_revlist(data, context, session):
    offset = context.get('offset')
    product_groups = set()
    if offset:
        revs_json = simplejson.loads(data.raw)
        total_pages = revs_json.get('totalPages', {}).get('count')
        revs = revs_json.get('pages', {})
    else:
        revs_json = data.xpath('//script[@type="application/json"]/text()').string()
        revs_json = simplejson.loads(revs_json)
        revs = revs_json.get('props', {}).get('pageProps', {}).get('pageData', {}).get('pages', {})

    for rev in revs:
        product_group_id = rev.get('productGroup', {}).get('id')
        if product_group_id:
            product_groups.add(product_group_id)

        ssid = rev.get('id')
        author = rev.get('author', {}).get('authorName')
        date = rev.get('publishedAt').split('T')[0]
        title = rev.get('title')
        url = context['url'] + '/' + rev.get('slug')
        session.queue(Request(url), process_review, dict(context, ssid=ssid, author=author, date=date, title=title, url=url))

    product_group_ = ''
    for product_group in product_groups:
        product_group_ += '"' + str(product_group) + '",'

    if offset and offset + 100 < total_pages:
        offset = context['offset'] + 100
    elif not offset:
        offset = 20
    else:
        return

    options = """--compressed -X POST -H 'Content-Type: text/plain;charset=UTF-8' --data-raw '{"first":100,"skip":""" + str(offset) + ""","filter":{"pageType":{"eq":"47700387"}, "OR":{"productGroup":{"in":[""" + product_group_[:-1] + """]}}}}'"""
    session.queue(Request('https://id.nl/api/content/pages', use='curl', options=options), process_revlist, dict(context, offset=offset))


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = context['cat']

    name = data.xpath('//p[contains(@class, "text-2xl")]/text()').string()
    if not name:
        name = context['title']
    product.name = name.replace('Review', '').replace('getest', '').replace('...', '').replace('- Getest', '').replace('Getest:', '').replace('Massatest:', '').replace('Consumenten testen:', '').replace('Test ', '').split(' - Weinig nieuws')[0].strip()

    if 'Waar voor je geld:' in name:
        process_reviews(data, context, session)
        return

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = context['date']

    author_url = data.xpath('//div[@class="flex content-center mb-3 md:mb-4"]/a/@href').string()
    if author_url:
        review.authors.append(Person(name=context['author'], ssid=context['author'], profile_url=author_url))
    else:
        review.authors.append(Person(name=context['author'], ssid=context['author']))

    grade_overall = data.xpath('//div[contains(@class, "bg-primary p-2")]/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.replace(',', '.'))
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    summary = data.xpath('//div[@class="undefined max-w-full mb-2"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    pros = data.xpath('//div[p[text()="Pluspunten"]]//p[@class="small"]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    pros = data.xpath('//li[p[text()="Minpunten"]]')
    for pros_ in pros:
        pros_ = pros_.xpath('preceding-sibling::li/p[not(text()="Pluspunten")]')
        for pro in pros_:
            pro = pro.xpath('.//text()').string(multiple=True)
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[p[text()="Minpunten"]]//p[@class="small"]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    cons = data.xpath('//li[p[text()="Minpunten"]]')
    for cons_ in cons:
        cons_ = cons_.xpath('following-sibling::li/p')
        for con in cons_:
            con = con.xpath('.//text()').string(multiple=True)
            review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(text(), "Conclusie")]/following-sibling::p/text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[p[@class="font-bree" and text()="Conclusie"]]/div[contains(@class, "leading")]//text()').string()

    if conclusion:
        review.add_property(type='conclusion', value=conclusion.replace('...', ''))

    excerpt = data.xpath('//p[contains(., "Pluspunten")]/preceding-sibling::p[not(contains(., "Pluspunten") or contains(., "Minpunten"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "Minpunten")]/preceding-sibling::p[not(contains(., "Pluspunten") or contains(., "Minpunten"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(text(), "Conclusie")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="md:col-span-8"]/p[not(contains(., "Lees ook:") or contains(., "Ook interessant:"))]//text()|//p[contains(., "Lees ook")]/text()[not(contains(., "Lees ook:"))]').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    revs = data.xpath('//h2[@class="heading2 mt-3 mb-1"]')
    for rev in revs:
        product = Product()
        product.url = context['url']
        product.ssid = context['ssid']
        product.category = context['cat']
        product.name = rev.xpath('text()').string()
        product.ssid = product.name.lower().replace(' ', '-').replace('(', '').replace(')', '')

        review = Review()
        review.type = 'pro'
        review.title = product.name
        review.url = product.url
        review.ssid = product.ssid
        review.date = context['date']

        author_url = data.xpath('//div[@class="flex content-center mb-3 md:mb-4"]/a/@href').string()
        if author_url:
            review.authors.append(Person(name=context['author'], ssid=context['author'], profile_url=author_url))
        else:
            review.authors.append(Person(name=context['author'], ssid=context['author']))

        excerpt = rev.xpath('following-sibling::p[position() < 3]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
