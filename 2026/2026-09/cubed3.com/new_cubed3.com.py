from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.cubed3.com/games/reviews'), process_revlist, {})


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[@class="wrapper blog-posts"]//div/h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@class="next page-numbers"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.url = context['url']
    product.category = 'Games'
    product.manufacturer = data.xpath('//p[contains(strong, "Developer:")]/text()').string()

    product.name = data.xpath('//div[@id="game_data_meta"]/h3/a/text()').string()
    if not product.name:
        product.name = context['title'].replace('Reviews', '').replace('Review', '')

    ssid = data.xpath('//div[@class="site-content"]/article[contains(@class,"status-publish")]/@id').string()
    if ssid:
        product.ssid = ssid.replace('post-', '')
    else:
        product.ssid = product.url.split('/')[-1]

    platforms = data.xpath('//p[contains(strong, "Formats:") or contains(strong, "Format:")]/text()').string()
    if platforms:
        product.category += '|' + platforms.replace('/', '\\').replace(', ', '/')

    genres = data.xpath('//p[contains(strong, "Genres:")]/text()').string()
    if genres:
        product.category += '|' + genres.replace(', ', '/')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//p[@class="meta-date"]/span[not(a)]/text()').string()

    author = data.xpath('//p[@class="meta-date"]/span/a/text()').string()
    author_url = data.xpath('//p[@class="meta-date"]/span/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))

    grade_overall = data.xpath('//div[@id="review_score"]//h3/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    conclusion = data.xpath('//div[@id="review_summary_text"]/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "entry-content")]/p//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.split("We behandelen je gegevens met respect en sturen geen spam. Lees meer over")[0].replace(u'Ã¡', u'á').replace(u"Ã\xa0", u"à").replace(u"Ã ", u"à").replace(u"Ã¢", u"â").replace(u"Ã©", u"â").replace(u'Ã¯', u'ï').replace(u'Ã¨', u'è').replace(u'Ã¤', u'ä').replace(r"Å\ufffd", u'ō').replace(r'Å\uFFFD', u'ō').replace(u'Ã¼', u'ü').replace(u'â€�', u"'").replace(u'Ã±', u'ñ').replace(u'â€¦', u'…').replace(u'Ãª', u'ê').replace(u'Ã§', u'ç').replace(u'â€™', "'").replace(u'â€˜', "'").replace(u'Ã¶', u'ö')
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
