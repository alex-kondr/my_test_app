

revs = data.xpath('//div[contains(@class, "chakra-stack") and @style]')
for rev in revs:
    name = rev.xpath('.//div[@class="css-0"]/text()').string()
    grade_overall = rev.xpath('.//div[@class="css-1r069ov"]/text()').string().split('/)[0]


//a[@class="chakra-button css-yuhplx" and .//*[@points="9 18 15 12 9 6"]]

//div[@class="chakra-stack css-63nlbd"]//div[@class="css-y0n1xr" and not(contains(., "Modell") or contains(., "Gesamtergebnis"))]
