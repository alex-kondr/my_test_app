from agent import *
from models.products import *
import simplejson
import time
import random


def run(context: dict[str, str], session: Session):
    session.sessionbreakers=[SessionBreak(max_requests=3000)]
    session.queue(Request('http://canaltech.com.br/analises/', max_age=0, force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    data_json = data.xpath('//script[@type="application/json"]/text()').string()
    if data_json:
        revs_json = simplejson.loads(data_json).get('props', {}).get('pageProps', {}).get('timelineData', {})
    else:
        revs_json = simplejson.loads(data.content).get('data', {})

    revs_json = revs_json.get('timeline', {})

    revs = revs_json.get('itens', [])
    for rev in revs:
        ssid = rev.get('id')
        title = rev.get('titulo')
        date = rev.get('data')
        url = rev.get('url')
        session.queue(Request(url, max_age=0, force_charset='utf-8'), process_review, dict(ssid=ssid, title=title, date=date, url=url))

    next_page = revs_json.get('paginacao')
    if next_page:
        next_url = 'https://i.canaltech.com.br/timelines/ultimas/tipo/analise?pagination=' + next_page
        session.queue(Request(next_url, force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    product = Product()
    product.ssid = context['ssid']
    product.category = 'Tecnologia'
    product.manufacturer = data.xpath('//td[contains(., "Desenvolvedor:")]/text()').string()

    product.name = context['title'].split('|')[0].replace('Review: ', '').replace('Review ', '').replace('Análise: ', '').replace('Análise do Jogo: ', '').replace('Análise do ', '').replace('Análise ', '').replace('Preview ', '').replace('Testamos o ', '').replace('Testamos a ', '').strip()
    if not product.name:
        product.name = context['title'].split('|')[-1]

    product.url = data.xpath('//a[@rel="sponsored" or @rel="nofollow sponsored"]/@href').string()
    if not product.url:
        product.url = context['url']

    platforms = data.xpath('//td[contains(., "Plataforma:")]/text()').string()
    genres = data.xpath('//td[contains(., "Gênero:")]/text()').string()
    if platforms and genres:
        product.category = 'Games|' + platforms.replace(', ', '/') + '|' + genres.replace(', ', '/')
    elif platforms:
        product.category = 'Games|' + platforms.replace(', ', '/')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    if context['date']:
        review.date = context['date'].split()[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('(//div[contains(h3, "Prós")]/following-sibling::ul)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//div[contains(h3, "Contras")]/following-sibling::ul)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Vale a pena") or contains(., "vale a pena")]/following-sibling::p[not(.//a[contains(@rel, "sponsored")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="contents" and h2[contains(., "Conclusão")]]/following-sibling::div[@class="contents"]/p[not(.//a[contains(@rel, "sponsored")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="contents" and h2[contains(., "Vale a pena") or contains(., "vale a pena")]]/following-sibling::div[@class="contents"]/p[not(.//a[contains(@rel, "sponsored")] or i[starts-with(normalize-space(.), "*")])]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Vale a pena") or contains(., "vale a pena")]/preceding-sibling::p[not(.//a[contains(@rel, "sponsored")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="contents" and h2[contains(., "Vale a pena") or contains(., "vale a pena")]]/preceding-sibling::div[@class="contents"]/p[not(.//a[contains(@rel, "sponsored")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="contents" and h2[contains(., "Conclusão")]]/preceding-sibling::div[@class="contents"]/p[not(.//a[contains(@rel, "sponsored")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="content-news"]/p[not(.//a[contains(@rel, "sponsored")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="contents"]/p[not(.//a[contains(@rel, "sponsored")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
