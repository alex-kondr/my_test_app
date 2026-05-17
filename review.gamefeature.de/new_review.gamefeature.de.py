from agent import *
from models.products import *
import simplejson


def run(context, session):
    options = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0' -H 'Accept: */*' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'accept-profile: public' -H 'apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhia290YWd5Y21uaXFhZHZ2cXN0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjcyNDcwNDEsImV4cCI6MjA4MjgyMzA0MX0.cQljzJSctZLUZM4QfGX00mu5-VWwYbn08vpXixeVkaM' -H 'authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhia290YWd5Y21uaXFhZHZ2cXN0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjcyNDcwNDEsImV4cCI6MjA4MjgyMzA0MX0.cQljzJSctZLUZM4QfGX00mu5-VWwYbn08vpXixeVkaM' -H 'x-client-info: supabase-js-web/2.105.4' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: cross-site'"""
    session.queue(Request('https://hbkotagycmniqadvvqst.supabase.co/rest/v1/episode_overrides?select=*', use='curl', force_charset='utf-8', options=options, max_age=0), process_revlist, dict())


def process_revlist(data, context, session):

    try:
        revs_json = simplejson.loads(data.content)
    except:
        return

    for rev in revs_json:
        product = Product()
        product.name = rev.get('episode_title').replace(' Test', '').replace('.Test', '.').strip()
        product.url = 'https://gamefeature.de/episode/' + rev.get('episode_title').replace('.', '').replace(',', '').replace(' ', '-').lower()
        product.ssid = rev.get('id')
        product.category = 'Games|' + '/'.join([cat.get('platform') for cat in rev.get('kauflinks', [])])

        review = Review()
        review.type = 'pro'
        review.title = rev.get('episode_title')
        review.url = product.url
        review.ssid = product.ssid

        date = rev.get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('hosts')
        if author:
            review.authors.append(Person(name=author[0], ssid=author[0]))

        grade_overall = rev.get('rating')
        if grade_overall and float(grade_overall):
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

        pros = rev.get('pro_points', [])
        for pro in pros:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

        cons = rev.get('contra_points', [])
        for con in cons:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

        excerpt = rev.get('beschreibung')
        if excerpt:
            excerpt = excerpt.replace('\n', '').replace('\t', '').strip()

            if ' Fazit: ' in excerpt:
                excerpt, conclusion = excerpt.split(' Fazit: ')
                review.add_property(type='conclusion', value=conclusion)

            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

                session.emit(product)

# load all revs
