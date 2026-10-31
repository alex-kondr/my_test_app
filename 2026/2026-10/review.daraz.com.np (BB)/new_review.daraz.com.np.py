#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def RequestCats():
    options = """--compressed \
    -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:158.0) Gecko/20100101 Firefox/158.0' \
    -H 'Accept: application/json' \
    -H 'Accept-Encoding: deflate' \
    -H 'Content-type: application/x-www-form-urlencoded' \
    -H 'x-i18n-language: en' \
    -H 'x-i18n-regionID: NP' \
    -H 'entrance: ' \
    -H 'traffic: drz-replatform' \
    -H 'Connection: keep-alive' \
    -H 'Cookie: t_fv=1792833811847; t_uid=iRwx6SRZ2lHMWpZaDw0oD0Gu2AfgxuAV; t_sid=IYQEcJaO3P5GlGKH6CmdmonNGOH2dM9s; utm_channel=NA; hng=NP|en-NP|NPR|524; lwrid=AgGhbTj1%2BXyKIstyhFoevA129P%2B%2B; lzd_cid=641c411c-38a7-4934-93ae-cf97144b6d5e; lzd_sid=1692b67e3d7e54219397e060249bab41; _tb_token_=35e65359ee7a4; lwrtk=AAIEatzplH/0dWbPWkxsF11PLLOl+uknXe7nAA4YqYlhujQHnZesSRE=; _m_h5_tk=9e17d386726124c2c45cd861abc0d472_1792842065243; _m_h5_tk_enc=36651d9c5a0e431f2c3b14439a31077c; tfstk=gkiiLcA7nVz_rDfeqsr6MX4s79LR1lZbSjIYMoF28WPC61It3-qmnjXYuCZtm2cn35lmhdw4gjl0MVpp2AM_coR0m3K-CzNcqBh07r5UTvwAgi8L7WP0DcAJw3KKShx3ZQHANtE0L-NUQRy4_pfUh8E4QiS2KWy0FZ5ZgoJHK-yN_Sy40MrU38r4gjr2KkyT3oPqgoJnLWw40SlQZFPs0Doe7Yli-ZldZDwgS7ka_sCxbMz15AV3w7oUI_LtIWDiID2gI74AnpXmbXHqXcaBuZqjp4cmubRdW5uuEX4-SQjiZfwqTJl9HZwnoxo7ffAG55uttzwU8tx7pbFECcuHh6kZw5qnzmpAm7ur3cziR31aM2Hom-mXGHco3Yg4-mfG4oQFzh7OcJJxxZ_L7Jw3wKj0Uv7xCq-eKpbyhPyQC7nvKZ7ONiSARpvhzE4adRNN.; cna=MGtjI/iEGkgCAVvhoricACrr; xlly_s=1; utm_origin=https://www.daraz.com.np/; isg=BBQUyh_NAhtVXpbXIPyCfeNn5lKGbThXduEvAK70Qx8imbbj1nyW52hSmQkBenCv; epssw=14*WCnskz_DDWxhADz8a3znDr2kDKUSUUnDDDZ1tWsBDg4KDK2ZoX4ZHk3IYlNHDlcKo0DDDiMlHpx5kbYISDDzGO_DPHS_AwE3MyXjlcLLVMYx5vERP1QjsLThyuQTDrAv34M0TWXEcsgcO_zkDKQ0KSj90CbRJq7mKy1nWD-8apecDDd4oDDDDDd4DtthiditlZcwh3ZwVCilDrO8z5pV2_AqI58GrPQwDS3Xh3gmpzudPW-MDqOdh7DrD1HnQJ-wBYDWWoGBwBZiY9IV8AZZYAUXvGqDG5ULgEvEKXYSif3QE0DDK4h_PWjNMBu-i1hBpKc2tXa-bzu-BRCMOLcrpOn86An.' \
    -H 'Sec-Fetch-Dest: empty' \
    -H 'Sec-Fetch-Mode: cors' \
    -H 'Sec-Fetch-Site: same-site'"""
    url = 'https://acs-m.daraz.com.np/h5/mtop.lazada.guided.shopping.categories.categorieslpcommon/1.0/?jsv=2.7.5&appKey=24937400&t=1792835553093&sign=f8a2cdd3cdaedd54db8515fb142dd39e&api=mtop.lazada.guided.shopping.categories.categoriesLpCommon&v=1.0&type=originaljson&isSec=1&AntiCreep=true&timeout=20000&dataType=json&sessionOption=AutoLoginOnly&x-i18n-language=en&x-i18n-regionID=NP&data=%7B%22regionId%22%3A%22NP%22%2C%22language%22%3A%22en%22%2C%22platform%22%3A%22pc%22%2C%22isbackup%22%3A%22true%22%2C%22backupParams%22%3A%22language%2CregionID%2Cplatform%2CpageNo%22%2C%22moduleName%22%3A%22categoriesLpMultiFloor%22%7D'
    r = agent.Request(url, use='curl', proxies=['rotating-eu'], force_charset='utf-8', options='-s -L --insecure '+options)
    return r


def RequestProds(cat, page):
    cat_url = urllib.quote(cat)
    url = 'https://www.daraz.com.np/catalog/?ajax=true&from=hp_categories&isFirstRequest=true&page={page}&q={cat}&service=all_channel&spm=a2a0e.searchlist.cate_1.3.44232dcbbM9s9l&src=all_channel'.format(cat=cat_url, page=page)
    r = Request(url, force_charset='utf-8')
    return r


def RequestRevs(ssid, page):
    url = 'https://my.daraz.com.np/pdp/review/getReviewList?itemId={ssid}&pageSize=5&filter=0&sort=0&pageNo={page}'.format(ssid=ssid, page=page)
    r = Request(url, force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.queue(RequestCats(), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    try:
        cats = simplejson.loads(data.content).get('data', {}).get('resultValue', {}).get('categoriesLpMultiFloor', {}).get('data', [])
    except:
        return

    for cat in cats:
        name = cat.get('categoryName')

        subcats = cat.get('level2TabList', [])
        for subcat in subcats:
            subcat_name = subcat.get('categoryName')
            session.queue(RequestProds(subcat_name, 1), process_prodlist, dict(cat=name, subcat=subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    try:
        prods_json = simplejson.loads(data.content)
    except:
        prods_json = {}

    prods = prods_json.get('mods', {}).get('listItems', [])
    for prod in prods:
        pr = dict()
        pr['name'] = prod.get('name')
        pr['url'] = 'https:' + prod.get('itemUrl').split('?')[0]
        pr['ssid'] = prod.get('itemId')
        pr['sku'] = prod.get('skuId')
        pr['category'] = context['cat'] + '|' + context['subcat']

        manufacturer = prod.get('brandName')
        if manufacturer and manufacturer.lower() != 'no brand':
            pr['manufacturer'] = manufacturer

        revs_cnt = prod.get('review')
        if revs_cnt and int(revs_cnt) > 0 and pr['ssid'] and not session.seen(pr['ssid']):
            session.queue(RequestRevs(pr['ssid'], 1), process_reviews, dict(product=pr, revs_cnt=int(revs_cnt)))

    prods_cnt = context.get('prods_cnt', prods_json.get('mainInfo', {}).get('totalResults'))
    offset = context.get('offset', 0) + 40
    if prods_cnt and offset < int(prods_cnt):
        next_page = context.get('page', 1) + 1
        session.queue(RequestProds(context['subcat'], next_page), process_prodlist, dict(context, prods_cnt=prods_cnt, offset=offset, page=next_page))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.ssid = context['product']['ssid']
    product.sku = context['product'].get('sku')
    product.category = context['product']['category']
    product.url = context['product']['url']
    product.manufacturer = context['product'].get('manufacturer')

    try:
        revs = simplejson.loads(data.content).get('model', {}).get('items', [])
    except:
        revs = []

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev['reviewRateId'])
        review.date = rev.get('reviewTime')

        author_name = rev.get('buyerName')
        author_ssid = rev.get('buyerId')
        author_email = rev.get('buyerEmail')
        if author_name and author_ssid and author_email:
            review.authors.append(Person(name=author_name, ssid=str(author_ssid), email=author_email))
        elif author_name and author_ssid:
            review.authors.append(Person(name=author_name, ssid=str(author_ssid)))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.get('isPurchased')
        if is_verified is True:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('upVotes')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('downVotes')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.get('reviewTitle')
        excerpt = rev.get('reviewContent')
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    revs_cnt = context['revs_cnt']
    offset = context.get('offset', 0) + 5
    if revs_cnt and offset < int(revs_cnt):
        next_page = context.get('page', 1) + 1
        session.queue(RequestRevs(product.ssid, next_page), process_prodlist, dict(context, offset=offset, page=next_page))
