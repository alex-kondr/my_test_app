from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://playfront.de/category/reviews/'), process_revlist, {})


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "p-wrap p-grid")]')
    for rev in revs:
        title = rev.xpath('h3[@class="entry-title"]/a/text()').string()
        url = rev.xpath('h3[@class="entry-title"]/a/@href').string()
        ssid = rev.xpath('@data-pid').string()
        session.queue(Request(url), process_review, dict(title=title, url=url, ssid=ssid))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, {})


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('Test: ')[-1].split('TEST: ')[-1].split('TEST – ')[-1].split(' – ')[0]
    product.url = data.xpath('//p/text()[contains(., "Offizielle Homepage:")]/following-sibling::a/@href').string() or data.xpath('//a[span[contains(., "Bei Amazon")]]/@href').string() or context['url']
    product.category = 'Hardware' if 'Hardware' in context['title'] else 'Spiele'
    product.ssid = context['ssid']

    manufacturer = data.xpath('//p/text()[contains(., "Entwickler:")]').string() or data.xpath('//p/text()[contains(., "Publisher:")]').string()
    if manufacturer:
        product.manufacturer = manufacturer.split(':', 1)[-1].split('//', 1)[0]

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.type = 'pro'

    date = data.xpath('//span[contains(@class, "meta-date")]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "meta-author")]/a').first()
    if author:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_ssid))

    pros = data.xpath('//div[@class="lets-review-block__pros"]/div[contains(@class, "block__pro")]/text()').strings()
    for pro in pros:
        pro = pro.strip()
        if pro:
            review.properties.append(ReviewProperty(type='pros', value=pro))

    cons = data.xpath('//div[@class="lets-review-block__cons"]/div[contains(@class, "block__con")]/text()').strings()
    for con in cons:
        con = con.strip()
        if con:
            review.properties.append(ReviewProperty(type='cons', value=con))

    grade_overall = data.xpath('//div[@class="score"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    conclusion = data.xpath('//div[contains(@class, "entry-content")]/div//div[@class="lets-review-block__conclusion"]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//blockquote[preceding-sibling::*[self::h2[@id="fazit"] or self::p[.="Fazit" or .="FAZIT"]]] ').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[.="Fazit" or .="FAZIT"]/following-sibling::p[1]//text()[not(contains(., "["))]').string(multiple=True)

    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(regexp:test(., "offizielle homepage:", "i") and a)][not(contains(., " // ") or (contains(., "Entwickler") and contains(., ":")))][not(.="Fazit" or .="FAZIT")][not(preceding-sibling::p[.="FAZIT" or .="Fazit"])][not(self::p[contains(., "»") or contains(., ">>")])]//text()[not(contains(., "[nggallery") or contains(., "[miniflickr") or contains(., "[youtube") or contains(., "[asa") or contains(., "[amazon"))]').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace('&nbsp;', ' ')

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type="excerpt", value=excerpt)

    product.reviews.append(review)

    session.emit(product)
