#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = [u'Tudástár']


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def Request(url):
    options = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: gzip, br' -H 'Connection: keep-alive' -H 'Cookie: sid=43b241ec60aa122c0c22617ccaed5a63938ed82f4918335d564d1f69ca2e6b6f; vid=8315ea398db3d3212476c48ca51eabffede12b7f0605a90da811a100ee71a26e; usprivacy=1---; euconsent-v2=CQjyS0AQjyS0AAKA9AHUCdFsAP_gAEPgAA6gMcNR_G__bWlr-bb3abtkeYxP9_hr7sQxBgbJk24FzLvW7JwHx2E5NAzatqIKmRIAu3TBIQNlHJDURUCgKIgFryDMaE2U4TNKJ6BkiFMZI2tQCFxvm4tjeQCY4ur_9kc1mB-t7dr82dzyy6hHn3a5fmS1UJCdIYetDfv8ZBOT-9IEd-x8v4v4_EbpEm8eS1n_pGtp4jc6Yns_dBmxt-Tyff7Pn__rl_e7X_ve_n3zv8oXn7rr____f_-7___2b_-___b-__7J_zI8GNAATDQ6IIyyIFAgUBCCBAAoKwgAoEAQAAJA0QEAJgwIcgYALrCZACAFAAMEAIAAQYAAgAAEgAQiACAAgEAIEAgUAAYAEAQEADAwABgAoRAIAAQHQMUwIIBAsAEiMqA0wIQAEggJbKhBKBgQVwhSLHAIIERMFAAACAAUAACA-FgISSglYkEAXEF0ACAAAAFECLAikLMAQVBmi0FYEnAZGmAJHmCZJToIgCYISMgyITVBIPFMUQoIcgNilmAOniCgBl2skIf6gWbgAAAA.IAAA.YAAAAAAAAAAA; IABGPP_HDR_GppString=DBABMA~CQjyS0AQjyS0AAKA9AHUCdFsAP_gAEPgAA6gMcNR_G__bWlr-bb3abtkeYxP9_hr7sQxBgbJk24FzLvW7JwHx2E5NAzatqIKmRIAu3TBIQNlHJDURUCgKIgFryDMaE2U4TNKJ6BkiFMZI2tQCFxvm4tjeQCY4ur_9kc1mB-t7dr82dzyy6hHn3a5fmS1UJCdIYetDfv8ZBOT-9IEd-x8v4v4_EbpEm8eS1n_pGtp4jc6Yns_dBmxt-Tyff7Pn__rl_e7X_ve_n3zv8oXn7rr____f_-7___2b_-___b-__7J_zI8GNAATDQ6IIyyIFAgUBCCBAAoKwgAoEAQAAJA0QEAJgwIcgYALrCZACAFAAMEAIAAQYAAgAAEgAQiACAAgEAIEAgUAAYAEAQEADAwABgAoRAIAAQHQMUwIIBAsAEiMqA0wIQAEggJbKhBKBgQVwhSLHAIIERMFAAACAAUAACA-FgISSglYkEAXEF0ACAAAAFECLAikLMAQVBmi0FYEnAZGmAJHmCZJToIgCYISMgyITVBIPFMUQoIcgNilmAOniCgBl2skIf6gWbgAAAA.IAAA.YAAAAAAAAAAA; nosubscribe=1' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers'"""
    r = agent.Request(url, proxies=['rotating-eu'], force_charset='utf-8', use='curl', options='-s -L --insecure '+options)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://mobilarena.hu/tesztek/index.html'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="content-filter-option"]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//h4/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if 'mobilarena.hu' in url:
            session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' - ')[0].split(' – ')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]

    category = context['cat']
    if category:
        product.category = category.replace(u'Egyéb', 'Technika')
    else:
        product.category = 'Technika'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@itemprop="author"]//text()').string(multiple=True)
    author_url = data.xpath('//a[@itemprop="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].replace('.html', '')
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grades = data.xpath('//tr[td[contains(text(), " pont")] and th//text()]')
    for grade in grades:
        grade_name = grade.xpath('th//text()').string()
        grade_val = grade.xpath('td/text()').string()
        if grade_name and grade_val:
            grade_val = grade_val.replace('pont', '').split('/')[0].replace(',', '.')
            try:
                if grade_val and grade_val[0].isdigit() and float(grade_val) > 0:
                    review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))
            except:
                continue

    if not grades:
        grades = data.xpath('//tbody[tr/td[contains(text(), " pont")]]/tr[not(@class)]')
        if grades and len(grades) == 2:
            grades_name, grades_val = grades
            for grade_name, grade_val in zip(grades_name.xpath('td'), grades_val.xpath('td')):
                grade_name = grade_name.xpath('.//text()').string(multiple=True)
                grade_val = grade_val.xpath('.//text()').string(multiple=True)
                if 'pont' in grade_val and grade_name:
                    grade_val = grade_val.replace('pont', '').split('/')[0].replace(',', '.')
                    try:
                        if grade_val and grade_val[0].isdigit() and float(grade_val) > 0:
                            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))
                    except:
                        continue

    pros = data.xpath('//tr[contains(@class, "subhead-pro")]/following-sibling::tr[not(@class or preceding-sibling::tr[contains(@class, "subhead-con")])]/th')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//tr[contains(@class, "subhead-con")]/following-sibling::tr/th')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@itemprop="description about"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h3|//h2)[contains(., "Verdikt") or contains(., "Összegzés") or contains(., "összegzés")]/following-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[b[contains(text(), "Verdikt") or contains(text(), "Összegzés") or contains(text(), "összegzés")]]/following-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Konklúzió")]/following-sibling::p[not(preceding-sibling::table[contains(.//img/@src, "aw_ma_cool_hu.png")])]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h3|//h2)[contains(., "Verdikt") or contains(., "Összegzés") or contains(., "összegzés")]/preceding-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[b[contains(text(), "Verdikt") or contains(text(), "Összegzés") or contains(text(), "összegzés")]]/preceding-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Konklúzió")]/preceding-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content-body")]/p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)

    pages = data.xpath('(//div[contains(@class, "dropdown-menu-limit")])[1]/a[@class="dropdown-item"]')
    if pages:
        p = []
        last_url = ''
        for page in pages:
            title = page.xpath('text()').string()
            page_url = page.xpath('@href').string()
            p.append(dict(type='pages', value=dict(title=title, url=page_url)))

            if u'specifikáció' not in title.lower():
                last_url = page_url

        session.queue(Request(last_url), process_review_last, dict(context, excerpt=excerpt, pages=p))

    elif excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_last(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' - ')[0].split(' – ')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat'].replace(u'Egyéb', 'Technika')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@itemprop="author"]//text()').string(multiple=True)
    author_url = data.xpath('//a[@itemprop="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].replace('.html', '')
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grades = data.xpath('//tr[td[contains(text(), " pont")] and th//text()]')
    for grade in grades:
        grade_name = grade.xpath('th//text()').string()
        grade_val = grade.xpath('td/text()').string()
        if grade_name and grade_val:
            grade_val = grade_val.replace('pont', '').split('/')[0].replace(',', '.')
            try:
                if grade_val and grade_val[0].isdigit() and float(grade_val) > 0:
                    review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))
            except:
                continue

    if not grades:
        grades = data.xpath('//tbody[tr/td[contains(text(), " pont")]]/tr[not(@class)]')
        if grades and len(grades) == 2:
            grades_name, grades_val = grades
            for grade_name, grade_val in zip(grades_name.xpath('td'), grades_val.xpath('td')):
                grade_name = grade_name.xpath('.//text()').string(multiple=True)
                grade_val = grade_val.xpath('.//text()').string(multiple=True)
                if 'pont' in grade_val and grade_name:
                    grade_val = grade_val.replace('pont', '').split('/')[0].replace(',', '.')
                    try:
                        if grade_val and grade_val[0].isdigit() and float(grade_val) > 0:
                            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))
                    except:
                        continue

    pros = data.xpath('//tr[contains(@class, "subhead-pro")]/following-sibling::tr[not(@class or preceding-sibling::tr[contains(@class, "subhead-con")])]/th')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//tr[contains(@class, "subhead-con")]/following-sibling::tr/th')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@itemprop="description about"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h3|//h2)[contains(., "Verdikt") or contains(., "Összegzés") or contains(., "összegzés")]/following-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[b[contains(text(), "Verdikt") or contains(text(), "Összegzés") or contains(text(), "összegzés")]]/following-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Konklúzió")]/following-sibling::p[not(preceding-sibling::table[contains(.//img/@src, "aw_ma_cool_hu.png")])]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    for page in context['pages']:
        review.add_property(**page)

    excerpt = data.xpath('(//h3|//h2)[contains(., "Verdikt") or contains(., "Összegzés") or contains(., "összegzés")]/preceding-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[b[contains(text(), "Verdikt") or contains(text(), "Összegzés") or contains(text(), "összegzés")]]/preceding-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Konklúzió")]/preceding-sibling::p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)
    if not excerpt and not conclusion:
        excerpt = data.xpath('//div[contains(@class, "content-body")]/p[not(@align="center" or (i and not(text())) or contains(., //a[@itemprop="author"]/span/text()))]//text()').string(multiple=True)

    if excerpt:
        context['excerpt'] += ' ' + excerpt

    if context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product.reviews.append(review)

        session.emit(product)
