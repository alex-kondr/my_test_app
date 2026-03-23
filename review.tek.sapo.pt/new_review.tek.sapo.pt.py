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


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://tek.sapo.pt/analises/'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    title = data.xpath('//h1[contains(@class, "title")]/text()').string()

    product = Product()
    product.name = title.replace('Análise TeK: ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Tecnologia'

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "post-title")]/div[contains(@class, "title-element")]/a/text()').string()
    author_url = data.xpath('//div[contains(@class, "post-title")]/div[contains(@class, "title-element")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//p[contains(@class, "post-excerpt")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Considerações finais") or contains(., "Veredito")]/following-sibling::p[not(contains(a/@href, "mailto") or small/i)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "Aspetos a reter")]/following-sibling::p[not(contains(a/@href, "mailto") or small/i)]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Considerações finais") or contains(., "Veredito")]/preceding-sibling::text()|//h3[contains(., "Considerações finais") or contains(., "Veredito")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "Aspetos a reter")]/preceding-sibling::text()|//p[contains(., "Aspetos a reter")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//div[contains(@class, "entry-content")]/p//text()|//div[contains(@class, "entry-content")]/text())[not(contains(., "gspb_gallery_grid") or contains(a/@href, "mailto") or small/i)]').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
