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
    session.queue(Request('https://www.soccercleats101.com/category/cleat-reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' Preview: Who ')[0].split(' Review: ')[0].replace(' – The review', '').replace(' Review', '').replace(' review', '').replace(' Tested', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = 'Cleat'

    product.url = data.xpath('//a[contains(@href, "https://www.pntrs.com/t/")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="post-meta-author"]//text()').string(multiple=True)
    author_url = data.xpath('//span[@class="post-meta-author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//h3[regexp:test(., "Summary", "i")]/following-sibling::p//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//h2[regexp:test(., "Summary", "i")]/following-sibling::p//text()').string(multiple=True)

    conclusion = data.xpath('//h3[regexp:test(., "Final Thoughts", "i")]/following-sibling::p[not(preceding::h3[regexp:test(., "Summary|Where to Find Them", "i")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[regexp:test(., "Verdict", "i")]/following-sibling::p[not(preceding::h3[regexp:test(., "Summary|Where to Find Them", "i")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[regexp:test(., "Conclusion", "i")]/following-sibling::p[not(preceding::h3[regexp:test(., "Summary|Where to Find Them", "i")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[regexp:test(., "Summary", "i")]]//text()[regexp:test(., "Summary", "i")]').string(multiple=True)

    if conclusion and summary:
        review.add_property(type='summary', value=summary)
    elif summary:
        conclusion = summary

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[regexp:test(., "Final Thoughts", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h3[regexp:test(., "Verdict", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h3[regexp:test(., "Conclusion", "i")]/preceding-sibling::p//text()').string(multiple=True)

    if not excerpt:
        excerpt = data.xpath('//div[@class="entry"]/p[not(preceding::h3[regexp:test(., "Summary|Where to Find Them", "i")] or strong[contains(., "Summary")])]//text()').string(multiple=True)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
