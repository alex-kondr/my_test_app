from agent import *
from models.products import *


XTITLE = ['best ', ' vs ']


def run(context, session):
    session.queue(Request("https://huehomelighting.com/home-lighting-reviews/", use='curl'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath("//div[h3]")
    for prod in prods:
        title = prod.xpath("h3/text()").string()
        url = prod.xpath("a//@href").string()

        if 'review' in title.lower() and not any(xtitle in title for xtitle in XTITLE):
            session.queue(Request(url, use='curl'), process_product, dict(context, title=title, url=url))

    # no next page


def process_product(data, context, session):
    product = Product()
    product.name = context['title'].split(" Review")[0].split(" review")[0].split("–")[0]
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Lighting'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath("//span[@class='post-date updated']//@datetime").string()

    author = data.xpath("//h5//span[@itemprop='author']//span[@itemprop='name']//text()").string()
    author_url = data.xpath("//h5//span[@itemprop='author']/a[@rel='author' and not(contains(@href, '/about/'))]//@href").string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath("//meta[@itemprop='ratingValue']//@content").string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath("//h4[text()[contains(., 'Pros')]]//following-sibling::ul[1]/li")
    for pro in pros:
        pro = pro.xpath("text()").string()
        if pro:
            pro = pro.replace('+', '')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath("//h4[contains(., 'Cons')]//following-sibling::ul[1]/li")
    for con in cons:
        con = con.xpath("text()").string()
        if con:
            con = con.replace('-', '')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath("//span[@itemprop='description']//text()").string(multiple=True)
    if not summary:
        summary = data.xpath('//div[@itemprop="articleBody"]/p[@class]//text()').string(multiple=True)

    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath("//h3[regexp:test(.,'Verdict|Are they worth it|Should you buy it')]//following-sibling::p//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//h3[contains(.,'Overall')]//following-sibling::p[1]//text()").string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath("//div[@itemprop='reviewBody']/p[not(@class or preceding::h3[regexp:test(., 'FAQ|Verdict|Are they worth it|Should you buy it')])]//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@itemprop='articleBody']/p[not(@class or preceding::h3[regexp:test(., 'FAQ|Verdict|Are they worth it|Should you buy it')])]//text()").string(multiple=True)

    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary,'').strip()
        if conclusion:
            excerpt = excerpt.replace(conclusion,'').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
