# Project Summary — Cohort Compass

---

## English version (LinkedIn post)

---

🧭 **Built an end-to-end e-commerce analytics platform on 285M real events. Here's what I learned.**

As a career-switcher into data analytics, I wanted a portfolio project that actually shows SQL depth — not just Jupyter notebooks on Titanic. So I spent two weeks building Cohort Compass.

**What it is:**
A full analytics platform on the REES46 dataset (285M events, Oct 2019–Apr 2020, real online store). 8 interactive dashboards, SQL-first architecture, live public demo.

**What I built:**
- 14-model dbt warehouse: staging → intermediate → marts, with full lineage graph
- 8 Streamlit pages: Funnel, Cohort Retention, RFM Segmentation, Churn Lab, Customer Journey (Sankey), Auto-Insights, Data Model
- Every chart has a "Show SQL" toggle — the interviewer can see exactly what SQL powers each visualization
- Churn classifier (LogReg, AUC 0.63) — intentionally honest: excluded 3 features that caused leakage
- 0$ infra: DuckDB runs as a single file, deployed on Streamlit Community Cloud

**Key findings from the data:**
- Monthly CVR (viewers → buyers): ~11% — drops noticeably in colder months
- M+1 cohort retention: **16.6%** — typical for e-commerce, but significant drop-off after first purchase
- Largest RFM segment: **Loyal customers (46%)** — Champions + Loyal = 65% of all buyers
- 12 CVR anomaly days detected across 214 days via rolling Z-score SQL
- Average customer LTV: ~$982 over 3.3 purchases

**The hardest technical challenge:**
DuckDB buffer pool = 75% of RAM. On my 16 GB machine, just opening the 14 GB database fills 12.4 GB instantly. Any window function over 285M rows OOMs. Solution: bypass DuckDB entirely and read raw Parquet via pyarrow for the most memory-intensive operations.

**What I learned:**
- SQL-first architecture (dbt DAG) makes every transformation auditable and testable
- Scale forces you to make architectural decisions early — "just add a column" can cost 12 GB of RAM
- Honest ML > impressive AUC: removing leaking features dropped AUC from ~0.85 to 0.63, but made the model actually useful
- CI/CD for data projects is non-trivial — debugging dbt docs on GitHub Pages taught me a lot about build pipelines

**Links:**
- Live Demo: https://cohort-compass-hd.streamlit.app
- dbt Docs (full lineage): https://heorhiidzhyncharadze.github.io/cohort-compass
- GitHub: https://github.com/HeorhiiDzhyncharadze/cohort-compass

\#DataAnalytics \#SQL \#dbt \#DuckDB \#Python \#Streamlit \#Portfolio \#DataEngineering \#MachineLearning

---

## Ukrainian version (розгорнутий опис для портфоліо)

---

### Cohort Compass — що це і навіщо

Більшість junior-портфоліо в аналітиці — це Jupyter notebook на датасеті Olist чи Titanic. Я хотів показати щось інше: реальний масштаб, SQL-глибину і production-ready архітектуру. Тому витратив два тижні на Cohort Compass.

**Датасет:** REES46 eCommerce — 285 мільйонів подій з реального інтернет-магазину (жовтень 2019 — квітень 2020). Чотири типи подій: view, cart, remove_from_cart, purchase. 14 ГБ сирих CSV.

---

### Що побудовано

**Архітектура (SQL-first):**

```
CSV (14 GB) → Parquet (партиції по місяцях) → DuckDB зовнішнє view
                                                      ↓
              dbt-duckdb: staging → intermediate → marts (14 моделей)
                                                      ↓
                    Streamlit app (8 сторінок) + sklearn LogReg
```

**dbt warehouse — 14 моделей:**
- `stg_events` — очищення, дедупл., типізація (VIEW, ніколи не матеріалізуємо 285M рядків)
- `int_sessions`, `int_purchases`, `int_users` — ephemeral CTEs
- `fct_purchases` — incremental TABLE з unique_key (purchases only)
- `dim_users` — spine всіх покупців
- `mart_funnel`, `mart_cohorts`, `mart_rfm`, `mart_ltv`, `mart_churn_features`, `mart_journey`, `mart_anomalies` — аналітичні marts

**8 Streamlit сторінок:**
1. **Overview** — KPI-картки (GMV, CVR, AOV, Repeat rate), тренд + 7-денна MA
2. **Funnel** — воронка view→cart→purchase, CVR по категоріях
3. **Cohort Retention** — матриця утримання, криві по когортах
4. **RFM** — скаттер R×F, сегменти Champions/Loyal/At Risk/Lost
5. **Churn Lab** — розподіл ймовірностей, what-if симулятор, ROC AUC
6. **Customer Journey** — Sankey-діаграма переходів між типами подій (SQL: LAG по сесії)
7. **Auto-Insights** — автоматичне виявлення аномалій CVR (rolling Z-score, чистий SQL)
8. **Data Model** — вбудований dbt lineage graph + каталог моделей + SQL snippets

**"Show SQL" toggle** — кожен чарт показує точний SQL що його живить. Рекрутер бачить не просто візуалізацію, а аналітичне мислення.

---

### Реальні дані і знахідки

Аналіз на ~2 млн унікальних покупців (у повному датасеті):

| Метрика | Значення | Інтерпретація |
|---|---|---|
| Monthly CVR (viewers → buyers) | **~11%** | Частка переглядачів, що купили у тому ж місяці |
| M+1 cohort retention | **16.6%** | Типово для e-commerce; різкий відтік після першої покупки |
| Найбільший RFM сегмент | **Loyal (46%)** | Champions + Loyal = 65% всіх покупців |
| Аномалії CVR | **12 з 214 днів** | Rolling Z-score, |Z| > 2 |
| Середній LTV | **~$982** | За 3.3 замовлення на покупця |
| Churn model AUC | **0.63** | Чесна модель, 3 leaking фічі виключено |

**Цікавий нюанс:** `cart_to_purchase_rate` в жовтні 2019 > 100%. Це не баг — це артефакт місячної агрегації: частина покупців поклала товари у кошик у вересні і купила у жовтні. Саме такі нюанси виникають при роботі з реальними даними.

---

### Технічні складнощі

**1. DuckDB buffer pool (найважче)**

DuckDB за замовчуванням займає 75% RAM. На моїй машині (16 GB) — це 12 ГБ. Просто відкрити `cohort_compass.duckdb` (зовнішні view на 14 ГБ Parquet) = заповнити 12.4 ГБ. Будь-який запит через `stg_events` — OOM.

Рішення: для `mart_journey` (LAG window function по 285M рядках) — закрити DuckDB і читати Parquet напряму через pyarrow. `pandas shift(1)` замість SQL `LAG`. Знайшов рішення після 6 невдалих спроб.

Урок: **коли DB-файл > 60% RAM — обходи DuckDB, читай Parquet напряму.**

**2. dbt docs на GitHub Pages**

`dbt docs generate --no-compile` потребує існуючого `manifest.json`. На CI (fresh checkout) його немає → порожній сайт з `(loading)`. Рішення: додати крок `dbt compile` перед генерацією docs.

**3. CI debugging**

Спочатку всі 4 workflow runs були червоні. Причина — стояли `</content>` XML-артефакти в кінці YAML файлів (баг інструменту що їх писав). YAML валідатор падав на "could not find expected ':'". Знайшов hex-редактором.

**4. Churn model leakage**

Перша версія моделі мала AUC ~0.85. Занадто добре. Знайшов 3 leaking фічі:
- `days_since_last_purchase` — напряму кодує label `is_churned`
- `r_score` (NTILE на `last_purchase_date`) — майже те саме через NTILE
- `cohort_month_num` — нові когорти не можуть бути churned за визначенням (< 60 днів у датасеті)

Після виключення → AUC 0.63. Чесніший і реалістичніший результат.

---

### Що я навчився

**SQL:**
- Window functions на реальному масштабі (285M рядків) вимагають архітектурних рішень — не тільки правильного синтаксису
- dbt DAG думання: кожна трансформація — це node з визначеним grain і upstream deps
- Sessionization через LAG + cumulative SUM — non-trivial pattern, рідко в junior-проєктах
- Rolling Z-score через AVG/STDDEV window — "auto-insights" чистим SQL без Python

**Інфраструктура:**
- DuckDB buffer pool behavior — дуже не очевидно без реального досвіду
- CI/CD для data проєктів: `dbt parse` без реальної БД, profiles.yml on-the-fly, `dbt compile` vs `dbt docs generate`
- Binary files (`.duckdb`) і git CRLF — потенційна проблема на Windows

**ML:**
- Feature leakage — не тільки теорія, а реальна проблема навіть у простих моделях
- Honest AUC важливіший за impressive AUC

---

### Що б зробив по-іншому

1. **Більше dbt тестів від початку** — зараз тільки 4 тести в `stg_events.yml`. Планував 40+, не дійшов.
2. **Раніше тестував deploy** — всі проблеми зі Streamlit Cloud виявились в кінці, коли вже хотілось finished.
3. **`.gitattributes` з самого початку** — `*.duckdb binary` запобіг би потенційній CRLF-корупції файлу на Windows.
4. **Ретентійна аналітика по категоріях** — цікавило б чи retention відрізняється по electronics vs fashion, але не встиг.

---

### Підсумок

Проєкт займав ~80 годин протягом 2 тижнів. На виході:
- Повна analytics платформа з live demo
- 14-модельний dbt warehouse з lineage graph
- 8 інтерактивних сторінок зі "Show SQL"
- Deployed на Streamlit Cloud + GitHub Pages
- CI/CD pipeline (pytest + dbt parse + auto-deploy docs)

Найважливіший результат — не цифри, а **розуміння trade-offs**: коли VIEW, коли TABLE, коли incremental, коли bypasс DuckDB взагалі. Це те, що junior-портфоліо на Jupyter notebook не дає.
