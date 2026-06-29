from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('http://iszene.com/forum-244.html', use='curl'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//div[@data-rate-thread='1']//span[contains(@class, 'subject')]/a")
    for rev in revs:
        title = rev.xpath(".//text()").string()
        url = rev.xpath("@href").string()

        if '[review]' in title.lower():
            session.queue(Request(url, use='curl'), process_product, dict(title=title, url=url))

    next_url = data.xpath("//a[@class='pagination_next']/@href").string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_revlist, dict())


def process_product(data, context, session):
    product = Product()
    product.name = context['title'].replace('[Review]', '').replace('[review]', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('-')[-1].replace('.html', '')

    category = data.xpath('//li[contains(., "Genre")]//text()').string(multiple=True)
    if category:
        product.category = category.replace('Genre:', '').split('(')[0].strip(': ')
    else:
        product.category = 'Tech'

    manufacturer = data.xpath('//li[contains(., "Entwickler")]/text()').string(multiple=True)
    if manufacturer:
        product.manufacturer = manufacturer.strip(': ')

    review = Review()
    review.type = 'user'
    review.title = context['title']
    review.ssid = product.ssid
    review.url = product.url

    date = data.xpath('//div[@id="posts"]/div[1]//span[@class="post_date"]/text()').string()
    if date:
        review.date = date.split(',')[0]

    author = data.xpath('//div[@id="posts"]/div[1]//span[@class="largetext"]//text()').string()
    author_url = data.xpath('//div[@id="posts"]/div[1]//span[@class="largetext"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('-')[-1].replace('.html', '')
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@id="posts"]/div[1]//img[regexp:test(@src, "https://iszene.com/images/iszene/star\d") and not(contains(@src,"_"))]/@src').string()
    if grade_overall:
        grade_overall = grade_overall.split('star')[-1].split('.')[0]
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    conclusion = data.xpath('//div[contains(span/span/text(), "Bewertung")]/following-sibling::div//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(span/span/text(), "Bewertung")]/preceding-sibling::div[contains(@class, "mycode") and not(img)]//text()[not(ancestor::ul)]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="posts"]/div[1]//div[contains(@class, "post_body")]/div[contains(@class, "mycode") and not(img)]//text()[not(ancestor::ul)]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="posts"]/div[1]//div[contains(@class, "post_body")]//text()[not(ancestor::ul)]').string(multiple=True)

    if excerpt:
        if "Bewertung:" in excerpt and not conclusion:
            excerpt_conclusion = excerpt.rsplit("Bewertung:", 1)
            if len(excerpt_conclusion) == 2:
                excerpt, conclusion = excerpt_conclusion
                if conclusion and len(conclusion.strip()) > 2:
                    review.add_property(type='conclusion', value=conclusion.strip())
            else:
                conclusion = None

        elif 'Zusammenfassung' in excerpt and not conclusion:
            excerpt, conclusion = excerpt.split('Zusammenfassung')
            if len(conclusion.strip()) > 2:
                review.add_property(type='conclusion', value=conclusion.strip())

        excerpt = excerpt.replace('Bewertung:', '').replace('Zusammenfassung', '').strip(' :')
        if len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt.strip())

            product.reviews.append(review)

            session.emit(product)
