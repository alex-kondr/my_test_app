from agent import *
from models.products import *


OPTIONS = """--compressed \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:158.0) Gecko/20100101 Firefox/158.0' \
  -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
  -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' \
  -H 'Accept-Encoding: deflate' \
  -H 'Connection: keep-alive' \
  -H 'Cookie: aws-waf-token=a78c8e4c-3074-43ae-9609-93d92f26592a:EQoAYKVpVk064AAA:Dyj+gNDCwRv9Pbaz44MjY8ztf3aXpx75P6kHBY243BURQGKfHetyMsfd+XXeQwFBO2seEykYhfy1SpPdeI8khfWjYSPHmv9YT4Kn18UGXiNfjHxCVo1FersVn6eYdTTEF/oSjneXT6Pnxj+DbFWJJeWhXrBaGTIQCg1qDEClZCwFSwFc6PL9vWF9R9U9MQaLJIGLxSMSHkL6DxiH/nZx6nsPmYTcgcjZERhFx8+USal1hYIh0yXQBtk7pHfep43igTYiBgib/HGBWcyCCTPyD6S44huIMIqkeiQC; XSRF-TOKEN=eyJpdiI6IjZCQzJSOUJ2OGpxVkJzS3BBZW40ZkE9PSIsInZhbHVlIjoiODBwVDVtb1BHT2oyTEJ4VVNudUpnakViUjVBa2dvdDUvYW9oSjdUalgvelczZkRGdkRNNFA3RkhaS3VFQmlxdGRjWnpDUlR6b09sNncvbmI4YVI4TVROYXAya2lub2p5SUpITlZMa0Qzb1dPYnVzM1hKMi9POUFCVEdlTjZJWFoiLCJtYWMiOiJhYzc4ZjRmYjIwODQzZmQ1MzFmMDljNTVkMDJhMTM1YTQ1ZjkwYWM2OWNmY2U1YmNhZWVlMjUyYmMyNzhkZThjIiwidGFnIjoiIn0%3D; moviefone-session=eyJpdiI6Ilpka0pPVE5QdFFzTTFzL3Q2U2htWHc9PSIsInZhbHVlIjoiWjA3RHJqNHZzbHd3dDRTN3AzN0JHNXZTNFdBWm5UTlQvendLODdoN2pjTlAvNDB2QmRQMVR2SXRDc3k3cFZ5ZmJPK0gyUUdadVh0R1k5YU5wU0V2RjQydHlzRmZ6RmlDUFpvSkEzSlRVNVRGYVNiSnJiQWIrS3NVa1BjcEZEdmEiLCJtYWMiOiI0ODgzMDNkMTkxZjAwN2NkOTUyZWI4MTYyM2RlNDBlZjY5MjZmM2EzZDlkMjNmODY4OTdjMzYxZjZmMjJkN2Y1IiwidGFnIjoiIn0%3D; mf_ad_stack=ione' \
  -H 'Upgrade-Insecure-Requests: 1' \
  -H 'Sec-Fetch-Dest: document' \
  -H 'Sec-Fetch-Mode: navigate' \
  -H 'Sec-Fetch-Site: none' \
  -H 'Priority: u=0, i' \
  -H 'Pragma: no-cache' \
  -H 'Cache-Control: no-cache' \
  -H 'TE: trailers'"""


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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.moviefone.com/movies/reviews/', use='curl', force_charset='utf-8', options=OPTIONS), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//a[contains(@class, "card-link")]/@href')
    for rev in revs:
        url = rev.string()
        session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS), process_review, dict(url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', options=OPTIONS), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    title = data.xpath('//h1[contains(@class, "title")]/text()').string()

    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('movie-review', '').strip(' -')
    product.category = 'Movie'

    product.name = data.xpath('//a[contains(@class, "card-title")]/text()').string()
    if not product.name:
        product.name = title

    genres = data.xpath('//a[contains(@class, "card-genre")]/text()').join('/')
    if genres:
        product.category += '|' + genres

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//a[contains(@class, "date-link")]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@property="article:author"]/@content').string()
    author_url = data.xpath('//div[contains(@class, "article-byline-author")]/a/@href').string()
    if author and author_url and 'moviefone' not in author.lower():
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author and 'moviefone' not in author.lower():
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(span, "Review")]//span[contains(@class, "score-num")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grade = data.xpath('//div[contains(span, "Audience")]//span[contains(@class, "score-num")]/text()').string()
    if grade:
        review.grades.append(Grade(name='Audience', value=float(grade), best=100.0))

    summary = data.xpath('//p[contains(@class, "article")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "final thoughts", "i")]/following-sibling::p[not(regexp:test(., "of 10 stars| out of 100| on Amazon|Buy Tickets:", "i") or preceding::h2[regexp:test(., "What |What’s ")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(., "Bottom line")]]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type="conclusion", value=conclusion.strip(': '))

    excerpt = data.xpath('//h2[regexp:test(., "final thoughts", "i")]/preceding-sibling::p[not((contains(., "Opening") and a) or regexp:test(., "of 10 stars| out of 100| on Amazon|Buy Tickets:", "i"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "article-body")]/p[not((regexp:test(., "Opening|The returning voice cast") and a) or regexp:test(., "of 10 stars| out of 100| on Amazon|Buy Tickets:", "i"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)