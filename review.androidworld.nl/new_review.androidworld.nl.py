from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://androidworld.nl/ajax/tag/6057/load-latest-articles/0/1000?format=default'), process_revlist, dict())


def process_revlist(data, context, session):
    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('latestArticles', [])
    for rev in revs:
        title = rev.get('title')
        ssid = rev.get('id')
        date = rev.get('date')
        author = rev.get('user')
        url = 'https://androidworld.nl' if 'https' not in rev.get('url') else ''
        url += rev.get('url')
        session.queue(Request(url), process_review, dict(title=title, ssid=ssid, date=date, author=author, url=url))

    offset = context.get('offset', 0) + 1000
    if offset <= len(revs):
        next_page = context.get('page', 0) + 1
        next_url = 'https://androidworld.nl/ajax/tag/6057/load-latest-articles/{next_page}/1000?format=default'.format(next_page=next_page)
        session.queue(Request(next_url), process_revlist, dict(offset=offset, page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Mini-review:', '').replace('Mini-review ', '').split('review:')[0].split(': mid-ranger doet veel')[0].split(': meer klasse')[0].split(': tweede toptoestel')[0].split(': flinke accu')[0].split(': smartphone met')[0].split(': smartwatch voor')[0].split(': minder sprekend')[0].split(': terugkeer van')[0].split(': 24 uur met')[0].split(': herkenbare smartphone')[0].split(': wie niet')[0].split(': sterke comeback')[0].split(': verfijning van')[0].split(': en de laatste')[0].split(': met stip op')[0].split(': stijlvolle metalen')[0].split(': topsmartphones')[0].split(': de nieuwe ')[0].split(': verrassende ')[0].split(': (g)een grote')[0].split(': nieuwe LG')[0].split(': budget en')[0].split(': chique uitstraling')[0].split(': waar voor')[0].replace('reviews op Androidworld', '').replace(' videoreview', '').replace('Review:', '').replace('Preview nieuwe ', '').replace('Preview ', '').replace('Cameratest:', '').replace('(videoreview)', '').replace(' getest', '').replace('[video]', '').replace('Review ', '').replace(' review', '').split('PureView eerste')[0].split('preview van de')[0].split(": 'laatste kans'")[0].replace('Videoreview ', '').strip()
    product.url = context['url']
    product.ssid = str(context['ssid'])
    product.category = 'Technik'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = context['date']

    if context['author']:
        review.authors.append(Person(name=context['author'], ssid=context['author']))

    grade_overall = data.xpath('//div[@class="ring-label"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//li[i[contains(@class, "fa-plus-circle")]]')
    if not pros:
        pros = data.xpath('//p[starts-with(normalize-space(.), "+ ")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' +-→')
        review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//h3[contains(., "Pluspunten")]/following-sibling::p[1]/text()[normalize-space()]')
        if not pros:
            pros = data.xpath('//h3[contains(., "Minpunten")]/preceding-sibling::p[starts-with(normalize-space(.), "→")]//text()[normalize-space()]')
        for pro in pros:
            pro = pro.string(multiple=True).strip(' +-→')
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//li[i[contains(@class, "a-minus-circle")]]')
    if not cons:
        cons = data.xpath('//p[starts-with(normalize-space(.), "- ") and not(.//a)]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' +-→')
        review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//h3[contains(., "Minpunten")]/following-sibling::p[1]/text()[normalize-space()]')
        if not cons:
            cons = data.xpath('//h3[contains(., "Minpunten")]/following-sibling::p[starts-with(normalize-space(.), "→")]//text()[normalize-space()]')
        for con in cons:
            con = con.string(multiple=True).strip(' +-→')
            review.add_property(type='cons', value=con)

    summary = data.xpath('//section[@id="article-content"]/following-sibling::p[not(preceding-sibling::h2 or preceding-sibling::h1)]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2[contains(., "Conclusie")]|//h3[contains(., "Conclusie")])/following-sibling::p[not(@id or starts-with(normalize-space(.), "+ ") or starts-with(normalize-space(.), "- ") or starts-with(normalize-space(.), "→ "))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2[contains(., "Conclusie")]|//h3[contains(., "Conclusie")])/preceding::p[not(@id or .//@datetime or starts-with(normalize-space(.), "+ ") or starts-with(normalize-space(.), "- ") or starts-with(normalize-space(.), "→ "))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//section[@id="article-content"]/following::p[@class="editor-paragraph mb-4 text-base text-secondary dark:text-zinc-50" and not(@id or starts-with(normalize-space(.), "+ ") or starts-with(normalize-space(.), "- ") or starts-with(normalize-space(.), "→ "))]//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
