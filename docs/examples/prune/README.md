# Еталонні агенти для сервера Prune

- Папки агентів мають чисту назву без суфіксів (наприклад `ingame.de`, `reviews.fotokoch.de`).
- Скрипт завантаження: `upload_code.py`.
- Використовує числовий `agent_id` та `product_test.functions.upload_code`.

### Додані зразки:
1. **`example_pro_review.py`** (на базі `ingame.de`):
   - **Тип огляду**: `review.type = 'pro'` (експертний огляд).
   - **Повний конвеєр**: `run` -> `process_frontpage` -> `process_revlist` -> `process_review`.
   - **Product**: витягування назви через спліт заголовка, формування категорій через ієрархію (`Spiele|Plattformen|Genre`), виробник з таблиць характеристик.
   - **Review**:
     - Автор: `Person` з `profile_url` та `ssid`.
     - Оцінка: витягування значення з атрибутів `@alt` та додавання `Grade(type='overall', value=..., best=10.0)`.
     - Плюси/Мінуси: пошук у таблицях `<td>` за префіксами `+` та `-`.
     - Тексти: розділення на `summary` (лід/вступ), `conclusion` (висновок/Fazit) та `excerpt` (основне тіло без висновку).

