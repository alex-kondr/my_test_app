from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.gamepro.de/spiele/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="media test-list article-list game-list p-l-1 p-r-1"]')
    for rev in revs:
        title = rev.xpath('.//a[string-length(text()) > 1]/text()').string()
        manufacturer = rev.xpath('.//span[contains(text(), "Entwickler:")]/text()').string()

        cat = rev.xpath('.//span[contains(text(), "Genre:")]/text()').string()
        cats = rev.xpath('.//span[@class="label"]/text()').strings()
        if cat:
            cat = cat.replace('Genre: ', '') + '|' + '|'.join(cats)
        else:
            cat = '|'.join(cats)

        url = rev.xpath('.//a[string-length(text()) > 1]/@href').string()
        session.queue(Request(url), process_review, dict(cat=cat, title=title, manufacturer=manufacturer, ur=url))

    page = context['page', 1]
    if page > 1 and page < context['page_cnt']:
        page += 1
        next_url = 'https://www.gamepro.de/gp_cb/index.cfm?page={page}&excludeids=%5B%5D&hideplayicon=false&paging=true&showratings=true&usesearch=false&searchtype=1&adddate=false&loadmoremobileonly=false&loadmore=false&maxitemsperrowresponsive=&itemsperrowresponsive=1&showitemhr=true&itemsperrow=0&itemsnippet=contentgameitem&showtag=false&showtime=true&showstar=true&maxrows=24&filterValues=&filter=rating&teasername=Alle%20Spiele&hstyle=&htag=h2&searchterm=&datasource=&fkcontentfilter=0&fktype=0&fkid=0&id=9200_35_138&teasermodule=content&event=content%3Aajax.loadList&r=95868.80243946423'.format(page=page)
        session.queue(Request(next_url), process_revlist, dict(context, page=page))
    elif page==1:
        page_cnt = data.xpath('.//span[count(a[@class="btn btn-toc"])=1]/a/@data-page').string()
        next_url = 'https://www.gamepro.de/gp_cb/index.cfm?page=2&excludeids=%5B%5D&hideplayicon=false&paging=true&showratings=true&usesearch=false&searchtype=1&adddate=false&loadmoremobileonly=false&loadmore=false&maxitemsperrowresponsive=&itemsperrowresponsive=1&showitemhr=true&itemsperrow=0&itemsnippet=contentgameitem&showtag=false&showtime=true&showstar=true&maxrows=24&filterValues=&filter=rating&teasername=Alle%20Spiele&hstyle=&htag=h2&searchterm=&datasource=&fkcontentfilter=0&fktype=0&fkid=0&id=9200_35_138&teasermodule=content&event=content%3Aajax.loadList&r=95868.80243946423'
        session.queue(Request(next_url), process_revlist, dict(context, page=2, page_cnt=int(page_cnt)))


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1].split(',')[0]
    product.category = context['cat']

    if context.get('manufacturer'):
        product.manufacturer = context['manufacturer'].replace('Entwickler: ', '')

    review = Review()
    review.url = product.url
    review.ssid = product.ssid

    rev_json = data.xpath('//script[@type="application/ld+json" and contains(., "Product")]/text()').string()
    if rev_json:
        rev_json = simplejson.loads(rev_json.replace('\n', ''))

        date = rev_json.get('review', {}).get('datePublished')
        if date:
            review.date = date.split('T')[0]

    excerpt = data.xpath('//div[@id="game-desc-fader-root"]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)