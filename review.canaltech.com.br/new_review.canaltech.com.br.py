from agent import *
from importlib import simple
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers=[SessionBreak(max_requests=10000)]
    session.queue(Request('http://canaltech.com.br/analises/'), process_revlist, dict())


def process_revlist(data, context, session):
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
        date = rev.get('idade')
        url = rev.get('url')
        session.queue(Request(url), process_review, dict(ssid=ssid, title=title, date=date, url=url))

    next_page = revs_json.get('paginacao')
    if next_page:
        next_url = 'https://i.canaltech.com.br/timelines/ultimas/tipo/analise?pagination=' + next_page
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('|')[0].replace('Review ', '').strip()
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = 'Tecnologia'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = context['date']

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    contents_json = data.xpath('//script[@type="application/json"]/text()')
    if contents_json:
        contents = simplejson.loads(contents_json).get('props', {}).get('pageProps', {}).get('homeData', {}).get('conteudo', {}).get('conteudo', [])

        for content in contents:
            pros_cons
            pros = [content.get('pros', []) for content in contents if content.get('tipo', '') == 'pros-e-contras'][0]
            for pro in pros:
                review.add_property(type='pros', value=pro)

            cons = [content.get('contras', []) for content in contents if content.get('tipo', '') == 'pros-e-contras'][0]
            for con in cons:
                review.add_property(type='cons', value=con)


