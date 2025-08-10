from agent import *
from models.products import *
import simplejson
import re


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
    options = """--compressed -X POST --data-raw 'action=csco_ajax_load_more&page=1&posts_per_page=6&query_data=%7B%22first_post_count%22%3A6%2C%22infinite_load%22%3Afalse%2C%22query_vars%22%3A%7B%22category_name%22%3A%22reviews-labs%22%2C%22error%22%3A%22%22%2C%22m%22%3A%22%22%2C%22p%22%3A0%2C%22post_parent%22%3A%22%22%2C%22subpost%22%3A%22%22%2C%22subpost_id%22%3A%22%22%2C%22attachment%22%3A%22%22%2C%22attachment_id%22%3A0%2C%22name%22%3A%22%22%2C%22pagename%22%3A%22%22%2C%22page_id%22%3A0%2C%22second%22%3A%22%22%2C%22minute%22%3A%22%22%2C%22hour%22%3A%22%22%2C%22day%22%3A0%2C%22monthnum%22%3A0%2C%22year%22%3A0%2C%22w%22%3A0%2C%22tag%22%3A%22%22%2C%22cat%22%3A63%2C%22tag_id%22%3A%22%22%2C%22author%22%3A%22%22%2C%22author_name%22%3A%22%22%2C%22feed%22%3A%22%22%2C%22tb%22%3A%22%22%2C%22paged%22%3A0%2C%22meta_key%22%3A%22%22%2C%22meta_value%22%3A%22%22%2C%22preview%22%3A%22%22%2C%22s%22%3A%22%22%2C%22sentence%22%3A%22%22%2C%22title%22%3A%22%22%2C%22fields%22%3A%22all%22%2C%22menu_order%22%3A%22%22%2C%22embed%22%3A%22%22%2C%22category__in%22%3A%5B%5D%2C%22category__not_in%22%3A%5B%5D%2C%22category__and%22%3A%5B%5D%2C%22post__in%22%3A%5B%5D%2C%22post__not_in%22%3A%5B%5D%2C%22post_name__in%22%3A%5B%5D%2C%22tag__in%22%3A%5B%5D%2C%22tag__not_in%22%3A%5B%5D%2C%22tag__and%22%3A%5B%5D%2C%22tag_slug__in%22%3A%5B%5D%2C%22tag_slug__and%22%3A%5B%5D%2C%22post_parent__in%22%3A%5B%5D%2C%22post_parent__not_in%22%3A%5B%5D%2C%22author__in%22%3A%5B%5D%2C%22author__not_in%22%3A%5B%5D%2C%22search_columns%22%3A%5B%5D%2C%22ignore_sticky_posts%22%3Afalse%2C%22suppress_filters%22%3Afalse%2C%22cache_results%22%3Atrue%2C%22update_post_term_cache%22%3Atrue%2C%22update_menu_item_cache%22%3Afalse%2C%22lazy_load_term_meta%22%3Atrue%2C%22update_post_meta_cache%22%3Atrue%2C%22post_type%22%3A%22%22%2C%22posts_per_page%22%3A6%2C%22nopaging%22%3Afalse%2C%22comments_per_page%22%3A%2250%22%2C%22no_found_rows%22%3Afalse%2C%22order%22%3A%22DESC%22%7D%2C%22in_the_loop%22%3Afalse%2C%22is_single%22%3Afalse%2C%22is_page%22%3Afalse%2C%22is_archive%22%3Atrue%2C%22is_author%22%3Afalse%2C%22is_category%22%3Atrue%2C%22is_tag%22%3Afalse%2C%22is_tax%22%3Afalse%2C%22is_home%22%3Afalse%2C%22is_singular%22%3Afalse%7D&attributes=undefined&options=%7B%22location%22%3A%22archive%22%2C%22meta%22%3A%22archive_post_meta%22%2C%22layout%22%3A%22grid%22%2C%22columns%22%3A3%2C%22image_orientation%22%3A%22landscape%22%2C%22image_size%22%3A%22csco-thumbnail%22%2C%22summary_type%22%3A%22summary%22%2C%22excerpt%22%3Afalse%7D&_ajax_nonce=f7f98f1587'"""
    session.do(Request('https://techcetera.co/wp-json/csco/v1/more-posts', use='curl', force_charset='utf-8', options=options, max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    data_json = simplejson.loads(data.content)
    if not data_json:
        return

    new_data = data.parse_fragment(data_json.get('data', {}).get('content'))

    revs = new_data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('.//text()').string(multiple=True)
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    if revs:
        next_page = context.get('page', 1) + 1
        options = """--compressed -X POST --data-raw 'action=csco_ajax_load_more&page=""" + str(next_page) + """&posts_per_page=6&query_data=%7B%22first_post_count%22%3A6%2C%22infinite_load%22%3Afalse%2C%22query_vars%22%3A%7B%22category_name%22%3A%22reviews-labs%22%2C%22error%22%3A%22%22%2C%22m%22%3A%22%22%2C%22p%22%3A0%2C%22post_parent%22%3A%22%22%2C%22subpost%22%3A%22%22%2C%22subpost_id%22%3A%22%22%2C%22attachment%22%3A%22%22%2C%22attachment_id%22%3A0%2C%22name%22%3A%22%22%2C%22pagename%22%3A%22%22%2C%22page_id%22%3A0%2C%22second%22%3A%22%22%2C%22minute%22%3A%22%22%2C%22hour%22%3A%22%22%2C%22day%22%3A0%2C%22monthnum%22%3A0%2C%22year%22%3A0%2C%22w%22%3A0%2C%22tag%22%3A%22%22%2C%22cat%22%3A63%2C%22tag_id%22%3A%22%22%2C%22author%22%3A%22%22%2C%22author_name%22%3A%22%22%2C%22feed%22%3A%22%22%2C%22tb%22%3A%22%22%2C%22paged%22%3A0%2C%22meta_key%22%3A%22%22%2C%22meta_value%22%3A%22%22%2C%22preview%22%3A%22%22%2C%22s%22%3A%22%22%2C%22sentence%22%3A%22%22%2C%22title%22%3A%22%22%2C%22fields%22%3A%22all%22%2C%22menu_order%22%3A%22%22%2C%22embed%22%3A%22%22%2C%22category__in%22%3A%5B%5D%2C%22category__not_in%22%3A%5B%5D%2C%22category__and%22%3A%5B%5D%2C%22post__in%22%3A%5B%5D%2C%22post__not_in%22%3A%5B%5D%2C%22post_name__in%22%3A%5B%5D%2C%22tag__in%22%3A%5B%5D%2C%22tag__not_in%22%3A%5B%5D%2C%22tag__and%22%3A%5B%5D%2C%22tag_slug__in%22%3A%5B%5D%2C%22tag_slug__and%22%3A%5B%5D%2C%22post_parent__in%22%3A%5B%5D%2C%22post_parent__not_in%22%3A%5B%5D%2C%22author__in%22%3A%5B%5D%2C%22author__not_in%22%3A%5B%5D%2C%22search_columns%22%3A%5B%5D%2C%22ignore_sticky_posts%22%3Afalse%2C%22suppress_filters%22%3Afalse%2C%22cache_results%22%3Atrue%2C%22update_post_term_cache%22%3Atrue%2C%22update_menu_item_cache%22%3Afalse%2C%22lazy_load_term_meta%22%3Atrue%2C%22update_post_meta_cache%22%3Atrue%2C%22post_type%22%3A%22%22%2C%22posts_per_page%22%3A6%2C%22nopaging%22%3Afalse%2C%22comments_per_page%22%3A%2250%22%2C%22no_found_rows%22%3Afalse%2C%22order%22%3A%22DESC%22%7D%2C%22in_the_loop%22%3Afalse%2C%22is_single%22%3Afalse%2C%22is_page%22%3Afalse%2C%22is_archive%22%3Atrue%2C%22is_author%22%3Afalse%2C%22is_category%22%3Atrue%2C%22is_tag%22%3Afalse%2C%22is_tax%22%3Afalse%2C%22is_home%22%3Afalse%2C%22is_singular%22%3Afalse%7D&attributes=undefined&options=%7B%22location%22%3A%22archive%22%2C%22meta%22%3A%22archive_post_meta%22%2C%22layout%22%3A%22grid%22%2C%22columns%22%3A3%2C%22image_orientation%22%3A%22landscape%22%2C%22image_size%22%3A%22csco-thumbnail%22%2C%22summary_type%22%3A%22summary%22%2C%22excerpt%22%3Afalse%7D&_ajax_nonce=f7f98f1587'"""
        session.do(Request('https://techcetera.co/wp-json/csco/v1/more-posts', use='curl', force_charset='utf-8', options=options, max_age=0), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('Los Primeros Reviews del ', '').replace('Retro Reseña – ', '').replace('Retro Reseña la', '').replace('Retro Reseña: ', '').replace('Reseña: el ', '').replace('Review del ', '').replace(' (Review: 94Fifty)', '').replace('Review: ', '').replace(': Review', '').replace(' [Review]', '').replace(' [Hands On]', '').replace(' (Review)', '').replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = 'Tecnología'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "meta-author")]//span[contains(@class, "meta-author-name")]/text()').string()
    author_url = data.xpath('//div[contains(@class, "meta-author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('(//h3[contains(., "Ventajas de|Lo bueno acerca de")]/following-sibling::*)[1]//li[not(@style)]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(., "Oportunidades de")]/following-sibling::*)[1]//li[not(@style)]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "entry__subtitle")]//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(summary).strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[regexp:test(., "\¿Entonces\?|\¿Actualizar o no\?|\¿Qué pensar acerca de")]/following-sibling::p[not(regexp:test(., "twitter", "i") or .//a[contains(@href, "twitter")])]//text()').string(multiple=True)
    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[regexp:test(., "\¿Entonces\?|\¿Actualizar o no\?|\¿Qué pensar acerca de")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]/p[not(regexp:test(., "twitter", "i") or .//a[contains(@href, "twitter")])]//text()').string(multiple=True)

    if excerpt:
        excerpt = remove_emoji(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
