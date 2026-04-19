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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.mixonline.com/technology/reviews', use='curl'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[@class="post-title"]')
    for rev in revs:
        title = rev.xpath('h2/text()').string().replace(u' ', '')
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' – ')[0].split(' — ')[0].replace('Mix Book Review Week: ', '').replace('Mix Book Review: ', '').replace('Real-World Review: ', '').replace('Field Test: ', '').replace('Reviews by Russ Long: ', '').replace(': ROAD-TESTED TIPS', '').replace(': PORTABLE AUDIO TEST SET', '').replace('Review: ', '').replace(' Review', '').strip()
    product.ssid = data.xpath('//script/@data-post-id').string()

    product.url = data.xpath('//td[contains(strong, "COMPANY:")]/a/@href').string()
    if not product.url:
        product.url = data.xpath('//p[contains(strong/text(), "WEBSITE:")]/a/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('//div[@id="breadcrumbs"]//a[not(regexp:test(., "Home|Reviews"))]/text()').string()
    if not product.category:
        product.category = 'Tech'

    manufacturer = data.xpath('//td[contains(strong, "COMPANY:")]/text()[normalize-space(.)]').string()
    if not manufacturer:
        manufacturer = data.xpath('//p[contains(strong/text(), "COMPANY:")]/text()[normalize-space(.)]').string()

    if manufacturer:
        product.manufacturer = manufacturer.strip(' •')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('(//p[@class="author-name"]/a|//a[@rel="author"])/text()').string()
    author_url = data.xpath('(//p[@class="author-name"]/a|//a[@rel="author"])/@href').string()
    if author and author_url:
        author = author.strip(' ⋅')
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        author = author.strip(' ⋅')
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//strong[contains(text(), "PROS:")]/following-sibling::text()[not(preceding::strong[contains(text(), "CONS:")])]')
    if not pros:
        pros = data.xpath('//p[contains(strong/text(), "PROS:")]/text()[normalize-space(.)]')

    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.replace('None found', '').strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//strong[contains(text(), "CONS:")]/following-sibling::text()')
    if not cons:
        cons = data.xpath('//p[contains(strong/text(), "CONS:")]/text()[normalize-space(.)]')

    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.replace('None found', '').strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="excerpt"]//text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').replace(u' ', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h4[contains(text(), "WHAT TO THINK?")]/following-sibling::p[not(preceding::h4[contains(text(), "PRODUCT SUMMARY")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//td[contains(strong/text(), "TAKEAWAY")]/text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').replace(u' ', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h4[contains(text(), "WHAT TO THINK?")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//section[@class="entry-content"]/p//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').replace(u' ', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
