from agent import *
from models.products import *


X_CATS = ['İŞLEMCİ NESLİ', 'OYUN BİLGİSAYARLARI', 'OYUNCU MONİTÖRÜ', 'İŞ BİLGİSAYARLARI', 'İŞ İSTASYONLARI']


def run(context, session):
    session.queue(Request("https://www.monsternotebook.com.tr", force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//a[use]/parent::li')
    for cat in cats:
        name = cat.xpath('a//text()').string()
        url = cat.xpath('a/@href').string()
        if name not in X_CATS:
            session.queue(Request(url, force_charset='utf-8'), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    cats = data.xpath('//li[@class="s2"]')
    for cat in cats:
        name = cat.xpath('span/a//text()').string()

        cats1 = cat.xpath('.//li[@class="s3"]')
        for cat1 in cats1:
            cat1_name = cat1.xpath('span/a//text()').string()
            url = cat1.xpath('span/a/@href').string()

            subcats = cat1.xpath('.//li[@class="s4"]')
            if subcats and context['cat'] == "AKSESUARLAR":
                for subcat in subcats:
                    subcat_name = subcat.xpath('span/a//text()').string()
                    url = subcat.xpath('span/a/@href').string()
                    session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + "|" + name + "|" + cat1_name + "|" + subcat_name))
            else:
                session.queue(Request(url, force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + "|" + name + "|" + cat1_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="ems-prd-inner"]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('.//h3[@class="ems-prd-name"]//text()').string(multiple=True)
        product.category = context['cat'].replace('TÜM LAPTOPLAR', 'LAPTOPLAR')
        product.url = prod.xpath('.//a[@class="ems-prd-lnk"]/@href').string()
        product.manufacturer = 'Monster Notebook'
        product.sku = prod.xpath('.//div[@id="plhUrun_UrnKod"]//text()').string()
        product.ssid = product.sku

        mpn = prod.xpath('.//div[@id="plhUrun_urunKodu"]//text()').string()
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        revs_cnt = prod.xpath('.//span[@class="toplamYorum"]//text()').string()
        if revs_cnt and int(revs_cnt) > 0:
            revs_url = "https://www.monsternotebook.com.tr/yorum/ascYorum_ajx.aspx?urn={sku}&ps=6&page=1&lang=tr-TR".format(sku=product.sku)
            session.queue(Request(revs_url), process_reviews, dict(product=product, page=1, revs_cnt=int(revs_cnt)))

    # no next page


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[contains(@class, "yorum_main yorum_main")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@class').string().split('yorum_main_')[-1]
        review.title = rev.xpath('.//div[@class="tableYorumListe_yorumBaslik"]//text()').string(multiple=True)
        review.date = rev.xpath('.//span[@class="spnYorumTarih"]//text()').string()

        author = rev.xpath('.//span[@class="spnYorumAdSoyad"]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[@class="tableYorumListe_ratingbar star-rating"]/@title').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//span[contains(@id, "URUNUSATINALDI")]//text()')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('.//span[contains(@id, "lblYorumEvet")]//text()').string()
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//span[contains(@id, "lblYorumHayir")]//text()').string()
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.xpath('.//div[@class="tableYorumListe_yorumMesaj"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    offset = context.get('offset', 0) + 6
    if offset < context['revs_cnt']:
        next_page = context['page'] + 1
        next_url = "https://www.monsternotebook.com.tr/yorum/ascYorum_ajx.aspx?urn={sku}&ps=6&page={next_page}&lang=tr-TR".format(sku=product.sku, next_page=next_page)
        session.do(Request(next_url), process_reviews, dict(product=product, offset=offset, page=next_page, revs_cnt=context['revs_cnt']))
    elif product.reviews:
        session.emit(product)
