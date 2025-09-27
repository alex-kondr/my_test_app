from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://musicplayers.com/category/reviews/", use='curl'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@id="main-menu"]/ul/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()
        cats1 = cat.xpath('.//ul[contains(@class, "bk-sub-menu")]/li[a[contains(., " Reviews")]]/ul/li')

        if cats1:
            for cat1 in cats1:
                name1 = cat1.xpath('a/text()').string()
                if name1:
                    name1 = name1.replace('Reviews', '').strip()
                    name1 = '' if name1 in name else name1

                cats2 = cat1.xpath('ul/li/a')
                if cats2:
                    for cat2 in cats2:
                        name2 = cat2.xpath('text()').string()
                        if name2:
                            name2 = name2.replace('Reviews', '').strip()

                        url = cat2.xpath('@href').string()
                        session.queue(Request(url, use='curl'), process_revlist, dict(cat=name+'|'+name1+'|'+name2))

                else:
                    url = cat1.xpath('a/@href').string()
                    session.queue(Request(url, use='curl'), process_revlist, dict(cat=name+'|'+name1))
        else:
            url = cat.xpath('.//ul[contains(@class, "bk-sub-menu")]/li[a[contains(., " Reviews")]]/a/@href').string()
            session.queue(Request(url, use='curl'), process_revlist, dict(cat=name))

def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="post-c-wrap"]')
    if not revs:
        return  # Empty page

    for rev in revs:
        title = rev.xpath('.//h4[@class="title"]/a/text()').string()
        url = rev.xpath('.//h4[@class="title"]/a/@href').string()

        cats = rev.xpath('.//div[@class="post-category"]/a//text()').strings()
        if 'Reviews' in cats:
            session.queue(Request(url, use='curl'), process_review, dict(context, title=title, url=url))

    cat_id = context.get('cat_id')
    if not cat_id:
        cat_id = data.xpath('//script[contains(., "category__in")]/text()').string()
        if cat_id:
            cat_id = cat_id.split('"category__in":"')[-1].split('"')[0]

    if cat_id:
        next_url = "https://musicplayers.com/wp-admin/admin-ajax.php"
        offset = context.get('offset', 12) + 4
        options = """-X POST --data-raw 'action=blog_load&post_offset={offset}&args%5Bcategory__in%5D={cat_id}'""".format(offset=offset, cat_id=cat_id)
        session.do(Request(next_url, use="curl", options=options, force_charset='utf-8', max_age=0), process_revlist, dict(context, cat_id=cat_id, offset=offset))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('Album Review:')[-1].split('Album Review -')[-1].split('ALBUM REVIEW:')[-1].split('DVD Review:')[-1].split(':')[0].split(' - ')[0].strip()
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2].replace('%ef%bb%bf', '')
    product.category = context['cat'].replace('||', "|").strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title'].replace(u'\uFEFF', '').strip()
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]').first()
    if author:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()
        author_ssid = author_url.split('/')[-2].replace('%ef%bb%bf', '')
        review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))

    grade_overall = data.xpath('//tbody/tr[regexp:test(., "overall", "i")]//img[not(regexp:test(@src, "WIHO", "i"))]/@src').string() or data.xpath('//tbody/tr[regexp:test(., "overall", "i")]/td[last()]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.lower().replace('overall', '').replace('rating', '').split(' out of ')[0].split('stars')[0].split('=')[-1].split('Stars,')[0].split(',')[0].replace(':', '').split('/')[-1].split('.')[0].replace("finalstar-", "").replace("_stars", "").replace("_", "").strip('( )')
        if float(grade_overall) > 10.0:
            grade_overall = float(grade_overall) / 10

        review.grades.append(Grade(type='overall', value=float(grade_overall), best=4.0))

    grade_names = []
    grades = data.xpath('//tbody/tr[.//img]')
    for grade in grades:
        grade_name = grade.xpath('td[1][not(regexp:test(., "overall", "i"))]/*[self::span or self::strong or self::em/strong]//text()').string()
        grade_value = grade.xpath('.//img/@src').string()
        if grade_name and grade_name not in grade_names and grade_value:
            grade_names.append(grade_name)
            grade_value = grade_value.split('/')[-1].split('.')[0].replace("finalstar-", "").replace("_stars", "").replace("_", "").replace("-", "")
            if float(grade_value) > 10.0:
                grade_value = float(grade_value) / 10

            review.grades.append(Grade(name=grade_name.replace(':', ''), value=float(grade_value), best=4.0))

    conclusion = data.xpath('//div[@class="article-content clearfix"]/p[regexp:test(., "The Verdict:", "i")]/following-sibling::p[not(contains(., "www.")) and not(regexp:test(., "Overall Rating", "i")) and not (regexp:test(., "Documentation and Product Support", "i")) and not(regexp:test(., "Contact Information", "i"))]/text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="entrytext" or contains(@class, "article-content") or @itemprop="articleBody"]/p[not(regexp:test(., "Verdict:", "i"))][not(preceding-sibling::p[regexp:test(., "Verdict", "i")])][not(contains(., "www.")) and not(regexp:test(., "Overall Rating", "i")) and not (regexp:test(., "Documentation and Product Support", "i")) and not(regexp:test(., "Contact Information", "i"))]/text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entrytext" or contains(@class, "article-content") or @itemprop="articleBody"]/h3[contains(text(), "Contact Information")]/preceding-sibling::text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
