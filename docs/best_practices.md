# Книга рецептів та найкращих практик (Best Practices)

Цей документ акумулює перевірені рішення для написання агентів у нашому проекті.

---

## 1. Робота з ідентифікаторами (`ssid`)
### Стандартний патерн (використовується майже всюди):
Витягування останнього сегмента (slug/ID) з URL з очищенням розширення `.html` та кінцевих слешів:
```python
product.ssid = product.url.rstrip('/').split('/')[-1].replace('.html', '')
review.ssid = product.ssid
```

> [!NOTE]
> Спроби витягувати суто число через регулярні вирази з назви статті часто призводять до сміттєвих значень (наприклад, з `...-dlya-windows-7-8-10.html` візьметься `7`), тому повний slug є значно надійнішим і унікальним.

---

## 2. Робота з оцінками (`Grade`)
Стандартний підхід — витягування оцінки з виділених елементів верстки (бейджі, атрибути зображень, класи):

### Еталонний приклад з `example_pro_review.py`:
Витягування оцінки з атрибута `@alt` зображення (наприклад, графік оцінки):
```python
grade_overall = data.xpath('//img[contains(@class, "RatioPlaceholder")]/@alt[contains(., "Test-Wertungsgrafik")]').string()
if grade_overall:
    grade_overall = grade_overall.split('-')[-1]
    if grade_overall and grade_overall[0].isdigit() and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))
```

### Специфічний випадок (виняток): витягування оцінки з суцільного тексту
Використовується рідко, коли оцінка не має окремого тегу/класу, а вписана прямо в текст статті:
```python
grade_overall = data.xpath("//div[@itemprop='articleBody']//text()[contains(., 'из 5') or contains(., '/10') or contains(., 'балл')]").string(multiple=True)
if grade_overall:
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:балл\w*)?\s*(?:из|\/)\s*(\d+(?:\.\d+)?)', grade_overall)
    if m:
        val = float(m.group(1))
        best = float(m.group(2))
        review.grades.append(Grade(type='overall', value=val, best=best))
```

---

## 3. Розділення тексту: Summary, Conclusion та Excerpt (для pro-оглядів)
В експертних оглядах (`review.type = 'pro'`) текст огляду розділяється на логічні частини:
1. **`summary`** — вступний абзац (лід-текст):
   ```python
   summary = data.xpath('//p[contains(@class, "leadText")]//text()').string(multiple=True)
   if summary:
       review.add_property(type='summary', value=summary)
   ```
2. **`conclusion`** — блок висновку (наприклад, під заголовком "Fazit" / "Висновок"):
   ```python
   conclusion = data.xpath('(//h2[regexp:test(., "Fazit", "i")]/following-sibling::p)[last()]//text()').string(multiple=True)
   if conclusion:
       review.add_property(type='conclusion', value=conclusion)
   ```
3. **`excerpt`** — основний текст огляду, який йде **до** блоку висновку (`preceding::p`), щоб уникнути дублювання:
   ```python
   excerpt = data.xpath('//h2[regexp:test(., "Fazit", "i")]/preceding::p//text()').string(multiple=True)
   if excerpt:
       review.add_property(type='excerpt', value=excerpt.strip())
   ```

---

## 3. Обробка плюсів і мінусів (`pros` / `cons`)
Заголовки блоків плюсів/мінусів часто містять варіації (`Плюсы:`, `Плюсы продукта:`, `Достоинства`).

### Рецепт:
```python
# Шукаємо за коренем слова, щоб не пропустити через двокрапку чи інші слова
pros = data.xpath('//p[contains(strong, "Плюс") or contains(., "Плюс")]/following-sibling::ul[1]/li')
for pro in pros:
    pro_text = pro.xpath(".//text()").string()
    if pro_text:
        pro_text = pro_text.strip(u' +-*.:;•,–►…')
        if len(pro_text) > 1:
            review.add_property(type='pros', value=pro_text)
```

---

## 4. Логіка формування категорій (`product.category`) та мовна специфіка
1. **Фільтрація оглядів за мовою джерела:**
   Маркери огляду залежать від мови сайту. Наприклад, для німецьких сайтів часто використовується маркер `'im Test'` або `'Test'`:
   ```python
   # Тільки статті, що є оглядами:
   if 'im Test' in title:
       session.queue(...)
   # Очищення назви продукту від маркера:
   product.name = context['title'].split('im Test')[0].strip()
   ```

2. **Умовна ієрархія категорій (приклад логіки з ingame.de):**
   Категорія часто будується динамічно залежно від наявності специфікацій. Наприклад, якщо знайдено платформу або жанр — це ігри (`Spiele`), якщо нічого з цього немає — це техніка (`Technik`):
   ```python
   product.category = 'Spiele'
   
   platforms = data.xpath('...').string()
   if platforms:
       product.category += '|' + platforms
   
   genres = data.xpath('...').string()
   if genres:
       product.category += '|' + genres
   
   # Fallback: якщо немає ні платформ, ні жанрів — перезаписуємо на загальну категорію:
   if not platforms and not genres:
       product.category = 'Technik'
   ```

---

## 5. Робота з `use_new_parser` та `strip_namespace`
Коли використовується новий парсер, розмітка сторінки практично ідентична до інспектора в браузері (DevTools), але вона може містити простори імен XML (`xmlns`, `ns0:`).

### Шаблон обов'язкової зв'язки:
```python
# 1. Оголошується на самому початку файлу першою функцією:
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


# 2. Вмикається у run():
def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(...)


# 3. Викликається ПЕРШИМ рядком у ВСІХ функціях-обробниках:
def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)
    ...

def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)
    ...
```

---

## 6. Пагінація
Перевірка наявності наступної сторінки:
```python
next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
if next_url:
    session.queue(Request(next_url), process_revlist, dict())
```

---

## 7. Обробка дат
Формат дати в моделі `Review.date` має бути строгим: `YYYY-MM-DD`.
Якщо дата в тезі `<meta>`:
```python
# Приклад: 2023-05-12T14:30:00+00:00
raw_date = data.xpath("//meta[@property='article:published_time']/@content").string()
if raw_date:
    review.date = raw_date.split('T')[0]
```
