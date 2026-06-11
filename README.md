# موسوعة الرجال — Streamlit app

Shia narrator database + isnad analyzer over `rijal_core.db`.

## Run
```
cd "Religious - Copy - Copy - Copy"
streamlit run Dirayah3/app/rijal_app.py
```
Opens at http://localhost:8501

## Sections
1. **🔎 مكتبة الرواة (Narrator Library)** — search by name/kunya/laqab; full profile: reliability
   (color-coded verdict + jarh/ta'dil with sources), tabaqah (+modifier +span +source), lifespan,
   aliases, clickable teachers/students, and the narrator's entry text in every rijal book.
2. **📚 كتب الرجال (Books)** — pick one of the 10 matched books, browse or full-text search entries,
   jump from any entry to the narrator's full profile.
3. **🔗 محلّل الأسناد (Isnad Analyzer)** — browse the 183K extracted chains (filter by book / narrator /
   ends-in-masum), view each isnad level-by-level (عطف grouped per level), every narrator badged with
   reliability + tabaqah, and an overall **grade by the weakest narrator** (صحيح/حسن/موثّق/مجهول/ضعيف).

## Files
- `db.py` — cached data-access layer (search, profiles, books, chains, reliability mapping).
- `rijal_app.py` — UI (RTL, light theme via `.streamlit/config.toml`).

## Possible next enhancements
- Free-text isnad input (paste "حدثنا فلان عن فلان…" → resolve narrators → analyze).
- Teacher/student link validation between chain levels (flag broken connections).
- Narrator network graph; tabaqah timeline view.
