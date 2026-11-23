# Project State & Knowledge Base Checklist

**Останнє оновлення**: 23 листопада 2026 р.
**Поточний статус**: Працюємо над переходом від `pro` оглядів до `user` відгуків (на прикладі `review.1mg.com (BB)`).

---

## 1. Де зупинилися прямо зараз
- Користувач переписує файл `review.1mg.com (BB)\new_review.1mg.com.py` у свій правильний стиль.
- Ціль: на прикладі цього файлу розібрати всі ключові архітектурні відмінності парсерів користувацьких відгуків (`review.type = 'user'`) від експертних статей (`review.type = 'pro'`).
- Після завершення редагування користувачем — агент аналізує оновлений код, виділяє нові патерни для `user` рев'ю та фіксує їх у правилах.

---

## 2. Зафіксовані стандарти та правила (вже в `.agentrules`)
1. **Середовище**:
   - Тільки сумісність з **Python 2.7**.
   - Тайпхінти пишемо лише в локальних файлах (скрипти завантаження зрізають їх на льоту).
   - Жодних складних регулярних виразів `re` на кирилиці (у Python 2.7 `\w` бере тільки ASCII). Використовувати `split`, `strip`, `find`.
2. **Серверні відмінності**:
   - **Сервер BB** (`{name} (BB)`): не імпортувати `re` та `simplejson` вручну; додавати `force_charset='utf-8'` у функцію `Request` для неанглійських сайтів; **не** додавати `proxies`, якщо їх не було в оригіналі.
   - **Сервер Prune** (звичайні папки): явні імпорти модулів потрібні.
3. **Лапки**:
   - Одинарні `'...'` для Python-рядків, подвійні `"..."` всередині XPath (`data.xpath('//div[@id="timeline"]/div')`).
4. **Очищення та парсер**:
   - `session.browser.use_new_parser = True` у функції `run()`.
   - `strip_namespace(data)` на початку кожного колбеку з `Response`.
5. **SSID**:
   - З `.html`: `product.ssid = product.url.rstrip('/').split('/')[-1].replace('.html', '')`
   - Без `.html`: `product.ssid = product.url.rstrip('/').split('/')[-1]`
6. **Дати**:
   - Пріоритет №1: `//meta[@property="article:published_time"]/@content`
   - Пріоритет №2: `//time/@datetime`
   - Фолбек: взяття дати в `process_revlist` та передача через `context`. Якщо вказано лише день і місяць — дописування поточного року через `date += ' ' + str(datetime.now().year)`.
7. **Пагінація**:
   - У 90%+ випадках перевіряти першим: `next_url = data.xpath('//link[@rel="next"]/@href').string()`.
8. **Автор (`Person`)**:
   - Шукати ім'я та посилання на профіль:
     ```python
     if author and author_url:
         author_ssid = author_url.split('/')[-1]
         review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
     elif author:
         review.authors.append(Person(name=author, ssid=author))
     ```
9. **Властивості відгуку (Pros & Cons, Text)**:
   - Тільки `review.add_property(type=..., value=...)`.
   - Очищення: `strip(' +-*.:;•,–►…')`.
   - Якщо плюси/мінуси записані в одному тегу через кому суцільним реченням — залишати їх суцільним рядком (не розбивати штучно).
   - Фільтрація тексту огляду через XPath (`preceding-sibling::`, `following-sibling::`, `not(ancestor::footer)` тощо) замість `.replace()`.
   - Код писати тільки під елементи, які реально є на сторінці (жодних порожніх обробників-привидів).

---

## 3. Еталонні файли в репозиторії
- `docs/examples/prune/example_pro_review.py` — приклад для Prune (`ingame.de`).
- `docs/examples/bb/example_newmobile_nl.py` — приклад для BB (`newmobile.nl`).
- `hwtech.ru (BB)\new_hwtech.ru.py` — робочий приклад зі складним видобуванням оцінки без `re`.
- `.agentrules` — центральні правила в корені проекту.
