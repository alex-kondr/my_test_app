from agent import *
from models.products import *


XCAT = ['Mumsnet Rated', 'Offers']


def run(context, session):
    session.queue(Request('https://www.mumsnet.com/h/reviews', use="curl", force_charset='utf-8'), process_category, dict())


def process_category(data, context, session):
    cats = data.xpath('//div[contains(@class, "p-4 mt-8 flex")]/a')
    if not cats:
        process_revlist(data, context, session)

    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        if url and name and name not in XCAT:
            session.queue(Request(url, use="curl", force_charset='utf-8'), process_category, dict(context, cat=context.get('cat', '') + '|' +name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="flex pt-6"]/div[p]')
    for rev in revs:
        title = rev.xpath('p[contains(@class, "text-xl")]/text()').string()
        url = rev.xpath('a/@href').string()
        if title and url:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_reviews, dict(context, title=title, url=url))


def process_reviews(data, context, session):
    prods = data.xpath('//div[@class="mt-8"][div[@class="prose"]/p][not(.//blockquote)][contains(., "Buy now from")]')
    for prod in prods:
        name = prod.xpath('preceding-sibling::div[@class="mt-8"][div[@class="prose"]/h2][1]//h2[last()]//text()').string(multiple=True)
        if not name:
            process_rewiew(data, context, session)
            return

        product = Product()
        product.url = prod.xpath('.//a[contains(., "Buy now from")]/@href').string()
        if not product.url:
            product.url = context['url']

        product.name = name.split(':', 1)[-1].split(' off')[-1].split('on the')[-1].split('. ', 1)[-1]
        product.ssid = product.name.strip().replace(" ", "_").replace('(', '').replace(')', '').lower()
        product.category = context["cat"].strip(' |')

        review = Review()
        review.type = 'pro'
        review.url = context['url']
        review.ssid = product.ssid
        review.title = context['title']

        author = data.xpath('//p[@class="mt-4 text-gray-600 text-sm"]//a').first()
        if author:
            author_name = author.xpath('text()').string()
            author_url = author.xpath('@href').string()
            if author_url and author_name:
                review.authors.append(Person(name=author_name, ssid=author_name, profile_url=author_url))
            elif author_name:
                review.authors.append(Person(name=author_name, ssid=author_name))

        date = data.xpath('//p[@class="mt-4 text-gray-600 text-sm"]/text()').string(multiple=True)
        if date:
            review.date = date.split('updated ')[-1]

        pros = prod.xpath('(.//h3[contains(., "What we love")] | .//h3[contains(., "What we like")])/following-sibling::ul[1]/li//text()')
        for pro in pros:
            value = pro.string()
            if value:
                review.add_property(type='pros', value=value)

        cons = prod.xpath('(.//h3[contains(., "What to know")] | .//h3[contains(., "What we don\'t like")])/following-sibling::ul[1]/li//text()')
        for con in cons:
            value = con.string()
            if value:
                review.add_property(type='cons', value=value)

        grade_overall = prod.xpath('.//p[contains(., "Rating: ")]//text()').string()
        if grade_overall:
            value = grade_overall.split('/')[0].split(': ')[-1]
            max_value = grade_overall.split('/')[-1]
            review.grades.append(Grade(type='overall', value=float(value), best=float(max_value)))

        excerpt = prod.xpath('(.//h3[contains(.,"Our verdict")] | .//h2[contains(.,"Our verdict")])[1]/following-sibling::p[not(contains(., "Read next:"))][not(contains(., "Related:"))]//text()').string(multiple=True)
        if not excerpt:
            excerpt = prod.xpath('.//p[not(contains(., "Buy now from"))][not(contains(.//a/@href, "talk"))][not(contains(., "Read next:"))][not(contains(., "Related:"))]//text() | .//h3//text()').string(multiple=True)

        if excerpt:
            excerpt = excerpt.split('What Mumsnet users say')[0]
            if grade_overall:
                excerpt = excerpt.replace(grade_overall, '')

            excerpt = excerpt.split('Read next:')[0]

            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

            session.emit(product)


def process_rewiew(data, context, session):
    product = Product()
    product.url = context["url"]
    product.name = data.xpath('//h1[@class="mt-12 lg:mt-16 h1"]/text()').string().split('review')[0]
    product.ssid = product.url.split('/')[-1]
    product.category = context["cat"].strip(' |')

    review = Review()
    review.type = 'pro'
    review.url = product.url
    review.ssid = product.ssid
    review.title = context['title']

    author = data.xpath('//p[@class="mt-4 text-gray-600 text-sm"]//a').first()
    if author:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()
        if author_url and author_name:
            review.authors.append(Person(name=author_name, ssid=author_name, profile_url=author_url))
        elif author_name:
                review.authors.append(Person(name=author_name, ssid=author_name))

    date = data.xpath('//p[@class="mt-4 text-gray-600 text-sm"]/text()').string(multiple=True)
    if date:
        review.date = date.split('updated ')[-1]

    pros = data.xpath('(//h3[contains(., "What we love")] | //h3[contains(., "What we like")])/following-sibling::ul/li//text() | //h2[contains(., "Pros")]/following-sibling::ul[1]/li//text()')
    for pro in pros:
        value = pro.string()
        if value:
            review.add_property(type='pros', value=value)

    cons = data.xpath('(//h3[contains(., "What to know")] | //h3[contains(., "What we don\'t like")])/following-sibling::ul/li//text() | //h2[contains(., "Pros")]/following-sibling::ul[1]/li//text()')
    for con in cons:
        value = con.string()
        if value:
            review.add_property(type='cons', value=value)

    grade_overall = data.xpath('//h3[contains(., "rating:")]/text()').string()
    if grade_overall:
        value = grade_overall.split('/')[0].split(': ')[-1]
        max_value = grade_overall.split('/')[-1]
        review.grades.append(Grade(type='overall', value=float(value), best=float(max_value)))

    summary = data.xpath('//div[@class="mt-4 text-xl prose"]/p//text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Final verdict")]/following-sibling::p[not(contains(., "Related: "))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(., "Our verdict")]/following-sibling::p[not(contains(., "Related: "))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[@class="mt-8"]/div[@class="prose"]/p[not(.//a[contains(., "Buy now from")])][not(contains(., "Read next:"))][not(preceding::text()[1][contains(., "Key specs")])][not(preceding::text()[1][contains(., "About Mumsnet Reviews")])][not(preceding::text()[contains(., "About the author")])][not(contains(., "Related:"))][not(contains(., "Overall star rating: "))]//text()').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        if summary:
            excerpt = excerpt.replace(summary, '')

        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
