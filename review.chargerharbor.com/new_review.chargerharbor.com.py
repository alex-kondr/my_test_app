from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.chargerharbor.com/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[a[contains(., "Product Reviews")]]/ul[@class="sub-menu"]/li')
    for cat in cats:
        name = cat.xpath("a/text()").string()

        sub_cats = cat.xpath('ul[@class="sub-menu"]/li')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('a/text()').string()

            sub_cats1 = sub_cat.xpath('ul[@class="sub-menu"]/li')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('a/text()').string()
                url = sub_cat1.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
            else:
                url = sub_cat.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))
        else:
            url = cat.xpath('a/@href').string()
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath("//h2[@class='entry-title']/a")
    for prod in prods:
        title = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review:', '').replace('Review', '').strip()
    product.category = context['cat'].replace(' Reviews', '')

    product.url = data.xpath('//a[@title="Buy on Amazon"]/@href').string()
    if not product.url:
        product.url = context['url']

    ssid = data.xpath("//article/@id").string()
    if ssid:
        product.ssid = ssid.split('-')[-1]
    else:
        product.ssid = context['url'].split('/')[-2]

    if context['title'].startswith("Best"):
        process_reviews(data, context, session)
        return

    review = Review()
    review.title = context['title']
    review.type = 'pro'
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time[@class="entry-date published"]/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//span[@class='author vcard']/a//text()").string()
    author_url = data.xpath("//span[@class='author vcard']/a/@href").string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grades = data.xpath('//div[@class="rev-option"]')
    for grade in grades:
        name = grade.xpath('.//h3//text()').string()
        value, best = grade.xpath('div/span[contains(., "/")]/text()').string(multiple=True).split('/')
        review.grades.append(Grade(name=name, value=float(value), best=float(best)))

    grades = data.xpath('//div[@class="wppr-review-option"]')
    for grade in grades:
        name = grade.xpath('.//span/text()').string()
        value = grade.xpath('count(.//li[contains(@class, "good")])')
        review.grades.append(Grade(name=name, value=float(value), best=10.0))

    grade_overall = data.xpath("//div[@class='review-wu-grade']//span/text()").string()
    if not grade_overall:
        grade_overall = data.xpath('//span[contains(@class, "wppr-review-rating-grade")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type="overall", value=float(grade_overall), best=10.0))

    pros = data.xpath("//div[@class='pros']//ul/li//text()")
    if not pros:
        pros = data.xpath('//div[@class="wppr-review-pros pros"]//ul/li//text()')
    for pro in pros:
        review.add_property(type='pros', value=pro.string())

    cons = data.xpath("//div[@class='cons']//ul/li/text()")
    if not cons:
        cons = data.xpath('//div[@class="wppr-review-pros cons"]//ul/li//text()')
    for con in cons:
        review.add_property(type='cons', value=con.string())

    conclusion = data.xpath("//h1[contains(., 'Conclusion')]/following-sibling::p//text()").string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h1[contains(., "Conclusion")]/preceding-sibling::p[not(.//span[contains(@style, "text-decoration")] or strong[contains(., "Port")] or strong[contains(., "Output:")] or strong[contains(., "USB Type-C:")] or strong[contains(., "Initial Capacity:")] or contains(., "Output Capacity:") or contains(., "Built-in Cable:") or contains(., "Max Output:") or contains(., "Micro-USB input:") or contains(., "Per Micro USB Input") or contains(., "Max Output –") or contains(., "Total if both Micro-USB Inputs") or contains(., "Micro-USB Input:") or contains(., "Lightning Input:") or contains(., "USB-C Input:") or contains(., "Port:") or contains(., "Max Input:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]/p[not(.//span[contains(@style, "text-decoration")] or strong[contains(., "Port")] or strong[contains(., "Output:")] or strong[contains(., "USB Type-C:")] or strong[contains(., "Initial Capacity:")] or contains(., "Output Capacity:") or contains(., "Built-in Cable:") or contains(., "Max Output:") or contains(., "Micro-USB input:") or contains(., "Per Micro USB Input") or contains(., "Max Output –") or contains(., "Total if both Micro-USB Inputs") or contains(., "Micro-USB Input:") or contains(., "Lightning Input:") or contains(., "USB-C Input:") or contains(., "Port:") or contains(., "Max Input:"))]//text()').string(multiple=True)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    revs = data.xpath('//div[@class="entry-content"]/h1[b and .//text()]')
    for i, rev in enumerate(revs, 1):
        product = Product()
        product.name = rev.xpath('.//text()').string()
        product.ssid = product.name.lower().replace(' ', '-').replace(',', '')
        product.category = context['cat'].replace(' Reviews', '')

        product.url = rev.xpath('following-sibling::p[count(preceding-sibling::h1[b and .//text()])=' + str(i) + ']/a[contains(@href, "amazon")]/@href').string()
        if not product.url:
            product.url = context['url']

        review = Review()
        review.type = 'pro'
        review.name = product.name
        review.ssid = product.ssid
        review.url = product.url

        date = data.xpath('//time[@class="entry-date published"]/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = data.xpath("//span[@class='author vcard']/a//text()").string()
        author_url = data.xpath("//span[@class='author vcard']/a/@href").string()
        if author and author_url:
            review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        excerpt = rev.xpath('following-sibling::p[not(.//span[contains(@style, "text-decoration")] or strong[contains(., "Port")] or strong[contains(., "Output:")] or strong[contains(., "USB Type-C:")] or strong[contains(., "Initial Capacity:")] or contains(., "Output Capacity:") or contains(., "Built-in Cable:") or contains(., "Max Output:") or contains(., "Micro-USB input:") or contains(., "Per Micro USB Input") or contains(., "Max Output –") or contains(., "Total if both Micro-USB Inputs") or contains(., "Micro-USB Input:") or contains(., "Lightning Input:") or contains(., "USB-C Input:") or contains(., "Port:") or contains(., "Max Input:"))][count(preceding-sibling::h1[b and .//text()])=' + str(i) + ']//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
