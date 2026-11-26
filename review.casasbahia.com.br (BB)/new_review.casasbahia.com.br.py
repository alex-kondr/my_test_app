#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = [u'Serviços', u'Carnê Digital', u'Gift Card']


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        line = line.replace('<!-- -->', '')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def Request(url):
    options = "--compressed -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'TE: trailers'"
    r = agent.Request(url, use='curl', force_charset='utf-8', proxies=['rotating-eu'], options='-s -L --insecure '+options, max_age=0)
    return r


def RequestProds(cat_id, page):
    url = 'https://api-partner-prd.casasbahia.com.br/api/v3/web/categoria?resultsperpage=20&apikey=casasbahia&filter={cat_id}&page={page}&banner=true&platformtype=1&variantconfiguration=A&multiselection=false&partnerkey=solr&enablepriceslider=false'.format(cat_id=cat_id, page=page)
    options = """-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:161.0) Gecko/20100101 Firefox/161.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: GCB-TRACKING=94.179.72.26; _abck=9B6DF8B4CEB83BF082F4181D52D4F619~0~YAAQz3nMFxUFAwOiAQAAgLwLGBDBfoTP3in9cp47U3mDzEZsQM1J3GLwd+zYYABKgHwA/nQZuR4wbXNQSMBsoVSSdYkbPgHw5tnd5hLGsiOrcrAuiJd3SBnNYMI0Zk4T6lRg7hGK7HiM6jq5+n+xzTzDsrnWuT1CafPkWW/UP34f0k9YFuhazWrLPtiThElHqCxKzwrseTGj+atUHZw5Chkwo16LecuJoUj/S2r7QRMdCt4Jd2SxqM7qEkOD+eAMyXw2pyaUdwoI12zGmmbyF7QNhzbzQ7p/96Kf0dIyuojYir2qS+isbZA8wvQCBA/gWZ0t86WvwPtsoJLxZ52yPMI5tfRKJooFPHiye5dLgJxWBi/dMchBnU9mvpeHI2llilY3BOdGnxNcZYIixQOjS7DovZ+STaXctBE2cMzA6whWls4/HBvA7yUcdYjYvd1QmJpCyNUtIca0VwPKz1DNOHdnG2brYUkklSUsHzYrwPEl5xZM5UxjFRG9cTKvcxpOfng+IbB2zdaX0Qw2wfExv53lJC9VE42v2SvE84O8ZON141gC1XMiUzV5ry2xDbY3JtB/C5ZCDWxoTprkdF4gYWlXrcOMliG/LfYbE60sBSWp8UbVvrS31cqzIHL3P+yybsrKpT9OA5DmxFrtR2QiU/9p0NATfJjss18RBZ+kQgH+HSYp028emiePgq78pDYjHjvtHhXxQ/Wg1fEUJRRzkyts3MB4GUYPyTODTHiY91Vo0JCTa6xOTNG/PhcqhjJrsgzS6cr9EAMV43HHRwhYbuw7qVcmLRPNpkL04Nw503AnLx+EhkHw9jXtXJWlrUqgjY++~-1~-1~1795702483~AAQAAAAG%2f%2f%2f%2f%2f8ePfUM0Vx%2f3Qx6+YkZufJjRJ1p8AI1OquBc7dnY%2f6xgW2xMzriOcYH5Xtc%2fi%2fC4daorKIgTSapf9SVSW69Vi1HSKP6kRzDr%2f4gE+pxxWFPckSCK3M9PTAqW0EGT2FB1bPoL07ShuayFI4LrwueIys0Yx9Pxqkx0Tt5gG+oT+ycCEPIZy87u5v2so1yJLqBWtc4O7Y5qUFRJWwDH2DwY6sJUHh81O7c8uhK2kJtRR5ZirnI%3d~-1; bm_s=YAAQbo8QAsZNP9WhAQAA744RGAapqeUvqfcbvo6NpSgtfWXyTGKE/9EMw1YII6pqgsEj4m9REDAUVEmI4VR8Jikn2uBGxIkVzxZvjfXhUWhipEBGUlP1HhNI3BhUD9Guemgq6/6UfV1wr6SsMg9FW90YLU4tzN5fhJytv8I8y6ggssoAxbofnb8xaZHY33sDW4lCw9cg+Z2P95xJ5+HckprHSwb8k4mEClJhoEmz8rfN7FRpwEyoG6NuE+n2EJ9Ra1H9ZNxyXzz7x3lfaA5+rLxOktk+7F4GN14OXr28GLfrx2PSxSIi6+d/wQyNIKVHGCPirBTA/UNGBXXfaU3McwvXeQoU+iGcJB9sy9vYE1vk1tM69gnAguKX0wCv2vfSMFuNS9zD5Gfm40Wgc4njNUDqJDZQqqqWTBoJ5yUItatyC52uVthAN0VnVg72oP23uTL0DAs41HXH3XOmJcqA43GJYulBfcfCoRB4LUtxOSulY76Trj844d/fATayLMiwoHfBXAlaiPnWO5+ecCEWXu6+d0pytAa+rJ5j2HzSfBAhn9ST8I18LJfJ85GGTwRQHNEuEimNxV+TSB9BZtXBnVrE8NHo4toid5vZvkU915/50nk+eQV2gZM334SpZ4QDN4u6CuNFAMS1qfSgDfIrCzjbiigfN79VwyE1ZomKi3TsPluRA1UJEjR/MSyovTkt7sgKoxE4nvkXgEh2+SwMuSU+s2cIxvyFK4qxJDZL4TCnS43qKDszU4gAlfuPhaEDgh0m9NxOzQLv52sg25bvlzYTyR+JIWKX1rqL/+2/Q10KVfqMsf9ux7JHk+LLqdFSLG+HdVdywvbiT0jlzJB7bWWOX26VHqHAq1GXiI/i6hdVfHHjFvPiqyBkwCZ/xSlUgT7hdvhP+GobayPDR9BsGUYoSjj1Sl7/NWbnhqUiq1/LGWqYYWq/jH9rGzB5KUfmDyoHvHDUIvPTeWJmvSVYOprb+WqPrEX1prNzGB/riaG+xpKQebSTYzS3Lg7Zh7MX/fPNUU7MtPY+3x5yRBb+l1X6JL4BbHmE8QaVFErFHv4cGdg5poKeLK5csOWdj7SsgbJfZI7nu2Yrydh30VqvibEkLYWQGX6C1atOJsxHeV8je0I7iJTl7A==; bm_so=588EF5D47EC0CD3B9079B23670BC90D719919EC0AA84A0E4E30857D165F05C02~YAAQjZYWApfgmfGhAQAAQlUQGAn6eJ6F15VjMcb6r1JHvKzR+/dG+Nmmlov92yfZ3C2EfKeh2QW2EtCPrOe4MJj/sZ4EjXRBcIVpvkVmsiC7eMyXZefZa3OO2jNI67mlz/yLoluwJvUD176HKsYhaO/4r+6qFA0MYOsfj5G5aEEotR9BFU0UUOTuyZ3tLAj2QcFlRqSIf5D5MTSNJ0S0JoCJ08FY08dMJTR+Ea2CTD7ZP+r8+PvslO4vl0Q91qhJ6E985Q1mPlkgpq5m0yXFqcFfAQN+XVrULJN+QNun3z/4qjcNtKfT3NbeSrFrvufti5GJfcp8Dr0l1b/oYkcmBWx8ttF14rLHoMoOebzgJnab0+0Mj24LM2XCFVOWEtAm8bE6wIeFj6HADFk9RPB6YmS+cZV1iAur+8Uwz/SBEBScE9QE+JnkEs6A3jZc/ZYHDb4zv1TQ6OWW2AitKDwzYXCaj8xvO/BLocELT+rA56FEZCXB/qAV0cLXxg==~0; bm_sz=FDA7A64BD7498761FA7C3BE9BB44B653~YAAQbo8QAshNP9WhAQAA744RGAEUfgFLp+txmJ0wjWR2TPn0+WZpAtd8B0OVMZG7ACL8LgXG2V4gamIwyG7ehCaGeCXn9uX6/GBshk/uyTojzh1WMT9UytqSBe5t5//dds2SbSmr9ilULOJNJZLWXuEJ1lX32yNW/eq4u4uFnYDg0NwlfPFz84y3PPxaQSM5HYJ01ZhZJfC4RI+o3GPW/dhBx4LovHT6Ps2XMw0UK6BuyrE4T8dm6zZsWr04PrCdWzQHfKd7N5agpez8md/d0Dq2J7b2zCQaIOefGP7E5I2dP885hR20yDnmIZJQRKnaxsvHy1sDDyeTH8x9j8pt0rui3G9IABbBqU/Kr7sQNolrp8sgbZ50HAy09vcLkPd++B9nOnEY/VXBt4FTOC6SaBkYZk84DPnIOND791W2itZXlQBPnRduckCvOj1p017Tgmc/gqFa6vV4yq/nKj84/y7PKrlaTpOHMce8fr07HYrrVGsT9FSB8dm3dL5l+AXyxwKh9y0Pgcee4D2iEEhKidgrnmha84mGGxs=~4539445~4605240; PIM-SESSION-ID=BmlAI0YTMKT2mU9e; sessionId=292eb3d1-a6e7-454a-9e20-e371713135cd; IPI-CasasBahia=UsuarioGUID=9fc6ff39-15d8-4eb1-b5c2-e8cc2efa905e; _gcl_au=1.1.1795733015.1795691684.781058687.1795696659.1795696659.2124383089.1795696659.1795696659; _ga_SGTM=GS2.1.s292eb3d1-a6e7-454a-9e20-e371713135cd$o3$g1$t1795700068$j48$l0$h1400376491$d-8yMmDkZ9OoNg_4XYN9W5xAn9tMjbiX7Bw; _ga=GA1.1.321057660.1795691685; _ga_DPL4W0QCQ5=GS2.1.s1795698656$o3$g1$t1795700068$j48$l0$h665163419$dzYH86o6oNmM1TiTsDuCN-4OX4ctsi0gWTA; AKA_A2=A; header-reject-fill-zip-code=true; ak_bmsc=CA77D4DB691C72CEF7553E9FA7029DEA~000000000000000000000000000000~YAAQz3nMF+EEAwOiAQAASLkLGAGUp42Rcd+7uGt4P/5d6/teLOZZG8dkNlW4GyLPWeMCsN57uL+OVS1yRFU5pYU/xtSc4p9DiU/fiuPIf9BuvyhUZOpvrtcdBUiYJaaG8qIT5b5WeZRvsslE/VeXSEymLvMjNNr9e9JKGhrps2f6YIWgNMsmjDq3kjg+C7C6cuNyomhJvqOJ8ccxVhtVuZb5Z7Us/+gV2TFHZlFRVcONK3CDGj9Fmvs4m3By1F5OrjZuYz7M53KEVURhrK7qV5xX77sjSnUMArYHjLMCsCjJhwmIX0Jr3Ocv8OO5m2d482QqmCY5ObifEiwRF5fx0VApw+kTl3QPDlRqOhSvZdMNy2E+5XRaCGT36t0eJgSbKS9dL1tH/Kz2OnKD5ZxNylcrN02w6ypj9eGUmA==; bm_sv=E82C9E9C57AA93CE4167B420C426E2C1~YAAQbo8QAsdNP9WhAQAA744RGAHgeObmaYP559+Q6Hvj4urpjqwYNA62LOqKFIqObLGZxWhzYtP3ycJtQW+ixGJs3Is/eG+737q4wbzoMEzetu20eJeNXEGlZF59sUoi+725ir1BcIMhURwt32kfIIccvjlYwcev5dwCOvhBz3RiiunHBkbT7wmmGwjFDw9tCzEYcb4ro7185Lh1iTNPLTYFT5n0n+YUprS9n/ppOiZwGEnYC8pJZs92QAoeP8YA+XOfaE4mApR1TU0o55sisg==~1; bm_mi=E1CFED04455034A6D33A8D193E1965B7~YAAQjZYWAsfgmfGhAQAApV8QGAE8VXbqTiYd5K4kYcdGVeHx06qbsHwK/LQnBISno8yEXSaJNdO6m46OE7VeObajBi7UWUpgrPrj+qcRoxsMozNxqBivCINSRKk41hT9QYhvd3n7RvWm1V7Hc8QZbSJPIrc7OjKds195fA8PNOh0i8Md5dIeM+4jWUGt8KAOL2Z+72PKwmkqUSjnbwo+p9I3VB0j1gDUGulb7QyAMTz3Ft8PkjT1iE68hTRo5FSU4k71IiZVCYy4RwBL5k8DAQ34fAZw/GOsHWDLSo8qD51Gu/oE8wYNG8bXKbvRN1Yh6ZQyY8JbeJe/hZsG0MHcqvy55ZgC2EOMewTD4gHgcLqs~1' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers'"""
    r = agent.Request(url, use='curl', force_charset='utf-8', proxies=['rotating-eu'], options='-s -L --insecure '+options, max_age=0)
    return r


def RequestRevs(ssid, page):
    url = "https://pdp-api.casasbahia.com.br/api/v2/reviews/product/" + ssid + "/source/CB?page=" + str(page) + "&size=3"
    options = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:161.0) Gecko/20100101 Firefox/161.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: GCB-TRACKING=94.179.72.26; _abck=9B6DF8B4CEB83BF082F4181D52D4F619~0~YAAQz3nMFxUFAwOiAQAAgLwLGBDBfoTP3in9cp47U3mDzEZsQM1J3GLwd+zYYABKgHwA/nQZuR4wbXNQSMBsoVSSdYkbPgHw5tnd5hLGsiOrcrAuiJd3SBnNYMI0Zk4T6lRg7hGK7HiM6jq5+n+xzTzDsrnWuT1CafPkWW/UP34f0k9YFuhazWrLPtiThElHqCxKzwrseTGj+atUHZw5Chkwo16LecuJoUj/S2r7QRMdCt4Jd2SxqM7qEkOD+eAMyXw2pyaUdwoI12zGmmbyF7QNhzbzQ7p/96Kf0dIyuojYir2qS+isbZA8wvQCBA/gWZ0t86WvwPtsoJLxZ52yPMI5tfRKJooFPHiye5dLgJxWBi/dMchBnU9mvpeHI2llilY3BOdGnxNcZYIixQOjS7DovZ+STaXctBE2cMzA6whWls4/HBvA7yUcdYjYvd1QmJpCyNUtIca0VwPKz1DNOHdnG2brYUkklSUsHzYrwPEl5xZM5UxjFRG9cTKvcxpOfng+IbB2zdaX0Qw2wfExv53lJC9VE42v2SvE84O8ZON141gC1XMiUzV5ry2xDbY3JtB/C5ZCDWxoTprkdF4gYWlXrcOMliG/LfYbE60sBSWp8UbVvrS31cqzIHL3P+yybsrKpT9OA5DmxFrtR2QiU/9p0NATfJjss18RBZ+kQgH+HSYp028emiePgq78pDYjHjvtHhXxQ/Wg1fEUJRRzkyts3MB4GUYPyTODTHiY91Vo0JCTa6xOTNG/PhcqhjJrsgzS6cr9EAMV43HHRwhYbuw7qVcmLRPNpkL04Nw503AnLx+EhkHw9jXtXJWlrUqgjY++~-1~-1~1795702483~AAQAAAAG%2f%2f%2f%2f%2f8ePfUM0Vx%2f3Qx6+YkZufJjRJ1p8AI1OquBc7dnY%2f6xgW2xMzriOcYH5Xtc%2fi%2fC4daorKIgTSapf9SVSW69Vi1HSKP6kRzDr%2f4gE+pxxWFPckSCK3M9PTAqW0EGT2FB1bPoL07ShuayFI4LrwueIys0Yx9Pxqkx0Tt5gG+oT+ycCEPIZy87u5v2so1yJLqBWtc4O7Y5qUFRJWwDH2DwY6sJUHh81O7c8uhK2kJtRR5ZirnI%3d~-1; bm_s=YAAQjZYWAg8UmvGhAQAAx+gXGAYlty8cbYUshH27Zpjb+qgve3vQ/ffXZ+LJKQqh8D6WmM1IkcfbrWxuI6GaOJtW1TQWbdyysm5Juj8Yd+qdPIL+Np2PvIe/JKVHtvpdf3AWvyRjniglkZ6RFRjf8OosE1QA8zu0CxeERgULrWqJBkRRah4BCN/G/Gz6R1qhKQmE8aIJYoeVk5tqb/qVH48XjAod0/jJVlXmxPT0d31eQZ5tAm0jFfkKQpye4q+V5RmQwltJTWPHXQa89ASRs6aeBWk2S6vqO8N58Ime84wX+QK+P+8TSKvwObW0DvEor7DxwuR64pVoxRuI/q4aPDzSrWkqtLe3AbC/UvhYYtWwTbg5NJ+TzkIkbuYwDkEsBbjsvexQE3FmaRgopUFCgHm9SRG9VSNem6WmtpieIh7Iy4MkET/4OJladWY6Pc+eGOJN4X7WFZTBbEdF9sFymIL3vdD75S/E3irNgVX09zKYAhN+P+4Q2FuJ2HBM2MfRwj9v2gpI9836cTB6aLwaSbkZzahyS3+J+Z8gqnv/nUBfVgnampuZ+VoczV690jmfb2YjO9OgkUJ3cJNIuL7fyQnD0FqZgDgwKe4hEyNhUpd88SMtG6hdRgFh5HSbmIX2hr5vAr0Mp/iGQHcHHI0GPPCdw1oVWd3PTr3f6z8k4pJAFZM0ys0+4loMKSPjqc/rktbkIt9jUd/JVnj6j44YbaOBRxbqxLgEXq7dJuX7mdLpU47zBWhhzeqrFfzAn2U5aFvJQ2dGyf3Tt7QnzkwkyhogtiGXUCa4xoL+4NcbnqZHJ+pFLfMsaqc+16t897u8t9Ec3C4YBn5pIX2vtNvjT3IXbnlgbJMpldKHwFkFOLgXv8sqFFTM6bmSIztARTS+niHEQwKWBJW/q+Bf4nYompOAc89Upqmp61sfU6wPPMEJ1325x4kUgkijbN/s+r+nZCUEYwDc+MdLQ4wKW+XlWTIrIFJUdgaXnqe6jIIVLSzjEz5IeZegEM35TukfWsIxP/8DsGwnf3Ff3qX74pu1cMR4VwoMSPw+4xvozTbJFvakGuG3SjXJ/iSOlcLzrhCiBHlSmceIAzrNaxS39iq76Ipy6qKF1Up/g1a4EqWOl8YpoKEHgJEJ7g==; bm_so=588EF5D47EC0CD3B9079B23670BC90D719919EC0AA84A0E4E30857D165F05C02~YAAQjZYWApfgmfGhAQAAQlUQGAn6eJ6F15VjMcb6r1JHvKzR+/dG+Nmmlov92yfZ3C2EfKeh2QW2EtCPrOe4MJj/sZ4EjXRBcIVpvkVmsiC7eMyXZefZa3OO2jNI67mlz/yLoluwJvUD176HKsYhaO/4r+6qFA0MYOsfj5G5aEEotR9BFU0UUOTuyZ3tLAj2QcFlRqSIf5D5MTSNJ0S0JoCJ08FY08dMJTR+Ea2CTD7ZP+r8+PvslO4vl0Q91qhJ6E985Q1mPlkgpq5m0yXFqcFfAQN+XVrULJN+QNun3z/4qjcNtKfT3NbeSrFrvufti5GJfcp8Dr0l1b/oYkcmBWx8ttF14rLHoMoOebzgJnab0+0Mj24LM2XCFVOWEtAm8bE6wIeFj6HADFk9RPB6YmS+cZV1iAur+8Uwz/SBEBScE9QE+JnkEs6A3jZc/ZYHDb4zv1TQ6OWW2AitKDwzYXCaj8xvO/BLocELT+rA56FEZCXB/qAV0cLXxg==~0; bm_sz=FDA7A64BD7498761FA7C3BE9BB44B653~YAAQjZYWAhEUmvGhAQAAx+gXGAHyEAEOXrqS68wClhmSLK0Ioh08oZf60V1kIL9KgioukBZbvR/SlVsFyhApz4NDeZoAUD1H3eDLEflVDUOWX6qWO19zAaRHWX9HF9vN3LBjYbsypKI8wRndYE1E7EeP9MAIHhvJklgXueOFHgrp28HpY9excmy+ru4XnUZqf2+SKs9tl7UyUKwyiaECX/0m7dUODwZNvxEVrhMfTAwmV3D5lYS4mygrWBKRZm0wMgh3v4qG7jOlmcK82uP8UqgmYwkrlrqUGgR59S3IoNauIfUpavP9BslhU1GEnSLZ3y1B1ZDvH6PF6IXOIcHNRNGDHuQ++oALHn1EXMVyi9vzh9zBtUv3goE4F9NnZUqaA07gm0/B9xuSCT8y26t9OWBA5gQYKU670kX1OSHlyBERd+E7UJHAI0qjZzox6eb+SuSMwKQZFLnVxKyrAKJX34h9x4FK8Aexc+K6dpCvZC6mL//3RTr/sncSaU9nudcdCzh8fxmryaxHuAmf7TrNjdYUR1EzCm9z8uTVi/N8L27hdiJGa63Daam5iDP15I0=~4539445~4605240; PIM-SESSION-ID=BmlAI0YTMKT2mU9e; sessionId=292eb3d1-a6e7-454a-9e20-e371713135cd; IPI-CasasBahia=UsuarioGUID=9fc6ff39-15d8-4eb1-b5c2-e8cc2efa905e; _gcl_au=1.1.1795733015.1795691684.781058687.1795696659.1795696659.2124383089.1795696659.1795696659; _ga_SGTM=GS2.1.s292eb3d1-a6e7-454a-9e20-e371713135cd$o3$g1$t1795700068$j48$l0$h1400376491$d-8yMmDkZ9OoNg_4XYN9W5xAn9tMjbiX7Bw; _ga=GA1.1.321057660.1795691685; _ga_DPL4W0QCQ5=GS2.1.s1795698656$o3$g1$t1795700068$j48$l0$h665163419$dzYH86o6oNmM1TiTsDuCN-4OX4ctsi0gWTA; ak_bmsc=CA77D4DB691C72CEF7553E9FA7029DEA~000000000000000000000000000000~YAAQz3nMF+EEAwOiAQAASLkLGAGUp42Rcd+7uGt4P/5d6/teLOZZG8dkNlW4GyLPWeMCsN57uL+OVS1yRFU5pYU/xtSc4p9DiU/fiuPIf9BuvyhUZOpvrtcdBUiYJaaG8qIT5b5WeZRvsslE/VeXSEymLvMjNNr9e9JKGhrps2f6YIWgNMsmjDq3kjg+C7C6cuNyomhJvqOJ8ccxVhtVuZb5Z7Us/+gV2TFHZlFRVcONK3CDGj9Fmvs4m3By1F5OrjZuYz7M53KEVURhrK7qV5xX77sjSnUMArYHjLMCsCjJhwmIX0Jr3Ocv8OO5m2d482QqmCY5ObifEiwRF5fx0VApw+kTl3QPDlRqOhSvZdMNy2E+5XRaCGT36t0eJgSbKS9dL1tH/Kz2OnKD5ZxNylcrN02w6ypj9eGUmA==; bm_sv=E82C9E9C57AA93CE4167B420C426E2C1~YAAQjZYWAhAUmvGhAQAAx+gXGAE0T3RFG7NK2NTiXx+HYm1vKiCZ7dbV0hdDhc1LNmgkVax3W0wLsztuZhQoqYNASrwesNodvJJd8SftonnOVif3tm7UpVPUPNMlO0Tvpouc7YgkGHSX9RHw/k32JtLEUNg5WMEdM1QTqkzEXV+MdlU5IBX/+ZGRMlpeyEHT7Bu2xRBfuc+Jij/I8mwd67GQcPB9ub/xLK3VXtf8hZYLsdstXup6zpv+BB++dIh0EG8iMzkyQ4G6s/g4rf008Q==~1; bm_mi=E1CFED04455034A6D33A8D193E1965B7~YAAQjZYWAsfgmfGhAQAApV8QGAE8VXbqTiYd5K4kYcdGVeHx06qbsHwK/LQnBISno8yEXSaJNdO6m46OE7VeObajBi7UWUpgrPrj+qcRoxsMozNxqBivCINSRKk41hT9QYhvd3n7RvWm1V7Hc8QZbSJPIrc7OjKds195fA8PNOh0i8Md5dIeM+4jWUGt8KAOL2Z+72PKwmkqUSjnbwo+p9I3VB0j1gDUGulb7QyAMTz3Ft8PkjT1iE68hTRo5FSU4k71IiZVCYy4RwBL5k8DAQ34fAZw/GOsHWDLSo8qD51Gu/oE8wYNG8bXKbvRN1Yh6ZQyY8JbeJe/hZsG0MHcqvy55ZgC2EOMewTD4gHgcLqs~1' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""
    r = agent.Request(url, use='curl', force_charset='utf-8', proxies=['rotating-eu'], options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.casasbahia.com.br/'), process_frontpage, dict(context))


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//nav//a[contains(@href, "/c/")]')
    for cat in cats:
        url = cat.xpath('@href').string()
        name = cat.xpath('.//text()').string(multiple=True)

        if name and name not in XCAT and not session.seen(url):
            session.queue(Request(url), process_category, dict(cat=name))


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    subcats = data.xpath('//div[contains(@class, "EncapsuleItensCategory")]/a')
    for subcat in subcats:
        subcat_name = subcat.xpath('.//text()').string(multiple=True)
        url = subcat.xpath('@href').string()

        if subcat_name and url and 'filtro=' in url:
            cat_id = url.split('filtro=')[-1].split('&')[0]
            if not session.seen(cat_id):
                session.queue(RequestProds(cat_id, 1), process_prodlist, dict(cat_id=cat_id, cat=context['cat']+'|'+subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    try:
        prods_json = simplejson.loads(data.content)
    except:
        return

    prods = prods_json.get('products', [])
    for prod in prods:
        pr = dict()
        pr['name'] = prod.get('name')
        pr['url'] = prod.get('url')
        pr['ssid'] = prod.get('id')
        pr['sku'] = str(prod.get('sku'))
        pr['category'] = context['cat']
        pr['manufacturer'] = (prod.get('brand') or {}).get('brand')

        revs_cnt = prod.get('ratingComments')
        if revs_cnt and int(revs_cnt) > 0 and pr['ssid'] and not session.seen(pr['ssid']):
            session.queue(RequestRevs(pr['ssid'], 1), process_reviews, dict(product=pr, revs_cnt=int(revs_cnt)))

    prods_cnt = context.get('prods_cnt', prods_json.get('size', 0))
    offset = context.get('offset', 0) + 20
    if offset < prods_cnt:
        next_page = context.get('page', 1) + 1
        session.queue(RequestProds(context['cat_id'], next_page), process_prodlist, dict(context, offset=offset, page=next_page, prods_cnt=prods_cnt))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.sku = context['product'].get('sku')
    product.category = context['product']['category']
    product.manufacturer = context['product'].get('manufacturer')

    try:
        revs = simplejson.loads(data.content).get('review', {}).get('userReviews', [])
    except:
        revs = []

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev['id'])
        review.date = rev.get('date')

        author = rev.get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('likes')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('dislikes')
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.get('text')
        if excerpt:
            excerpt = excerpt.strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    offset = context.get('offset', 0) + 3
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        session.queue(RequestRevs(product.ssid, next_page), process_reviews, dict(context, offset=offset, page=next_page))
