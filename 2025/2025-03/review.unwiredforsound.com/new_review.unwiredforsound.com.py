from agent import *
from models.products import *
import simplejson


XCAT = ["Articles"]


def run(context, session):
    session.queue(Request('https://unwiredforsound.com/', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@class="menu"]//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h3[@class="title"]/a')
    if not revs:
        new_data = simplejson.loads(data.content.replace("{}\r\n", ''))[1]
        new_data = data.parse_fragment(new_data)
        revs = new_data.xpath('//h3[@class="title"]/a')

    if not revs:
        return

    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    cat_id = context.get('cat_id', data.xpath('//a[contains(., "Load more")]/@data-id').string())
    page = context.get('page', 1) + 1
    next_url = 'https://unwiredforsound.com/wp-json/codetipi-zeen/v1/block?paged={page}&type=1&data%5Bid%5D={cat_id}&data%5Bnext%5D={next_page}&data%5Bprev%5D=1&data%5Btarget%5D=0&data%5Bmnp%5D=0&data%5Bpreview%5D=1&data%5Bis110%5D=1&data%5Bcounter%5D=0&data%5Bcounter_class%5D=&data%5Bpost_subtitle%5D=&data%5Bexcerpt_off%5D=0&data%5Bexcerpt_length%5D=12&data%5Bexcerpt_full%5D=0&data%5Bimg_shape%5D=0&data%5Bbyline_off%5D=0&data%5Bfi_off%5D=0&data%5Bppp%5D=8&data%5Bargs%5D%5Bcat%5D=33&data%5Bargs%5D%5Bposts_per_page%5D=8&data%5Bargs%5D%5Bauthor__in%5D=&data%5Bargs%5D%5Btag__in%5D=&data%5Bargs%5D%5Bpost__in%5D=&data%5Bargs%5D%5Boffset%5D=&data%5Bargs%5D%5Bpost_type%5D=&data%5Bargs%5D%5Btax_query%5D=&data%5Bargs%5D%5Btipi%5D=&data%5Bargs%5D%5Btrending%5D='.format(page=page, next_page=page+1, cat_id=cat_id)
    if cat_id:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict(context, cat_id=cat_id, page=page))


def process_review(data, context, session):
    revs = data.xpath('//div[contains(@class, "pc-row")]')
    if not revs:
        revs = data.xpath('//div[contains(@class, "block__proscons")]')

    if revs and len(revs) > 1:
        process_reviews(data, context, session)
        return

    product = Product()
    product.name = context['title'].split(': ')[0].replace('review', '').strip()
    product.ssid = context['url'].split('/')[-1].replace('-review', '')
    product.category = context['cat']

    product.url = data.xpath('//a[contains(@class, "aff-button")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="author"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="score"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[@data-score]')
    for grade in grades:
        grade_val = grade.xpath('@data-score').string()
        grade_name = grade.xpath('div[contains(@class, "title")]/text()').string()
        if grade_val and grade_val.isdigit() and grade_name:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))

    pros = data.xpath('//div[contains(@class, "pros")]/div[contains(@class, "procon")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "cons")]/div[contains(@class, "procon")]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//p[contains(@class, "subtitle")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@class, "conclusion")]/text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(.//em)]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    revs = data.xpath('//h3[contains(@class, "block-heading") and a]')
    if not revs:
        revs = data.xpath('//h2[contains(@class, "block-heading") and regexp:test(., "\d+\.")]')

    for i, rev in enumerate(revs, start=1):
        product = Product()
        product.name = rev.xpath('.//text()').string()
        product.ssid = product.name.lower().replace(' ', '-')
        product.category = context['cat']

        product.url = rev.xpath('following-sibling::div[contains(@class, "review")][count(preceding-sibling::h2[contains(@class, "block-heading") and regexp:test(., "\d+\.")])={}]//a[contains(@class, "aff-button")]/@href'.format(i)).string()
        if not product.url:
            product.url = rev.xpath('following-sibling::a[contains(@rel, "sponsored")][count(preceding-sibling::h3[contains(@class, "block-heading") and a])={}]/@href'.format(i)).string()
        if not product.url:
            product.url = context['url']

        review = Review()
        review.type = 'pro'
        review.title = product.name
        review.url = context['url']
        review.ssid = product.ssid

        date = data.xpath('//meta[@property="article:published_time"]/@content').string()
        if date:
            review.date = date.split('T')[0]

        author = data.xpath('//meta[@name="author"]/@content').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        pros = rev.xpath('following-sibling::div[contains(@class, "review")][count(preceding-sibling::h2[contains(@class, "block-heading") and regexp:test(., "\d+\.")])={}]//div[contains(@class, "block__pros")]/div[contains(@class, "procon")]'.format(i))
        if not pros:
            pros = rev.xpath('following-sibling::div[contains(@class, "pc")][count(preceding-sibling::h3[contains(@class, "block-heading") and a])={}]//div[contains(@class, "pros")]//li'.format(i))

        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            review.add_property(type='pros', value=pro)

        cons = rev.xpath('following-sibling::div[contains(@class, "review")][count(preceding-sibling::h2[contains(@class, "block-heading") and regexp:test(., "\d+\.")])={}]//div[contains(@class, "block__cons")]/div[contains(@class, "procon")]'.format(i))
        if not cons:
            cons = rev.xpath('following-sibling::div[contains(@class, "pc")][count(preceding-sibling::h3[contains(@class, "block-heading") and a])={}]//div[contains(@class, "cons")]//li'.format(i))

        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            review.add_property(type='cons', value=con)

        summary = data.xpath('//p[contains(@class, "subtitle")]//text()').string(multiple=True)
        if summary:
            review.add_property(type='summary', value=summary)

        excerpt = rev.xpath('following-sibling::p[count(preceding-sibling::h3[contains(@class, "block-heading") and a])={}][not(contains(., "Features:"))]//text()'.format(i)).string(multiple=True)
        if not excerpt:
            excerpt = rev.xpath('following-sibling::p[count(preceding-sibling::h2[contains(@class, "block-heading") and regexp:test(., "\d+\.")])={}][not(contains(., "Features:"))]//text()'.format(i)).string(multiple=True)

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
