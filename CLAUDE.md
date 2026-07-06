# Jaffle Shop — Analytics Portfolio Project

## מה הפרויקט
פרויקט פורטפוליו שמדגים כישורי Data/Business/Product Analyst לתפקידים בחברות טק ישראליות.
הנתונים: מסעדה בדיונית "Jaffle Shop" — 935 לקוחות, 61,948 הזמנות, 6 סניפים, 10 מוצרים.

## סטטוס נוכחי
- [x] Phase 0 — Environment Setup (Python 3.14, dbt-duckdb 1.10.1, DuckDB 1.5.4)
- [x] Phase 1 — dbt analytics layer (6 models חדשים + 27 tests)
- [x] Phase 2 — SQL Analyses (6 קבצים ב-analyses/)
- [x] Phase 3 — Streamlit Dashboard (5 דפים: Overview, Revenue, Customers, Products, Locations, Segmentation)
- [ ] Phase 4 — Predictive Models (Churn + LTV)
- [ ] Phase 5 — Google Sheets export
- [ ] Phase 6 — Power BI (.pbix)
- [ ] Phase 7 — Notion storytelling

## מבנה תיקיות
```
jaffle-shop-main/
├── models/
│   ├── staging/          ← 6 views (ניקוי + rename)
│   └── marts/
│       ├── (6 tables קיימים)
│       └── analytics/    ← 6 tables שבנינו
├── analyses/             ← 6 SQL queries עסקיות
├── python/
│   └── utils/            ← db_connector.py, plotting_theme.py
├── dashboard/
│   ├── app.py            ← דף Overview
│   ├── explore.py        ← גרסה ישנה / sandbox
│   └── pages/
│       ├── 1_Revenue.py
│       ├── 2_Customers.py
│       ├── 3_Products.py
│       ├── 4_Locations.py
│       └── 5_Segmentation.py
├── exports/              ← 17 קבצי CSV של כל הטבלאות
├── seeds/jaffle-data/    ← קבצי CSV גולמיים (raw)
└── jaffle_shop.duckdb    ← מסד הנתונים המקומי

```

## איך להריץ

### dbt
```bash
cd "C:\Users\royi1\OneDrive\Desktop\Data Project\jaffle-shop-main"
# PATH צריך לכלול:
# C:\Users\royi1\AppData\Local\Python\pythoncore-3.14-64\Scripts

dbt run       # בונה את כל ה-models
dbt test      # מריץ 57 tests
dbt docs generate && dbt docs serve   # lineage diagram
```

### Streamlit Dashboard
```bash
streamlit run dashboard/app.py --server.port 8503
# פתח: http://localhost:8503
# פורטים 8501, 8502 תפוסים על ידי פרויקטים אחרים
```

### Python scripts
```bash
python python/00_setup.py      # health check — row counts לכל הטבלאות
python python/explore_data.py  # ממצאים מרכזיים ב-terminal
```

## הגדרות סביבה
- **Python:** 3.14.5 (נמצא ב-C:\Users\royi1\AppData\Local\Python\pythoncore-3.14-64\)
- **pip:** python -m pip (לא pip ישירות)
- **dbt profile:** ~/.dbt/profiles.yml — profile name: "default"
- **DuckDB path:** jaffle-shop-main/jaffle_shop.duckdb
- **dbt schema:** כל ה-models נמצאים ב-schema "main" (dev mode — generate_schema_name macro מאחד הכל ל-main)

## ממצאים עיקריים שגילינו
1. Revenue גדל x5.8 (ספט׳ 2024 → אוג׳ 2025): $16K → $94K
2. 77% מהזמנות הן שתייה בלבד (AOV $6.36) — מעורבות שוות $27 (x4)
3. רק 2 מתוך 6 סניפים פעילים בנתונים (Philadelphia + Brooklyn)
4. Philadelphia מרוויחה $4,215/חודש לעומת Brooklyn $2,183
5. "Cannot Lose Them" — 82 לקוחות עם avg spend $998 שלא הזמינו לאחרונה
6. nutellaphone — margin 89% אבל volume נמוך (Question Mark → הזדמנות)
7. chai and mighty — perishable risk 29% (הכי גבוה = סיכון בזבוז)

## packages מותקנים
dbt-duckdb, duckdb, pandas, numpy, matplotlib, seaborn, plotly,
streamlit, scikit-learn, lifetimes, shap, statsmodels, jupyter

## מה הלאה (Phase 4)
- python/04_churn_model.py — Logistic Regression + Random Forest + SHAP values
- python/05_ltv_forecast.py — BG/NBD model + Gamma-Gamma
- python/06_revenue_diagnostics.py — anomaly detection
- dashboard/pages/6_Predictions.py — churn threshold slider + LTV forecast
