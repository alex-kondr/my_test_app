# Project State & Knowledge Base Checklist

**Останнє оновлення**: 24 листопада 2026 р.
**Поточний статус**: Завершено та перевірено парсер `review.eftm.com-au (BB)\new_review.eftm.com-au.py` (`review.type = 'pro'`).

---

## 1. Останній прогрес
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

## 2. Стандарти назв функцій (Architecture Rules)
- `run` — точка входу (ініціалізація `session.browser.use_new_parser = True`).
- `process_frontpage` — головна сторінка сайту.
- `process_catlist` — список/дерево категорій (HTML чи JSON API).
- `process_prodlist` / `process_revlist` — перелік товарів / перелік оглядів відповідно.
- `process_product` / `process_review` — картка товару / сторінка експертного огляду (`type = 'pro'`).
- `process_reviews` — сторінка множинних відгуків покупців (`type = 'user'`).

---

## 3. Відмінності USER відгуків від PRO
1. **Співвідношення**: В `pro` 1 товар = 1 огляд. В `user` 1 товар = список відгуків (`product.reviews.append(review)` у циклі, `emit(product)` лише один раз наприкінці, якщо є відгуки).
2. **SSID відгуку**: Для кожного відгуку покупця обов'язковий свій `review.ssid` (з ID у JSON або через `review.digest()`).
3. **Verified Buyer**: Властивість `review.add_property(type='is_verified_buyer', value=True)`.
4. **Виробник і SKU**: В інтернет-магазинах частіше з'являються `product.sku = product.ssid` та `product.manufacturer = ...` (наприклад, з `application/ld+json`).
