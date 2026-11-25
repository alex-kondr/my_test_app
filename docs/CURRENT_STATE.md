# Project State & Knowledge Base Checklist

**Останнє оновлення**: 25 листопада 2026 р.
**Поточний статус**: Завершено та перевірено `review.21vek.by (BB)/new_review.21vek.by.py` (`review.type = 'user'`). Файл збережено як еталонний зразок для стеку BB у `docs/examples/bb/example_review_21vek_by.py`, а нові правила зафіксовано в `.agentrules`.

---

## 1. Останній прогрес
- **review.21vek.by (BB)**:
  - Повністю переписано та протестовано (`review.21vek.by.txt` — 19/19 чистих `EMIT: Product(...)`).
  - Категорії: JSON API (`https://gate.21vek.by/catalog/catalog`), 3-рівневий обхід (`XCATS`, `isVirtual`, `cats`/`cats1`/`subcats`).
  - Лістинг (`process_prodlist`): картки товарів через `data-testid="product-list"`, немодифіковані HTML-URL, ранній вихід (`return`) при `revs_cnt == 0` при сортуванні за рейтингом.
  - Товар (`process_product`): збір `pr = dict()` з `context` + `manufacturer` з `ld+json` (`"""//script[contains(., '"@type":"Product"')]/text()"""`).
  - Відгуки (`process_reviews`): `RequestRevs` через `curl` (`gate.21vek.by/reviews/product/{slug}/reviews`), `Product()` + `product.sku = product.ssid`, фільтр шаблонного автора `'Покупатель 21vek.by'`, `offset += 10` по `context['revs_cnt']`.
  - Додано правила до `.agentrules`: потрійні лапки замість екранування, стиль обходу дерева категорій (`XCATS`), `ssid` vs `sku`, незмінність HTML-URL, ранній вихід із пагінації.
- **review.emag.ro (BB)**:
  - З головної сторінки (`process_frontpage`) збираються посилання департаментів вищого рівня.
  - У `process_catlist` реалізовано рекурсивний перехід по навігаційному дереву категорій у сайдбарі з конкатенацією шляху `cat_path = context['cat'] + '|' + subcat_name`. Коли на сторінці категорій більше немає (`if not cats:`), автоматично викликається `process_prodlist`.
  - У `process_product`: витягуються дані товару (`application/ld+json`), перевіряється наявність відгуків (`reviewCount > 0`), дані зберігаються у `product = dict()` (без передачі інстансу `Product()` через `context`).
  - У `process_reviews`: ініціалізується повноцінний `Product()`, відгуки парсяться з JSON API (`product-feedback`), очищуються від емодзі через `remove_emoji`, додаються властивості `excerpt` та `is_verified_buyer`, реалізовано пагінацію відгуків пачками по 20 штук (`page[limit]=20`).
- **review.eftm.com-au (BB)**:
  - Створено папку агента через `create_agent/main.py`.
  - Повністю реалізовано про-парсер: навігація по сторінках оглядів (`process_revlist`), парсинг товару та огляду (`process_product`).
  - Виправлено очищення `product.name` від залишків слова "review", покращено вилучення `product.category` та `product.ssid` (з числових ID наприкінці URL).
  - Підтверджено коректне вилучення `grade_overall`, `grades`, `summary`, `conclusion` та `excerpt`.
- **review.bellen.nl (BB)**:
  - Розв'язано проблему з неробочим сайтом через `sitemap.xml` з обходом XML namespaces та параметром `ignore_errors=True`.
- **review.1mg.com (BB)**:
  - Реалізовано логіку збору категорій та товарів з JSON API PWA.

---

## 2. Стандарти назв функцій та категорій (Architecture Rules)
- `run` — точка входу (ініціалізація `session.browser.use_new_parser = True`).
- `process_frontpage` — головна сторінка сайту.
- `process_catlist` — список/дерево категорій (HTML чи JSON API).
- `process_prodlist` / `process_revlist` — перелік товарів / перелік оглядів відповідно.
- `process_product` / `process_review` — картка товару / сторінка експертного огляду (`type = 'pro'`).
- `process_reviews` — сторінка множинних відгуків покупців (`type = 'user'`).
- **Іменування рівнів категорій**:
  - Перший (головний) рівень завжди називається `cats` (`for cat in cats:` → `name`).
  - Останній (кінцевий) рівень завжди називається `subcats` (`for subcat in subcats:` → `subcat_name`).
  - Усі проміжні рівні між ними називаються послідовно: `cats1` (`cat1` / `cat1_name`), `cats2` (`cat2` / `cat2_name`) і т. д.
  - Формат шляху категорії: `name + '|' + cat1_name + '|' + subcat_name`.

---

## 3. Відмінності USER відгуків від PRO
1. **Співвідношення**: В `pro` 1 товар = 1 огляд. В `user` 1 товар = список відгуків (`product.reviews.append(review)` у циклі, `emit(product)` лише один раз наприкінці, якщо є відгуки).
2. **SSID відгуку**: Для кожного відгуку покупця обов'язковий свій `review.ssid` (з ID у JSON або через `review.digest()`).
3. **Verified Buyer**: Властивість `review.add_property(type='is_verified_buyer', value=True)`.
4. **Виробник і SKU**: В інтернет-магазинах частіше з'являються `product.sku = product.ssid` та `product.manufacturer = ...` (наприклад, з `application/ld+json`).
