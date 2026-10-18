from agent import *
from models.products import *


XCAT = ['Autres tests']


def run(context: dict[str, str], session: Session):
    session.queue(Request("https://www.zonetravaux.fr/", use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//ul[@class="sub-menu"]//li/a[contains(@href,"category/tests") and not(i) and text()]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name and url and name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if title and url and 'Test ' in title:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].replace('Test : ', '').replace('Test outillage : ', '').replace('Test outil : ', '').replace('Test outillage placo : ', '').replace('Test accessoires : ', '').replace('Test Bosch Pro : ', '').replace('Test ', '').strip()
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat']

    product.url = data.xpath('//a[@rel="noreferrer noopener"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//div[@class="wpb_wrapper" and not(@style)]/div/div/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "author-name")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "author-name")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))

    pros = data.xpath('(//p[regexp:test(., "«.\+.»")]/following-sibling::ul)[1]/li//text()')
    if not pros:
        pros = data.xpath('//p[regexp:test(., "«.\+.»")]/following-sibling::text()[contains(., "=>")]')
    if not pros:
        pros = data.xpath('(//p[regexp:test(., "«.\+.»")]/following-sibling::p)[1][contains(., "– ")]/text()')
    if not pros:
        pros = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//p[strong[contains(text(), "Les avantages du Mini Rod Cut")]]/following-sibling::p[1]/strong/span/text()')

    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip('( =>–+-*.:;•,)')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p[regexp:test(., "«.–.»")]/following-sibling::ul)[1]/li//text()')
    if not cons:
        cons = data.xpath('//p[regexp:test(., "«.–.»")]/following-sibling::text()[contains(., "=>")][following::text()[contains(., "« + »")]]')
    if not cons:
        cons = data.xpath('(//p[regexp:test(., "«.–.»")]/following-sibling::p)[1][contains(., "– ")]/text()')
    if not cons:
        cons = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//p[strong[contains(text(), "Les avantages du Mini Rod Cut")]]/following-sibling::p[preceding-sibling::p[strong[contains(text(), "Les inconvénients")]]]/strong/span/text()')

    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip('( =>+-*.:;•,–)')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p[not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[@class='tdb-block-inner td-fix-index']//*[preceding-sibling::h2[1][contains(., 'Conclusion et prix')]]//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h1[contains(text(), "Pour conclure …")]/following-sibling::p[position() < last() - 3][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//*[preceding-sibling::h2[1][contains(text(), "Résultat final")]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//*[preceding-sibling::h2[1][contains(text(), "Conclusion")]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//*[preceding-sibling::h2[1][contains(text(), "Résultat")]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//p[preceding-sibling::p/strong[contains(text(), "Bilan et Conclusion")]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//p[preceding-sibling::p/strong[contains(text(), "Conclusion et bilan")]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//p[preceding-sibling::p/strong[contains(text(), "Conclusion")]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text() | //div[@class="tdb-block-inner td-fix-index"]//blockquote[preceding-sibling::p[1][contains(., "Conclusion")]]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//p[preceding-sibling::p/strong[contains(text(), "Admirez le résultat")]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//p[preceding-sibling::p/strong[contains(text(), "BILAN ET CONCLUSION")]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//p[preceding-sibling::p/strong[contains(text(), "Admirez le résultat")]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//p[preceding-sibling::p/strong[contains(text(), "Résultat (presque) final")]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//h2[contains(text(), "En conclusion")]//following-sibling::p[not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(text(), "L’avis")]/following-sibling::p[not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('''//div[@class='tdb-block-inner td-fix-index']//*[preceding-sibling::h2[1][contains(text(), 'Conclusion et prix')]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]//text()''').string(multiple=True)

    if conclusion:
        context['conclusion'] = conclusion

    excerpt = data.xpath('//div[regexp:test(@class, "td_block_wrap tdb_single_content|post-content")]//p[not(preceding::text()[contains(., "[vc_tabs]")] and following::text()[contains(., "[/vc_tab]")])][not(contains(., "[taq_review]"))][not(contains(., "[amazon_link"))][not(contains(., "sur ") and contains(., "ZoneTravaux"))][not(contains(., "[vc_tabs]"))][not(preceding::text()[contains(., "————")] and following::text()[contains(., "————")])][not(p[contains(., "En conclusion :")])][not(preceding::p[contains(., "En conclusion :")])][not(contains(., "————"))][not(contains(., "Caractéristiques du produit :"))] [not(contains(., "Plus produit "))][not(contains(., "Les différentes étapes"))][not(contains(., "En conclusion"))][not(preceding-sibling::p[regexp:test(., "en synthèse :", "i")])][not(regexp:test(., "en synthèse :", "i"))][not(preceding::*[regexp:test(., "conclusion", "i")])][not(strong[regexp:test(., "\d/")])][not(preceding-sibling::h2[contains(text(), "L’avis")])]//text()').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        context['excerpt'] = excerpt.strip()

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url and int(next_url.split('/')[-2].strip('/ ')) > 1:
        title = review.title + " - Pagina 1"
        review.add_property(type='pages', value=dict(title=title, url=review.url))

        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_review_next, dict(context, product=product, review=review, page=2))

    else:
        context['product'] = product
        context['review'] = review
        process_review_next(data: Response, context: dict[str, str], session: Session)


def process_review_next(data: Response, context: dict[str, str], session: Session):
    review = context['review']

    page = context.get('page', 1)
    if page > 1:
        title = review.title + " - Pagina " + str(page)
        url = data.xpath('//link[@rel="canonical"]/@href').string()
        review.add_property(type='pages', value=dict(title=title, url=url))

        pros = data.xpath('(//p[regexp:test(., "«.\+.»")]/following-sibling::ul)[1]/li//text()')
        if not pros:
            pros = data.xpath('//p[regexp:test(., "«.\+.»")]/following-sibling::text()[contains(., "=>")]')
        if not pros:
            pros = data.xpath('(//p[regexp:test(., "«.\+.»")]/following-sibling::p)[1][contains(., "– ")]/text()')
        if not pros:
            pros = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//p[strong[contains(text(), "Les avantages du Mini Rod Cut")]]/following-sibling::p[1]/strong/span/text()')

        for pro in pros:
            pro = pro.string(multiple=True)
            if pro:
                pro = pro.strip('( =>–+-*.:;•,)')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

        cons = data.xpath('(//p[regexp:test(., "«.–.»")]/following-sibling::ul)[1]/li//text()')
        if not cons:
            cons = data.xpath('//p[regexp:test(., "«.–.»")]/following-sibling::text()[contains(., "=>")][following::text()[contains(., "« + »")]]')
        if not cons:
            cons = data.xpath('(//p[regexp:test(., "«.–.»")]/following-sibling::p)[1][contains(., "– ")]/text()')
        if not cons:
            cons = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//p[strong[contains(text(), "Les avantages du Mini Rod Cut")]]/following-sibling::p[preceding-sibling::p[strong[contains(text(), "Les inconvénients")]]]/strong/span/text()')

        for con in cons:
            con = con.string(multiple=True)
            if con:
                con = con.strip('( =>+-*.:;•,–)')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

        conclusion = data.xpath('//div[@class="tdb-block-inner td-fix-index"]/p[preceding-sibling::h2[contains(., "Conclusion")]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")] or strong[contains(., "ZT")])][not(.//a[regexp:test(., "forum", "I")])][not(preceding-sibling::p[contains(., "Installation de")])][not(contains(., "Installation de"))]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//p[preceding-sibling::h2[regexp:test(., "conclusion", "i")]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])][not(.//a and regexp:test(., "forum", "I"))]//text() | //div[@class="tdb-block-inner td-fix-index"]//blockquote[preceding-sibling::h2[regexp:test(., "conclusion", "i")]]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//div[@class="tdb-block-inner td-fix-index"]//*[preceding-sibling::h2[1][contains(text(), "Conclusion et prix")]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]/text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//div[@class="td-post-content tagdiv-type"]//*[preceding-sibling::h2[1][contains(text(), "Le résultat final")]][not(contains(., "[amazon_link"))][not(contains(., "sur ") and strong[contains(., "ZoneTravaux")])]/text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//p[strong[contains(text(), "Conclusion")]]/following-sibling::blockquote[1]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//p[preceding-sibling::p[regexp:test(., "pour conclure", "i")] and following-sibling::p[strong]][following-sibling::p[contains(., "« – »")]]/text()').string(multiple=True)

        if conclusion:
            context['conclusion'] = context.get('conclusion', '') + conclusion

        excerpt = data.xpath('//div[regexp:test(@class, "td_block_wrap tdb_single_content|post-content")]//p[not(preceding::text()[contains(., "[vc_tabs]")] and following::text()[contains(., "[/vc_tab]")])][not(contains(., "[taq_review]"))][not(contains(., "[amazon_link"))][not(contains(., "sur ") and contains(., "ZoneTravaux"))][not(contains(., "[vc_tabs]"))][not(preceding::text()[contains(., "————")] and following::text()[contains(., "————")])][not(p[contains(., "En conclusion :")])][not(preceding::p[contains(., "En conclusion :")])][not(contains(., "————"))][not(contains(., "Caractéristiques du produit :"))] [not(contains(., "Plus produit "))][not(contains(., "Les différentes étapes"))][not(contains(., "En conclusion"))][not(preceding-sibling::p[regexp:test(., "en synthèse :", "i")])][not(regexp:test(., "en synthèse :", "i"))][not(preceding::*[regexp:test(., "conclusion", "i")])][not(strong[regexp:test(., "\d/")])][not(preceding-sibling::h2[contains(text(), "L’avis")])]//text()').string(multiple=True)
        if excerpt:
            if conclusion:
                excerpt = excerpt.replace(conclusion, '')

            context['excerpt'] += " " + excerpt.strip()

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_review_next, dict(context, page=page+1))

    elif context.get('excerpt'):
        if context.get('conclusion'):
            review.add_property(type='conclusion', value=context['conclusion'])

        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
