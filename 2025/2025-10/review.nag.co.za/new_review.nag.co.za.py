from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.nag.co.za/wp-json/codetipi-zeen/v1/block?paged=1&type=1&data%5Bid%5D=88038&data%5Bnext%5D=2&data%5Bprev%5D=0&data%5Btarget%5D=0&data%5Bmnp%5D=0&data%5Bpreview%5D=1&data%5Bis110%5D=1&data%5Bcounter%5D=0&data%5Bcounter_class%5D=&data%5Bpost_subtitle%5D=&data%5Bexcerpt_off%5D=1&data%5Bexcerpt_length%5D=12&data%5Bexcerpt_full%5D=0&data%5Bimg_shape%5D=0&data%5Bbyline_off%5D=0&data%5Bfi_off%5D=0&data%5Bppp%5D=15&data%5Bargs%5D%5Bcat%5D=4563&data%5Bargs%5D%5Bposts_per_page%5D=15&data%5Bargs%5D%5Bauthor__in%5D=&data%5Bargs%5D%5Btag__in%5D=&data%5Bargs%5D%5Bpost__in%5D=&data%5Bargs%5D%5Boffset%5D=&data%5Bargs%5D%5Bpost_type%5D=&data%5Bargs%5D%5Btax_query%5D=&data%5Bargs%5D%5Btipi%5D=&data%5Bargs%5D%5Btrending%5D=', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    revs_json = simplejson.loads(data.content)
    if not revs_json:
        return

    new_data = data.parse_fragment(revs_json[-1])

    revs = new_data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath("text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_product, dict(context, title=title, url=url))

    if revs and len(revs) >= 15:
        page = context.get('page', 1) + 1
        next_url = "https://www.nag.co.za/wp-json/codetipi-zeen/v1/block?paged=" + str(page) + "&type=1&data[id]=88038&data[next]=" + str(page+1) + "&data[prev]=" + str(page-1) + "&data[target]=0&data[mnp]=0&data[preview]=1&data[is110]=1&data[counter]=0&data[counter_class]=&data[post_subtitle]=&data[excerpt_off]=1&data[excerpt_length]=12&data[excerpt_full]=0&data[img_shape]=0&data[byline_off]=0&data[fi_off]=0&data[ppp]=15&data[args][cat]=4563&data[args][posts_per_page]=15&data[args][tag__in]=&data[args][post__in]=&data[args][offset]=&data[args][post_type]=&data[args][tax_query]=&data[args][tipi]=&data[args][trending]="
        session.queue(Request(next_url, max_age=0), process_frontpage, dict(page=page))


def process_product(data, context, session):
    product = Product()
    product.name = context['title'].split(' Review – ')[0].replace(' (re-)review', '').replace(' (semi-)review', '').replace(' mega-climax-review', '').replace(' preview', '').replace(' review', '').replace('Review: ', '').replace(' Review', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = "Tech"
    product.manufacturer = data.xpath('//div[div[contains(text(), "DEVELOPER")]]/div[not(contains(., "DEVELOPER"))]/text()').string(multiple=True)

    product.url = data.xpath('//div[div[contains(., "Where to buy")]]/div/a[contains(@href, "https://www.amazon.co.za")]/@href').string()
    if not product.url:
        product.url = context['url']

    platforms = data.xpath('//div[div[contains(text(), "PLATFORMS")]]/div[not(contains(., "PLATFORMS"))]/text()').string()
    if platforms:
        product.category = 'Games|' + platforms.replace('; ', '/').replace(', ', '/').replace(' | ', '/').replace(' \\ ', '/').replace(' (PC and Switch versions coming later)', '').replace(' (Steam)', '')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//span[@class='byline-part author']/a/text()").string()
    author_url = data.xpath("//span[@class='byline-part author']/a/@href").string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath("//div[@class='score']/text()").string()
    if not grade_overall:
        grade_overall = data.xpath("//span[@class='su-dropcap su-dropcap-style-default']/text()").string()

    if grade_overall and grade_overall.isdigit():
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    pros = data.xpath("//div[@class='lets-review-block__pros']/div[@class='lets-review-block__procon lets-review-block__pro']")
    if not pros:
        pros = data.xpath("//div[contains(., 'Plus')]/div[@class='su-box-content su-u-clearfix su-u-trim']/ul/li")

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–…')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath("//div[@class='lets-review-block__cons']/div[@class='lets-review-block__procon lets-review-block__con']")
    if not cons:
        cons = data.xpath("//div[contains(., 'Minus')]/div[@class='su-box-content su-u-clearfix su-u-trim']/ul/li")

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–…')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath("//div[@class='lets-review-block__conclusion']//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//body/h4//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[@class='entry-content-wrap clearfix']/div/h4//text()").string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        if grade_overall:
            conclusion = conclusion.replace(grade_overall, '').strip()

        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath("//div[@class='entry-content-wrap clearfix']/div/p//text()").string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
