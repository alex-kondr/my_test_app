from agent import *
from models.products import *
import simplejson


XCAT = ['Acties', 'Tweedekans', 'Merchandise']


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.alternate.nl/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@id="navigation-tree"]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        sub_cats_id = cat.xpath('@data-tree-id').string()
        url = 'https://www.alternate.nl/navigation_desktop_ajax.xhtml?t=' + sub_cats_id

        if name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="py-2 px-4"]')
    for cat in cats:
        name = cat.xpath('.//a[not(@title)]/text()').string()

        if name not in XCAT and 'merken' not in name.lower():
            if 'Alle' in name or 'Meer' in name:
                name = ''
            else:
                name = name + '|'

            sub_cats = cat.xpath('.//a[@title]')

            if sub_cats:
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('text()').string()
                    url = sub_cat.xpath('@href').string()

                    if sub_name not in XCAT and 'merken' not in sub_name.lower():
                        session.queue(Request(url + '?s=rating_asc'), process_prodlist, dict(cat=context['cat'] + '|' + name + sub_name))
            else:
                url = cat.xpath('.//a[not(@title)]/@href').string()
                session.queue(Request(url + '?s=rating_asc'), process_prodlist, dict(cat=context['cat'] + '|' + name))


def process_prodlist(data, context, session):
    prods = data.xpath('//a[contains(@class, "card align-content-center productBox")]')
    for prod in prods:
        name = prod.xpath('.//div[@class="product-name font-weight-bold"]//text()').string(multiple=True)
        url = prod.xpath('@href').string()

        revs_cnt = prod.xpath('.//span[contains(@class, "ratingCoun")]/text()').string()
        if revs_cnt and revs_cnt.strip('()').isdigit() and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url), process_product, dict(name=name, url=url, revs_cnt=int(revs_cnt.strip('()'))))
        else:
            return

    next_url = data.xpath('//a[@aria-label="Volgende pagina" and not(contains(@class, "disable"))]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.sku = product.ssid
    product.category = context['cat']

    prod_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)[0]

        product.manufacturer = prod_json.get('brand', {}).get('name')

        mpn = prod_json.get('mpn')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('gtin8')
        if ean and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    if context['revs_cnt'] < 6:
        revs_url = 'https://www.alternate.nl/part/ratings_detail.xhtml?p=' + product.ssid
        options = "--compressed -X POST -H 'Referer: {}'".format(product.url)
    else:
        revs_url = 'https://www.alternate.nl/part/ratings_detail.xhtml'
        options = "--compressed -X POST -H 'Referer: {prod_url}' -H 'Cookie: JSESSIONID=nmu4f1Mg_5Yi6wFTY-jJF4sUiaasMLcXZ2fOpxt3.21; permanent=c8398e164d8385b249a2eae5f895a8166ce129f47f3716d8c7e12d14fb3a4; lastVisited=%5B%7B%22kid%22%3A1327511%2C%22lastAdded%22%3A1716814145844%7D%2C%7B%22kid%22%3A1845414%2C%22lastAdded%22%3A1716796721710%7D%5D; __cf_bm=X26b8lwSF8zNlnBkrLO38k4rp5jq6CUF8n1xytPWXwo-1716814137-1.0.1.1-_vPd6ZhAm_9PLpx027awyrq0E0Ww2XaOd5WLmmg4frQxolR162CtFVJZr1IIZSBY3D9NcOcbFUNzhImD1rZbIw' --data-raw 'ratings-section%3Aratings-list=ratings-section%3Aratings-list&ratings-section%3Aratings-list%3Aj_idt93%3A0%3Aj_idt94%3Aj_idt96=f126ac019dc221a6da73add2a048dae1&ratings-section%3Aratings-list%3Aj_idt93%3A1%3Aj_idt94%3Aj_idt96=d59b9ac31f3705ac0d272e87706b5b53&ratings-section%3Aratings-list%3Aj_idt93%3A2%3Aj_idt94%3Aj_idt96=ef8766014f2f7f9dac7d3fdf1da9e8c5&ratings-section%3Aratings-list%3Aj_idt93%3A3%3Aj_idt94%3Aj_idt96=d25eecbc7468896cf7a7e2d455e28071&ratings-section%3Aratings-list%3Aj_idt93%3A4%3Aj_idt94%3Aj_idt96=040b3df2ee99f8613f053651bd748cf5&p={ssid}&jakarta.faces.ViewState=1445424041924757489%3A-1323237574770768540&jakarta.faces.source=ratings-section%3Aratings-list%3Aj_idt130&jakarta.faces.partial.event=click&jakarta.faces.partial.execute=ratings-section%3Aratings-list%3Aj_idt130%20ratings-section%3Aratings-list%3Aj_idt130&jakarta.faces.partial.render=ratings-section%3Aratings-list&jakarta.faces.behavior.event=action&jakarta.faces.partial.ajax=true'".format(prod_url=product.url, ssid=product.ssid)

    session.queue(Request(revs_url, use='curl', options=options), process_reviews, dict(product=product))

def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="card ratingBox py-2 mb-3"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        author = ''
        date_author = rev.xpath('.//div[contains(., "review door") and not(@class)]//text()').string(multiple=True)
        if date_author:
            date_author = date_author.replace('review door ', '').split()
            if len(date_author) > 1:
                review.date = date_author[-1].strip()

                author = " ".join(date_author[:-1])
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//i[@class="fas fa-star"])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        is_verified_buyer = rev.xpath('.//div[@data-bs-toggle="popover"]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('.//span[contains(@data-url, "true")]//text()').string(multiple=True)
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//span[contains(@data-url, "false")]//text()').string(multiple=True)
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.xpath('.//span[@class="d-block py-2"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
