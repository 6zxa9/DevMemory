---
name: rag-knowledge
description: "Двусторонний обмен знаниями с Pinecone RAG базой. READ: перед задачей ищет существующие решения с кодом. WRITE: после успеха сохраняет решение с реальным кодом, WHY, REJECTED. COMPARE: сверяет с Context7 для актуальности. Работает автоматически в каждом проекте."
---

# RAG Knowledge — двусторонний обмен знаниями

Автоматически ищет проверенные решения перед реализацией и сохраняет новые решения с реальным кодом после успеха. Каждое решение сверяется с Context7 для актуальности.

## CLI

```
python ~/.claude/tools/pinecone-store.py <command>
```

Credentials: `~/.claude/tools/.env` (PINECONE_API_KEY, PINECONE_HOST)
Embedding: Multilingual_E5_Large (Pinecone hosted)

---

## Секция 1: Когда активировать

### AUTO-READ (перед реализацией)

Автоматически запрашивай Pinecone когда:
- Пользователь ставит задачу на реализацию фичи
- Пользователь описывает баг для исправления
- Пользователь просит архитектурное решение
- Начало нового проекта
- Перед любой нетривиальной задачей (3+ файлов, новая механика)

### AUTO-WRITE (после реализации)

Предложи сохранить когда:
- Пользователь говорит **"отлично"** / **"запиши"** / **"сохрани"**
- Завершена нетривиальная фича (3+ файлов изменено)
- Решён production баг (неочевидная причина)
- Найден workaround платформы (Telegram, PixiJS, etc.)
- Настроены числа баланса через итерации
- Принято архитектурное решение с выбором из альтернатив
- После `/game-audit` с хорошей оценкой

### COMPARE (всегда при READ)

При каждом найденном решении:
- Проверить актуальность через Context7 (resolve-library-id → query-docs)
- Если библиотека обновилась → предупредить
- Предложить лучший вариант на основе сравнения

---

## Секция 2: READ Workflow

```
1. Определить ключевые слова задачи (на русском + английском)
2. Выполнить:
   python ~/.claude/tools/pinecone-store.py query "<keywords>" --ns all --top-k 10 -v
3. Если найдены релевантные записи (score > 0.6):
   a. Показать пользователю:
      "Нашёл в базе знаний: [название] (score X.XX)"
   b. Кратко описать решение и показать код если есть
   c. Проверить через Context7:
      - resolve-library-id для библиотек из решения
      - query-docs: "current best practice for [задача]"
   d. Сравнить:
      - "Решение из базы (проверено в production)" vs
      - "Актуальная документация (может быть новее)"
   e. Предложить выбор:
      - Использовать решение из базы
      - Использовать новый подход из документации
      - Гибрид: база + обновления
4. Если не найдено (score < 0.6) — сообщить кратко и продолжить обычную реализацию
```

**Формат ответа пользователю:**

> **Pinecone KB** (score 0.85): `code__energy_lazy_atomic`
> Lazy regen + atomic spend через SQL CTE. Drizzle `db.execute(sql...)`.
> **Context7**: Drizzle docs подтверждают — `db.execute()` актуален в v0.30+.
> **Рекомендация**: использовать решение из базы, код проверен в production.

---

## Секция 3: WRITE Workflow

```
1. Определить что решено (проблема → решение)
2. Извлечь код: конкретные функции, ключевые строки (20-80 строк)
3. Сформировать запись по формату (см. Секция 4)
4. Спросить: "Сохранить в базу знаний? [краткое описание записи]"
5. При подтверждении:
   a. Записать JSON в /tmp/rag_<date>_<topic>.json
   b. python ~/.claude/tools/pinecone-store.py store-patterns /tmp/rag_<date>_<topic>.json
   c. Удалить временный файл
6. Подтвердить: "Сохранено в Pinecone: [название], namespace: [ns]"
```

---

## Секция 4: Формат записи с кодом

### Для design_patterns (store-patterns)

```json
{
  "source": "PROJECT_NAME",
  "date": "YYYY-MM-DD",
  "patterns": [
    {
      "id": "code__<snake_case_name>",
      "name": "Название решения",
      "domain": "backend|frontend|fullstack|platform|architecture|economy|retention|monetization|core_loop|performance|polish|virality|session_design|competitive_intelligence",
      "description": "КОНТЕКСТ: какую проблему решали. ЧТО СРАБОТАЛО: конкретное решение. ПОЧЕМУ: обоснование. ОТВЕРГНУТО: альтернативы и почему нет. ОГРАНИЧЕНИЯ: когда не применимо.",
      "mechanics": ["keyword1", "keyword2", "keyword3"],
      "examples": ["Project X: path/to/file.ts — functionName()"],
      "competitors_using": [],
      "effectiveness": "critical|high|medium",
      "implementation_notes": "FILE: path/to/file.ts\n\n```typescript\n// Ключевой код (20-80 строк)\nexport function solution() {\n  // ...\n}\n```\n\nWHY: почему именно так.\nREJECTED: что не сработало и почему."
    }
  ]
}
```

### Для dev_lessons (store-lessons)

```json
{
  "project": "PROJECT_NAME",
  "date": "YYYY-MM-DD",
  "lessons": [
    {
      "id": "bug__<snake_case_name>",
      "title": "Краткое описание",
      "category": "infrastructure|backend|frontend|telegram|game_design|ci_cd|security|fullstack",
      "tags": ["tag1", "tag2"],
      "pattern": "Что пошло не так (root cause)",
      "rule": "Как делать правильно (prevention rule)",
      "context": "Полная история: что случилось, как нашли, как починили. Код: ```lang\n// fix\n```",
      "severity": "critical|high|medium|low"
    }
  ]
}
```

---

## Секция 5: Критерии качества

### Сохранять

- Решение с **конкретным кодом**, подтверждённое работой в production
- **Неочевидные workaround'ы** платформы (Telegram WebApp, PixiJS, etc.)
- **Формулы и числа**, найденные через итерации (с обоснованием диапазонов)
- **Архитектурные решения** с обоснованием выбора и отвергнутыми альтернативами
- **Production баги** с root cause, fix, prevention rule
- Код **20-80 строк** ключевой логики (не весь файл, а суть)

### НЕ сохранять

- Очевидные вещи из документации (CRUD, стандартные паттерны)
- Сырой код без контекста "почему"
- Промежуточные решения (только финальные, проверенные)
- Код который работает но НЕ проверен в production
- Информация которая есть в README / официальной документации

### Тест на ценность

> Если через 6 месяцев эта запись поможет избежать 2+ дней работы — сохраняй.
> Если нет — не засоряй базу.

---

## Секция 6: Context7 Integration

При каждом READ из базы:

```
1. Определить библиотеки/фреймворки в найденном решении
2. resolve-library-id для каждой (React, Fastify, Drizzle, PixiJS, etc.)
3. query-docs: "current best practice for [задача из решения]"
4. Сравнить:
   - Решение из базы: проверено в production, с кодом
   - Актуальная документация: может содержать новые API, breaking changes
   - Есть ли deprecated API в решении из базы?
5. Предложить выбор:
   a) "Решение из базы (проверено в production)" — если код актуален
   b) "Новый подход из документации" — если API изменился
   c) "Гибрид: логика из базы + новый API" — если есть minor changes
6. НЕ копировать слепо! Решение из базы = reference, не template
```

---

## Секция 7: Pinecone CLI

```bash
# Поиск (READ)
python ~/.claude/tools/pinecone-store.py query "описание задачи" --ns all -v
python ~/.claude/tools/pinecone-store.py query "energy system" --ns design_patterns --top-k 5 -v
python ~/.claude/tools/pinecone-store.py query "Redis bugs" --ns dev_lessons --json

# Запись (WRITE)
python ~/.claude/tools/pinecone-store.py store-patterns /tmp/patterns.json
python ~/.claude/tools/pinecone-store.py store-lessons /tmp/lessons.json
python ~/.claude/tools/pinecone-store.py store-audit /tmp/audit.json
python ~/.claude/tools/pinecone-store.py store-docs /tmp/doc.md

# Управление
python ~/.claude/tools/pinecone-store.py info
python ~/.claude/tools/pinecone-store.py list --ns design_patterns
python ~/.claude/tools/pinecone-store.py delete --id "code__old_entry"
python ~/.claude/tools/pinecone-store.py delete --prefix "code__deprecated_"
```

### Namespace'ы

| Namespace | Содержимое | Когда запрашивать |
|-----------|-----------|-------------------|
| `design_patterns` | Game design решения с кодом | Перед реализацией фичи |
| `dev_lessons` | Production баги, root cause, fix | Перед деплоем, при ошибке |
| `game_audits` | Scorecard по 10 измерениям | При оценке прогресса |
| `competitors` | Конкурентные сканы | При benchmark'е |
| `project_docs` | Ключевые документы | При контексте проекта |

---

## Примеры записей с кодом

### Пример: Energy Lazy Regen + Atomic Spend

```json
{
  "id": "code__energy_lazy_atomic",
  "name": "Energy Lazy Regen + Atomic Spend (SQL CTE)",
  "domain": "backend",
  "description": "КОНТЕКСТ: Energy system с regen по таймеру. Наивный подход (cron job) создаёт race conditions при concurrent requests. ЧТО СРАБОТАЛО: lazy regen — не обновлять energy по таймеру, а вычислять текущее значение при каждом запросе через SQL CTE. Atomic spend через UPDATE ... WHERE energy >= cost. ОТВЕРГНУТО: cron job (race conditions), Redis counter (persistence issues), application-level lock (bottleneck). ОГРАНИЧЕНИЯ: требует PostgreSQL, не подходит для real-time UI без WebSocket push.",
  "mechanics": ["energy", "lazy_regen", "atomic", "sql_cte", "race_condition"],
  "examples": ["Pet Hotel v2: server/src/services/energy.ts — spendEnergy()"],
  "effectiveness": "critical",
  "implementation_notes": "FILE: server/src/services/energy.ts\n\n```typescript\nexport async function spendEnergy(playerId: number, cost: number) {\n  const result = await db.execute(sql`\n    WITH current AS (\n      SELECT\n        energy + LEAST(\n          FLOOR(EXTRACT(EPOCH FROM (NOW() - last_energy_update)) / ${REGEN_SECONDS}),\n          ${MAX_ENERGY} - energy\n        ) as computed_energy\n      FROM players WHERE id = ${playerId}\n    )\n    UPDATE players SET\n      energy = current.computed_energy - ${cost},\n      last_energy_update = NOW()\n    FROM current\n    WHERE players.id = ${playerId}\n      AND current.computed_energy >= ${cost}\n    RETURNING energy\n  `);\n  return result.rowCount > 0;\n}\n```\n\nWHY: SQL CTE вычисляет актуальную energy с учётом regen, а WHERE >= cost гарантирует atomic spend. Один запрос = zero race conditions.\nREJECTED: cron job обновлял energy каждую минуту — при 100 concurrent requests 15% получали stale value. Redis INCRBY не переживал restart."
}
```
