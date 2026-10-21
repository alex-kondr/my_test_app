#!/usr/bin/python
# -*- coding: utf-8 -*-
import HTMLParser
import httplib
httplib._MAXHEADERS = 200

# .\koyeb.exe service logs vocational-ruth/vpn-service --tail -t runtime

def Request(url):
    options = """--compressed \
    -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:158.0) Gecko/20100101 Firefox/158.0' \
    -H 'Accept: */*' \
    -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' \
    -H 'Accept-Encoding: gzip, deflate, br, zstd' \
    -H 'Referer: https://www.dolce-gusto.es/capsulas' \
    -H 'X-NewRelic-ID: UAMCV1FSGwYAUlRUBQEDXg==' \
    -H 'newrelic: eyJ2IjpbMCwxXSwiZCI6eyJ0eSI6IkJyb3dzZXIiLCJhYyI6IjQ1NTY3MSIsImFwIjoiNTA3NDMxNjk3IiwiaWQiOiJhODIwMmQ1NmYxY2NjODRkIiwidHIiOiI0NTY5M2ViM2Q3YWQ5OGZjNzg4Nzk4NGQ1N2QyNzkyNiIsInRpIjoxNzkyNTAwNzI2NjEwLCJ0ayI6IjE3MDIyMjYifX0=' \
    -H 'traceparent: 00-45693eb3d7ad98fc7887984d57d27926-a8202d56f1ccc84d-01' \
    -H 'tracestate: 1702226@nr=0-1-455671-507431697-a8202d56f1ccc84d----1792500726610' \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -H 'X-Requested-With: XMLHttpRequest' \
    -H 'Connection: keep-alive' \
    -H 'Cookie: _abck=893830BFBB4ABEA1E154E99825F05529~0~YAAQFQRTaJ5xxi6hAQAAONlRWRC0OpJSC0D7COSlwW6/0SQ0O2Sb5hMwkPRRbouhzbSSrn78Ij13RrMhm1kphzlzbBMw4ix9IxAMr2aKxSEFE772hXGmOtI7LJYqw5LXC/gv5U7DAOv5rZnyMPsTJwNWj7UqQJrgJvz69kr2H1FbSUO/55lyIH2oTps+hA/nevS/scK/qG/EnzOmm2LDwbrRLtG0DQZZsd5NGHocdZBPATbJosx+uadvbQYd0gkQKwDkEkfHmwZQfJEcydDNCvSRI6THhIxt9tWQup7M2IuNKDLNAyBEiMJ+YJqZmDiT/Eo5KOgRi+Mt+cF6nRILsjT7KjrPIjh++k3F8C4rEH56Mt/lbXGmB398euqZRNABlDuzfhvEAI12ZhcAXLgxT8cprM59rMAVeUWgaePTQxIGe0dB6V5ms/4khJecpr7TiGPFZO2TN40SUjt+XoLaT2UkdChNugd6XdGgwGE4PHeeS+UnUTpWoLNo5wgBTnkPTo+iAEopflQNulbBXmnU9NzD3Xonrli1XgCIYyJJbVlBDoPn50WFL/2GjGfL1T46nG8j+GFIh99+QBgQcGCgm40TSIi/vP648qlodgVXmYKlU2vx/eCmDkyUuX+vUiAaQTY23hVPmJH7iwYS+Gn7i6GHEyT8urkN9hiOi4YdgfWT~-1~-1~1792503496~AAQAAAAG%2f%2f%2f%2f%2fzis6JftTUKK%2fGHLVKfK0P%2foWERjBVAkcBYtu9FQuJbHjHEvTymSxBgvTsKgFvt%2fmnZjAemCmare2rlLQYGnmoMomnyImW3xU%2fFk~-1; bm_s=YAAQjikSAlkqaS+hAQAA1YBeWQZJ0VgNoiyfMgNN/ZFMs13TuIv2GBndrWIndXRGWZVmKdtjJi+adROvU97Vu12GEVpKe8jEihVkWXUH+aVy6Tvy36/XNK35dmBAVnouPn4e4/eSjSazYOMX8HP3WQyoExN+o47p0Z88mnueEAvQROehbXHANThU0w27O9NjrQ0gAsTYZQ7a/CKFJv+ZNiwFQQ9nq1ZIkyOwYFpvNNSDoL8YiewXlzdSCDnThO1X2HZrgoaJ1DB8We0KeuB/zZUGN7IgZ/fkL6VHd7QhWxOn9wAA91/zgOLJdgi0IZLXnmuhN4xO6p8SO5E/AsP17lUgiiHK9Hq4OgcqSmUMjXSn8K+sxb+BsEc+n6xLUEfVyd19eRI76Ir5Ri45JOA6r70dyspknGf8x58xM6CV197OvS/yiAflXPb9gA8oZzFulkjS1vebcoh0sA/pqsTA8pkucocH6m1t76njRlQHd++/9qRYW6B7nZQIVnaNzAgcBiUzvR8RzRoWK70MoiLvOM4ieqXJbCau0L8lfmOUor9t/zhjwbu8S/123BJhTdYnEUUTaFwQNyM4TU9/GMfXZOr2j1QswNm8MnZDWNRaJKy55L8e6zey7afjx0JtL47oWWBang4wOzJxdMCko8GoP1Mt+c9I1o9ae+AgezslDQKEqM5NNQshJ2CDkIVwfI7tHfLUX1owZiuc72wQ3aXwvRkbgIjhsLk4OxKGGA34DZvqfTd1d4kxjqkVnNhK7/g8AbxsffKelmp+md1YNB1Wu45R79uSyYaoKw6OuILJ4cclnp0uP+3RHHvwaXzuVSqwkJfzZ4TZQSIbGFAF0NwGmDsY1TU2tIrwrZvMkE64asxnsyKyoYIkrzHBPXKbbEJB88sUvKBcEAeH8dremm/t71iwlR/6O21/5xY73KdHVgTBNpha3XCbIM2MR2OYqoAaVVBn25Sm2v5sFY4EDpCYdTydGCbLCaKs510K7gb3OL2nAKC6UeQf+nGYjTiKzl9tPtn0gaisM4cuSwJURl3F57B8pvnl0zzkCVp9NlSCr2Q3piKbfSulNc8WK1v+TYFncj2k0/eZsVJ6Nvl2SimUmvBH2OWahHOegvI=; bm_so=E403F828068841231974884BB5619D4B27460D0E44544F095822B839111DB92C~YAAQjikSAuApaS+hAQAAom9eWQkwITh0862OMBm2t3xuQBh8CHyWp7MNVPYxDvMli5uOhZfnh+BVJVUmQHHsx8TF4y61sMqDWx38bNdN1kLTSES8srVRb9bkSdJZaFBKivcwwuG5EoE8Bn5KGeRcqGejHSLUvdm6ljJvoXY1bv/nsMkdCK5vFjv20bbMghNRjBPyhZdhBhzN1iCJwQdaS51smABsxqxLguvAtZnN4go1DyPX/DI+sAZ4JhafDHbJ7CyHu+TBDC4fvxdRqBL029L14h63wtESBkJ39MFLVw9iwGekYVBrt0KAPsWKk0BtHanFu8QblOghQN97YRf3KLl1B9dpxKlGDdL5d0XZO0ZCz1Kk4+PQUFookgTMWgY++dVZCmgVq4LpI/9FhktD8BN5meJsjBWpyvX9RNOW2avpxMnnZBho4c/88bgPJspV7FciubX/WwuuaSUooabiYzL0pWoGqFYb/w6BgjMZ~3; bm_sz=68F02CB3234971F4FD00446C8764EB28~YAAQjikSAlsqaS+hAQAA1YBeWQGq5uiaDgqoFbtbku+J+PVJTjX5UJC2Coh3bjcvB38T5lYis6iwqFB9S6H9Y0DakydWryyCMp3T4u4VUlQBT2B7fywvU+WP8PYPs+EPUFcgy0CQ41Am+rNx+MMqXgys1D8H76WxdmXysRwdMxT0alyX1C5A2mS4BCoeJl6BFf+fzMHJBeS1TNrGAUDFKkLAV31jES1yAmz9WdHHrrKLwzowmv+5bE1kjetYdO/0kQXLuMmhVp0QpzcWKUGvrWRZ1VzRG5v3c7l0alWPZrsO+PfZ47ojdPkygveT2p/p7vtyHx+fuKpOawFvHVchJ7ExePRFvMGQ/CEDFFVgfIwubSrAXt510HWutbr8PgPn0cau5on+TxypIDPGn8KHdvoXCzHoG/0N9m5A~4604982~4277301; PHPSESSID=2082e52097256e84f6feb0621ede8bac; X-Magento-Vary=2371e23c707b12a2a9024878a69a7e14a059455179df1ec744837d97fe5a070f; ak_bmsc=DDD4BC86AC0F946F293CF9F4041A78A7~000000000000000000000000000000~YAAQFQRTaGFtxi6hAQAA281RWQGhaX0BljejA5lH/sAqY1lfD98J6EoRCORvfmyYeh4MVEAT1mzTdMPFLpqJBeAy4QTvuiiZuh0M5OUg5vemFXSD7qI7sPZABTJE6yr6RxCfql74G+0SRmepjRpc8hEhBmMv+EKFXPH5Sgl3zFc7jaP0ENTQdKxLEOfrJX4hTwPSA+0UuW0etlJvEK7jv6ntlbQf9AXZwULpib5e0KFFwS48qSaPzP2K8IGu5xQNSuE9EDS5qjhXQJVYMR+rtKYpzu+W+BUZzGfc+u8JYI3Lq/6khWPu11+ut85FCT9Y32uxqdIyWM0JvJrAW1TWNnObK6hrU5EwaALneuIlLw6NXF8dGkJUw4EJGp8sjT9kEgMGs0PATS3dTyyxRnvk; last_visited_store=ndg_es; mage-cache-sessid=true; bm_lso=E403F828068841231974884BB5619D4B27460D0E44544F095822B839111DB92C~YAAQjikSAuApaS+hAQAAom9eWQkwITh0862OMBm2t3xuQBh8CHyWp7MNVPYxDvMli5uOhZfnh+BVJVUmQHHsx8TF4y61sMqDWx38bNdN1kLTSES8srVRb9bkSdJZaFBKivcwwuG5EoE8Bn5KGeRcqGejHSLUvdm6ljJvoXY1bv/nsMkdCK5vFjv20bbMghNRjBPyhZdhBhzN1iCJwQdaS51smABsxqxLguvAtZnN4go1DyPX/DI+sAZ4JhafDHbJ7CyHu+TBDC4fvxdRqBL029L14h63wtESBkJ39MFLVw9iwGekYVBrt0KAPsWKk0BtHanFu8QblOghQN97YRf3KLl1B9dpxKlGDdL5d0XZO0ZCz1Kk4+PQUFookgTMWgY++dVZCmgVq4LpI/9FhktD8BN5meJsjBWpyvX9RNOW2avpxMnnZBho4c/88bgPJspV7FciubX/WwuuaSUooabiYzL0pWoGqFYb/w6BgjMZ~3~1792500721538; form_key=DjFliYfxffR46kWV; bm_sv=4215D9E989BD61FAEF3CE91949643400~YAAQjikSAloqaS+hAQAA1YBeWQG5tm6Tmvj2nJvPc70Ef9tyYH2G+mz5HtcxcDmrakD//OHGkgIaikGcHTOfcz0uaElpLrXA3ZjSE4KLmP5YDThsh5q52IzEVgJ39prj1A562r0bznS3cYfTGORDU+xahi0W9+G2Z2ymzT9fV/XlVbsJkiCI6ugnGsN/sIigq/MHTg04nf2vHNkNknAQA67K+nSp93c4iv4IIG8PYnT6GbArswu1ZzF210e/gdhBgfZuAw==~1; private_content_version=35f5af87d6de5a9560a0610c45bde90a; bm_mi=760A51C9FFDD78E1F023CCFE3C9024E8~YAAQjikSAlgqaS+hAQAA1YBeWQEEXLLj3WYdaKqekOYGApwS8zU564xUukhbEMxKsdZkPF4HBHMOo4S5vtXEhvUtU3AnLkaoBErNPq/dh34tU90v/n5S9PWxf8P400bN+X+eYnZQg70vHt5LqtgWdbuMHh4tFQWKwpmQZUz1K0PZI9oFbfjEspILaZmkDFpU4IrNQiCNz9Q+LnZXu7Ag+BLVua1B//qfyr21mTRVocgGNnImq19Z0UawD/D3rAczOuu4sheNpSVAzNkyZd9kQaUQR/I2tRfLvdUHQxgyH3m2/I+A+qquFYcxBkFBxEA6EHDqSZJX4cl06w==~1' \
    -H 'Sec-Fetch-Dest: empty' \
    -H 'Sec-Fetch-Mode: cors' \
    -H 'Sec-Fetch-Site: same-origin' \
    -H 'Pragma: no-cache' \
    -H 'Cache-Control: no-cache' \
    -H 'TE: trailers'"""
    r = agent.Request(url, proxies=['rotating-us'], use='curl', force_charset='utf-8', options='-s -L --insecure '+options, max_age=0)
    return r


h = HTMLParser.HTMLParser()
h.unescape()
session.browser.use_new_parser = True
session.sessionbreakers = [SessionBreak(max_requests=10000)]

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

'//h2[contains(., "Fazit")]/preceding-sibling::*'
'//h2[contains(., "Fazit")]/following-sibling::*'
'//div/ancestor::div'

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

# product.name = re.sub(r'[\s]?[P]?review[ed]{0,2}[ -–:]{0,3}', '', re.split(r' [p]?Review[ed]{0,2}[ :-–]{1,3}', context['title'], flags=re.I)[0], flags=re.I).strip()

# multiple JSONs
# decoded HTML with many replaces
# HTML in JSON
# Bypassed authentication, codes in categories
# Problem with HTML in JSON
# problem with JSON and parsing from JavaScript
# data for all processes from json with specific options
# no prod id in data for request to revs, create custom url to get it
# create new function of pagination of review, resolve many exceptions when pagination works incorrectly; resolve problem with Chinese brackets
# problem with HTML
# many exceptions in reviews, adjusting of multirevs and multipages functions
# many exceptions in reviews, problem with api


    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.category = context['product']['category']
    product.manufacturer = context['product'].get('manufacturer')

    mpn = context['product'].get('mpn')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = context['product'].get('ean')
    if ean and str(ean).isdigit() and len(str(ean)) > 10:
        product.add_property(type='id.ean', value=str(ean))