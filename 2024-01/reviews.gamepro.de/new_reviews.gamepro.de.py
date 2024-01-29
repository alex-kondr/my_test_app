from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.gamepro.de/spiele/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="media test-list article-list game-list p-l-1 p-r-1"]')
    for rev in revs:
        title = rev.xpath('.//a[string-length(text()) > 1]/text()').string()
        manufacturer = rev.xpath('(.//span[contains(text(), "Entwickler:")]|.//p[contains(text(), "Entwickler:")])/text()[normalize-space()]').string()

        genre = rev.xpath('(.//span[contains(text(), "Genre:")]|.//p[contains(text(), "Genre:")])/text()').string()
        platforms = rev.xpath('.//span[@class="label"]/text()').strings()
        platforms = [platform.strip() for platform in platforms]
        cat = '/'.join(platforms)
        if genre:
            cat += '|' + genre.replace('Genre: ', '')

        url = rev.xpath('.//a[string-length(text()) > 1]/@href').string()
        session.queue(Request(url), process_review, dict(cat=cat, title=title, manufacturer=manufacturer, url=url))

    next_page = context.get('page', 1) + 1
    total_pages = context.get('total_pages', data.xpath('.//span[count(a[@class="btn btn-toc"])=1]/a/@data-page').string())
    if next_page <= int(total_pages):
        next_url = 'https://www.gamepro.de/gp_cb/index.cfm?page={next_page}&excludeids=%5B%5D&hideplayicon=false&paging=true&showratings=true&usesearch=false&searchtype=1&adddate=false&loadmoremobileonly=false&loadmore=false&maxitemsperrowresponsive=&itemsperrowresponsive=1&showitemhr=true&itemsperrow=0&itemsnippet=contentgameitem&showtag=false&showtime=true&showstar=true&maxrows=24&filterValues=&filter=rating&teasername=Alle%20Spiele&hstyle=&htag=h2&searchterm=&datasource=&fkcontentfilter=0&fktype=0&fkid=0&id=9200_35_138&teasermodule=content&event=content%3Aajax.loadList&r=95868.80243946423'.format(next_page=next_page)
        session.queue(Request(next_url), process_revlist, dict(context, page=next_page, total_pages=total_pages))


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.ssid = context['url'].split('/')[-1].split(',')[0]
    product.category = context['cat']

    product.url = data.xpath('//td[contains(., "Webseite:")]/following-sibling::td/a/@href').string()
    if product.url and 'http' not in product.url:
        product.url = 'https://' + product.url
    elif not product.url:
        product.url = context['url']

    if context.get('manufacturer'):
        manufacturer = context['manufacturer'].replace('Entwickler: ', '').strip('-')
        if len(manufacturer) > 1:
            product.manufacturer = manufacturer

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    rev_json = data.xpath('//script[@type="application/ld+json" and contains(., "Product")]/text()').string()
    if rev_json:
        rev_json = simplejson.loads(rev_json.replace('\n', ''))

        date = rev_json.get('review', {}).get('datePublished')
        if date:
            review.date = date.split('T')[0]

        author = rev_json.get('review', {}).get('author', {}).get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev_json.get('review', {}).get('reviewRating', {}).get('ratingValue')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    excerpt = data.xpath('//div[@id="game-desc-fader-root"]/p//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.split('Fazit:')

        if len(excerpt) == 2:
            review.add_property(type='conclusion', value=excerpt[1])

        review.add_property(type='excerpt', value=excerpt[0])

        product.reviews.append(review)

        session.emit(product)
