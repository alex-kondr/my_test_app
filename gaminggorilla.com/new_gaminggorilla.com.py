from agent import *
from models.products import *


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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://gaminggorilla.com/hardware/'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//li[contains(@class, "blog-story")]/a[@data-wpel-link="internal"]')
    for rev in revs:
        title = rev.xpath('.//h2/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Hardware'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "author-name")]//text()').string()
    author_url = data.xpath('//span[contains(@class, "author-name")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//span[contains(@class, "post-excerpt")]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Conclusion|Final Thoughts")]/following-sibling::p[not(@align="center" or @style="text-align: center;")]//text()').string()
    if not conclusion:
        conclusion = data.xpath('//p[contains(strong, "Conclusion")]/following-sibling::p[not(@align="center" or @style="text-align: center;")]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Conclusion|Final Thoughts")]/preceding-sibling::p[not(@align="center" or @style="text-align: center;")]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(strong, "Conclusion")]/preceding-sibling::p[not(@align="center" or @style="text-align: center;")]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@id, "content-main")]/p[not(@align="center" or @style="text-align: center;")]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
