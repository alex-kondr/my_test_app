from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.binomania.it/recensioni-binomania/', use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//ul/li/a[contains(@href, "/tag/")]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h1[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Video recensione dello ', '').replace('Video recensione del ', '').replace('Videorecensione del ', '').replace(' video e recensione', '').replace('Video e recensione del ', '').replace('Video e recensione dei ', '').replace('Recensione del ', '').replace('Recensione ', '').split(' – ')[0].replace('Preview dei ', '').replace(' videorecensione', '').split('- preview')[0].split(': recensione')[0].replace(' preview', '').replace('Test approfondito:', '').replace('Video recensione ', '').split('- preview')[0].replace(' video e recensione', '').replace(' preview', '').replace(' videorecensione', '').replace('RECENSIONE DEL ', '').replace('Video recensione ', '').replace('Preview ', '').split(': prestazioni')[0].replace('. la video recensione', '').replace('RECENSIONE DELLA ', '').replace('Videorecensione della ', '').strip().capitalize()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('recensione-', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="entry-author"]//text()').string()
    author_url = data.xpath('//span[@class="entry-author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('(//p[contains(., "PREGI")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p[contains(., "DIFETTI")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[h2[regexp:test(., "IN SINTESI|CONCLUSIONE", "i")]]//p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="entry-content"]//p[@class="" and not(parent::td or preceding::h2[regexp:test(., "PREGI E DIFETTI|IN SINTESI|RINGRAZIAMENTI|DISCLAIMER|CONCLUSIONE", "i")])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
