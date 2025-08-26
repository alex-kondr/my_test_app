from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.gamevicio.com/analises-de-jogos-games-controles-e-consoles/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if not re.search(r'\d+ jogos ', title, re.I):
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Análise – ', '').replace('Análise | ', '').replace('#GV Review – ', '').strip()#.replace('Análise ', '')
    product.ssid = context['url'].split('/')[-2].replace('analise-', '')
    product.category = 'Tecnologia'

    product.url = data.xpath('//a[contains(@href, "https://amzn.to/")]/@href').string()
    if not product.url:
        product.url = context['url']

    platforms = data.xpath('//p[strong[contains(., "Disponível nas plataformas:")]]/text()').string()
    if platforms:
        product.category = 'Jogos|' + platforms.replace(' e ', '/')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@href, "https://www.gamevicio.com/author/") and not(img)]/text()').string()
    author_url = data.xpath('//a[contains(@href, "https://www.gamevicio.com/author/") and not(img)]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[contains(@class, "post-excerpt")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[h2[contains(text(), "Conclusão")]]/following-sibling::p[not(contains(., "Disponível nas plataformas:") or preceding-sibling::hr)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h4[contains(text(), "Conclusão")]/following-sibling::p[not(contains(., "Disponível nas plataformas:"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(text(), "Concluindo")]/following-sibling::p[not(contains(., "Disponível nas plataformas:"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[h2[contains(text(), "Conclusão")]]/preceding-sibling::p[not(preceding::h2[contains(text(), "Especificações Técnicas")])]//text()[not(starts-with(normalize-space(.), "–"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h4[contains(text(), "Conclusão")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(text(), "Concluindo")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "post_content ")]/p[not(preceding::h2[contains(text(), "Especificações Técnicas")])]//text()[not(starts-with(normalize-space(.), "–") or contains(., "Disponível nas plataformas:"))]').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
