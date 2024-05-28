from agent import *
from models.products import *
import simplejson
import re


XCAT = ['Acties', 'Tweedekans', 'Merchandise']


def remove_emoji(string):
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
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
            session.queue(Request(url), process_product, dict(context, name=name, url=url, revs_cnt=int(revs_cnt.strip('()'))))
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
        options = "--compressed -X POST -H 'Referer: {prod_url}' -H 'Cookie: permanent=c8398e164d8385b249a2eae5f895a8166ce129f47f3716d8c7e12d14fb3a4; lastVisited=%5B%7B%22kid%22%3A1697733%2C%22lastAdded%22%3A1716902476305%7D%2C%7B%22kid%22%3A1898270%2C%22lastAdded%22%3A1716901831706%7D%2C%7B%22kid%22%3A1898892%2C%22lastAdded%22%3A1716816136644%7D%2C%7B%22kid%22%3A1925081%2C%22lastAdded%22%3A1716815985076%7D%2C%7B%22kid%22%3A1864205%2C%22lastAdded%22%3A1716815966358%7D%2C%7B%22kid%22%3A1600205%2C%22lastAdded%22%3A1716814678406%7D%2C%7B%22kid%22%3A1327511%2C%22lastAdded%22%3A1716814145844%7D%2C%7B%22kid%22%3A1845414%2C%22lastAdded%22%3A1716796721710%7D%5D; JSESSIONID=qVhB3-T9P9wzrQiR3K4T7ev9tJuFaRbV2h_3NVSU.21; CONFSESSIONID=aea4216a-a77b-4d8f-a675-0686169da760; __cf_bm=DC9AO8BXC.ZQ6SOiKF0gKxNAMytZg39gt8bsLts7ee8-1716901831-1.0.1.1-qfRwpbkYmOSa7xgxL5as5y.gQLWdvrEevptPnKxs9iBd4Q7_h_9X08h7ESYrRtU1LAe81RSNc6lhx7Tbe2vP6A' --data-raw 'ratings-section%3Aratings-list=ratings-section%3Aratings-list&ratings-section%3Aratings-list%3Aj_idt93%3A0%3Aj_idt94%3Aj_idt96=656b6d166ece48fc84cf976cf33a01e1&ratings-section%3Aratings-list%3Aj_idt93%3A1%3Aj_idt94%3Aj_idt96=ec669cfc0e08fe9becda08bf16ae50fd&ratings-section%3Aratings-list%3Aj_idt93%3A2%3Aj_idt94%3Aj_idt96=57d813d650b399e4931c1a551828c13e&ratings-section%3Aratings-list%3Aj_idt93%3A3%3Aj_idt94%3Aj_idt96=6bea3b87b53f7aa4037bc007bb07c37a&ratings-section%3Aratings-list%3Aj_idt93%3A4%3Aj_idt94%3Aj_idt96=ce6fe4f1030064836fa68a0b280b97de&p={ssid}&jakarta.faces.ViewState=-2804370384737691200%3A-4152291505745804544&jakarta.faces.source=ratings-section%3Aratings-list%3Aj_idt130&jakarta.faces.partial.event=click&jakarta.faces.partial.execute=ratings-section%3Aratings-list%3Aj_idt130%20ratings-section%3Aratings-list%3Aj_idt130&jakarta.faces.partial.render=ratings-section%3Aratings-list&jakarta.faces.behavior.event=action&jakarta.faces.partial.ajax=true'".format(prod_url=product.url, ssid=product.ssid)

    session.do(Request(revs_url, use='curl', options=options), process_reviews, dict(product=product))

def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="card ratingBox py-2 mb-3"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        author = ''
        date_author = rev.xpath('.//div[(contains(., "review door") or contains(., "klant is niet meer geregistreerd")) and not(@class)]//text()').string(multiple=True)
        if date_author:
            date_author = date_author.replace('review door ', '').replace('klant is niet meer geregistreerd ', '').strip().split()
            review.date = date_author[-1].strip()

            if len(date_author) > 1:
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
            excerpt = remove_emoji(excerpt).replace('•', '').strip()
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
