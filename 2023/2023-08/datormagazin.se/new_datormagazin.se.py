from agent import *
from models.products import *


URL = 'https://www.datormagazin.se/wp-admin/admin-ajax.php'
OPTIONS = "--data-raw 'action=bunyad_block&block%5Bid%5D=grid&block%5Bprops%5D%5Bcat_labels%5D=&block%5Bprops%5D%5Bcat_labels_pos%5D=top-left&block%5Bprops%5D%5Breviews%5D=bars&block%5Bprops%5D%5Bpost_formats_pos%5D=center&block%5Bprops%5D%5Bload_more_style%5D=a&block%5Bprops%5D%5Bmeta_cat_style%5D=text&block%5Bprops%5D%5Bmedia_style_shadow%5D=0&block%5Bprops%5D%5Bshow_post_formats%5D=1&block%5Bprops%5D%5Bmeta_above%5D%5B%5D=cat&block%5Bprops%5D%5Bmeta_above%5D%5B%5D=date&block%5Bprops%5D%5Bmeta_above%5D%5B%5D=read_time&block%5Bprops%5D%5Bmeta_below%5D%5B%5D=author&block%5Bprops%5D%5Bmeta_below%5D%5B%5D=comments&block%5Bprops%5D%5Bmedia_ratio%5D=&block%5Bprops%5D%5Bmedia_ratio_custom%5D=&block%5Bprops%5D%5Bread_more%5D=none&block%5Bprops%5D%5Bcontent_center%5D=0&block%5Bprops%5D%5Bexcerpts%5D=1&block%5Bprops%5D%5Bexcerpt_length%5D=20&block%5Bprops%5D%5Bstyle%5D=&block%5Bprops%5D%5Bpagination%5D=true&block%5Bprops%5D%5Bpagination_type%5D=load-more&block%5Bprops%5D%5Bspace_below%5D=none&block%5Bprops%5D%5Bsticky_posts%5D=false&block%5Bprops%5D%5Bcolumns%5D=2&block%5Bprops%5D%5Bexclude_ids%5D%5B%5D=42117&block%5Bprops%5D%5Bexclude_ids%5D%5B%5D=42077&block%5Bprops%5D%5Bexclude_ids%5D%5B%5D=42069&block%5Bprops%5D%5Bexclude_ids%5D%5B%5D=42057&block%5Bprops%5D%5Bexclude_ids%5D%5B%5D=42044&block%5Bprops%5D%5Bmeta_items_default%5D=true&block%5Bprops%5D%5Bpost_type%5D=&block%5Bprops%5D%5Bposts%5D=100&block%5Bprops%5D%5Btaxonomy%5D=category&block%5Bprops%5D%5Bterms%5D=73&paged="
NOCATS = ['Tester', 'DMZ Rekommenderar', 'Artikel', 'Toppklass', 'Nyheter', 'Jämförande', 'Jämförande test', 'Topphändelser', 'Reportage']


def run(context, session):
    session.queue(Request(URL, use='curl', options=OPTIONS+"1'", max_age=0, force_charset='utf-8'), process_revlist, dict(page=1))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="content" and .//span[@class="meta-item post-author"]]')
    for rev in revs:
        title = rev.xpath('.//h2[@class="is-title post-title"]/a/text()').string()
        author = rev.xpath('.//span[contains(@class, "post-author")]/a/text()').string()
        author_url = rev.xpath('.//span[contains(@class, "post-author")]/a/@href').string()
        date = rev.xpath('.//span[@class="date-link"]/text()').string()
        category = rev.xpath('.//a[@rel="category"]/text()').string()
        url = rev.xpath('.//h2[@class="is-title post-title"]/a/@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, author=author, author_url=author_url, date=date, category=category, url=url))

    if revs:
        next_page = context['page'] + 1
        session.do(Request(URL, use='curl', options=OPTIONS+str(next_page)+"'", max_age=0, force_charset='utf-8'), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('Test:')[-1].split(':')[-1].replace('GODLIKE', '').strip()
    product.url = context['url']

    if context['category'] in NOCATS:
        product.category = 'Technik'
    else:
        product.category = context['category'].replace('test', '')

    ssid = data.xpath('//article/@id').string()
    if ssid:
        product.ssid = ssid.replace('post-', '')
    else:
        product.ssid = product.url.split('/')[-1]

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = context.get('date')

    author = context.get('author')
    author_url = context.get('author_url')
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@property="ratingValue"]/text()').string()
    if grade_overall and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=6.0))

    pros = data.xpath('(//div[@class="rwp-pros"])[1]//text()').string(multiple=True)
    if pros:
        pros = pros.split(', ')
        for pro in pros:
            pros_ = pro.split('. ')
            for pro_ in pros_:
                _pros = pro_.split(';')
                for _pro in _pros:
                    review.add_property(type='pros', value=_pro.replace('.', '').strip())

    cons = data.xpath('(//div[@class="rwp-cons"])[1]//text()').string(multiple=True)
    if cons:
        cons = cons.split(', ')
        for con in cons:
            cons_ = con.split('. ')
            for con_ in cons_:
                _cons = con_.split(';')
                for _con in _cons:
                    review.add_property(type='cons', value=_con.replace('.', '').strip())

    award = data.xpath('//a[contains(@href, "_toppklass_")]/@href').string()
    if not award:
        award = data.xpath('//img[contains(@src,"_rek_")]/@src').string()
    if award:
        review.add_property(type='awards', value=dict(image_src=award))

    summary = data.xpath('//div[@class="post-content cf entry-content content-spacious"]/h2/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//div[@class="rwp-summary"])[1]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class,"post-content")]/p//text()[not(contains(., "SPECIFIKATIONER"))]').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
