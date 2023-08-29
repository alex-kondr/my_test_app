import simplejson

from agent import *
from models.products import *


URL = 'https://www.generation-nt.com/api/articles/list-tests-guides-0?page='


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request(URL + '1', force_charset='utf-8'), process_revlist, dict(page=1))


def process_revlist(data, context, session):
    revs_json = simplejson.loads(data.content)
    new_data = data.parse_fragment(revs_json.get('data', {}).get('html'))
    revs = new_data.xpath('//div[contains(@class, "flex-col justify-between mb-1")]//a')
    for rev in revs:
        url = rev.xpath('@href').string()
        title = rev.xpath('text()').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(context, url=url, title=title))

    if revs_json.get('data', {'action': 'delete'}).get('action') != 'delete':
        next_page = context['page'] + 1
        session.queue(Request(URL + str(next_page), force_charset='utf-8'), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = context['url'].split('-')[-1]
    product.name = context['title'].replace('Comparatif et test de ', '').replace(' Technical Preview', '').replace('PREVIEW -', '').replace('Preview ', '').replace('On a testé le', '').replace('Test :', '').replace('Test de la', '').replace('On teste le', '').replace('Test de', '').replace('Test du', '').replace('TEST du', '').replace('Test ', '').replace('TEST ', '').replace('test ', '').split(' : ')[0].split(', ')[0].split(' - ')[0].strip()

    category = data.xpath('//a[not(@title)]/span[@itemprop="name"]/text()').string()
    if category:
        product.category = category.replace('Tests & ', '')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.ssid = product.ssid
    review.url = product.url

    date = data.xpath("//time/@datetime").string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//span[time]/a").first()
    if author:
        author_name = author.xpath("text()").string()
        author_url = author.xpath("@href").string()
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))

    pros = data.xpath('//ul[@class="list-disc marker:text-green-500"]/li//text()[normalize-space(.)]').strings()
    for pro in pros:
        pro = pro.replace('- ', '').replace('...', '').strip()
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="list-disc marker:text-red-500"]/li//text()[normalize-space(.)]').strings()
    for con in cons:
        con = con.replace('- ', '').replace('...', '').strip()
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "text-black text-md xs:text-md")]//span[@class="text-ellipsis overflow-hidden"]/span/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2/span[contains(., "Conclusion")]/following::p[not(@align|@id|@class|.//em|.//strong|.//picture|.//a[contains(@rel, "sponsored")])][not(contains(., "La discussion est réservée aux membres GNT")) and not(contains(., "AliExpress au prix")) and not(contains(., "Amazon")) and not(contains(., "en précommande et sera disponible")) and not(contains(., "Caractéristiques")) and not(contains(., "Commencez par")) and not(contains(., "Copyright ©")) and not(starts-with(., "-"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2/span[contains(., "Conclusion")]/following::span[br]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2/span[contains(., "Conclusion")]/following::p[@class="MsoNormal"]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2/span[contains(., "Conclusion")]/preceding::p[not(@align|@id|@class|.//em|.//strong|.//picture|.//a[contains(@rel, "sponsored")])][not(contains(., "La discussion est réservée aux membres GNT")) and not(contains(., "AliExpress au prix")) and not(contains(., "Amazon")) and not(contains(., "en précommande et sera disponible")) and not(contains(., "Caractéristiques")) and not(contains(., "Commencez par")) and not(contains(., "Copyright ©")) and not(starts-with(., "-"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2/span[contains(., "Conclusion")]/preceding::span[br]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2/span[contains(., "Conclusion")]/preceding::p[@class="MsoNormal"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="w-full lg:w-2/3"]//p[not(@align|@id|@class|.//em|.//picture|.//a[contains(@rel, "sponsored")])][not(contains(., "La discussion est réservée aux membres GNT")) and not(contains(., "en précommande et sera disponible")) and not(contains(., "Caractéristiques")) and not(contains(., "Commencez par")) and not(contains(., "Copyright ©")) and not(starts-with(., "-"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="w-full lg:w-2/3"]//span[br and not(em)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//body[not(@class)]/span/span/span/text()|//body[not(@class)]//p[not(@align|@id|@class|.//em|.//picture|.//a[contains(@rel, "sponsored")]) and not(contains(., "Commencez par"))]//text())[normalize-space(.)][not(contains(., "La discussion est réservée aux membres GNT")) and not(contains(., "en précommande et sera disponible")) and not(contains(., "Caractéristiques")) and not(contains(., "Copyright ©")) and not(starts-with(., "-"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//span[br]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[@class="MsoNormal"]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)
##############################################
    product.reviews.append(review)

    session.emit(product)
