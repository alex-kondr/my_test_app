import simplejson

from agent import *
from models.products import *


URL = 'https://www.generation-nt.com/api/articles/list-tests-guides-0?page='


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request(URL + '1', force_charset='utf-8'), process_productlist, dict(page=1))


def process_productlist(data, context, session):
    prods_json = simplejson.loads(data.content)
    prods_html = data.parse_fragment(prods_json.get('data', {}).get('html'))
    prods = prods_html.xpath('//div[contains(@class, "flex-col justify-between mb-1")]//a')
    for prod in prods:
        url = prod.xpath('@href').string()
        title = prod.xpath('text()').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(context, url=url, title=title))

    if prods_json.get('data', {'action': 'delete'}).get('action') != 'delete':
        page = context['page'] + 1
        session.queue(Request(URL + str(page), force_charset='utf-8'), process_productlist, dict(page=page))


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = context['url'].split('-')[-1]
    product.name = context['title'].split(' : ')[0].split(', ')[0].split(' - ')[0].replace('Test de la', '').replace('On teste le', '').replace('Test de', '').replace('Test du', '').replace('Test ', '').strip()

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

    authors = data.xpath("//span[time]/a")
    # #######################################
    if len(authors) > 1:
        raise ValueError('more authors')
    ###########################################
    for author in authors:
        author_name = author.xpath("text()").string()
        author_url = author.xpath("@href").string()
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))

    pros = data.xpath('//ul[@class="list-disc marker:text-green-500"]/li//text()').strings()
    for pro in pros:
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="list-disc marker:text-red-500"]/li//text()').strings()
    for con in cons:
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "text-black text-md xs:text-md")]//span[@class="text-ellipsis overflow-hidden"]/span/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2/span[contains(., "Conclusion")]/following::p[not(@align|@id|@class|.//picture|.//a[contains(@rel, "sponsored")])][not(contains(., "La discussion est réservée aux membres GNT")) and not(contains(., "en précommande et sera disponible")) and not(contains(., "Caractéristiques")) and not(contains(., "Commencez par")) and not(contains(., "Copyright ©")) and not(starts-with(., "-"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2/span[contains(., "Conclusion")]/following::span[br]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2/span[contains(., "Conclusion")]/preceding::p[not(@align|@id|@class|.//picture|.//a[contains(@rel, "sponsored")])][not(contains(., "La discussion est réservée aux membres GNT")) and not(contains(., "en précommande et sera disponible")) and not(contains(., "Caractéristiques")) and not(contains(., "Commencez par")) and not(contains(., "Copyright ©")) and not(starts-with(., "-"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2/span[contains(., "Conclusion")]/preceding::span[br]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="w-full lg:w-2/3"]//p[not(@align|@id|@class|.//picture|.//a[contains(@rel, "sponsored")])][not(contains(., "La discussion est réservée aux membres GNT")) and not(contains(., "en précommande et sera disponible")) and not(contains(., "Caractéristiques")) and not(contains(., "Commencez par")) and not(contains(., "Copyright ©")) and not(starts-with(., "-"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)
##############################################
    product.reviews.append(review)

    session.emit(product)

#https://www.generation-nt.com/tests/ringcube-mojopac-environnement-virtuel-windows-25070
# pros-cons
# excerpt