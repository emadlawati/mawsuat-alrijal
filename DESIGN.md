# موسوعة الرجال — Design Specification (v3 "Manuscript Warm")

A complete design spec for the Streamlit rijal app. Hand this to a designer (or "claude design")
to iterate further; everything the app renders derives from the tokens and components below.

---

## 1. Design language

**Concept:** a classical Arabic manuscript brought into a modern reading app. Warm parchment
surfaces, deep-ink text, gold reserved for the Imams/sacred, deep-green as the single interactive
accent. Generous line-height for classical text. RTL throughout.

### Tokens (`app/style.css :root`)
| Token | Value | Use |
|---|---|---|
| `--bg` | `#faf7f1` | page background (parchment) |
| `--bg-soft` | `#f1ece2` | quote blocks, pills, inputs |
| `--card` | `#fffdf9` | card surfaces |
| `--line` | `#e7dfd0` | borders |
| `--ink` | `#2b2317` | primary text |
| `--ink-soft` | `#6b5d4a` | secondary text |
| `--gold` | `#b8860b` | Imams / sacred highlights only |
| `--gold-soft` | `#fbf4e2` | Imam node fill |
| `--accent` | `#175d4f` | the ONE interactive color (buttons, links, nav) |
| `--accent-soft` | `#e8f1ee` | hover/selected fills |
| verdict scale | ثقة `#2e7d32` · حسن `#689f38` · موثق `#00897b` · مختلف `#ef6c00` · ضعيف `#c62828` · مجهول `#8d8d8d` · معصوم gold | reliability chips, grade box |
| `--radius` | 14px | cards/tiles |
| `--shadow` | `0 1px 4px rgba(70,55,30,.08)` | all raised surfaces |

### Typography
- **Cairo** (400/600/700/800) — all UI: nav, headings, labels, buttons, chips.
- **Amiri** (serif) — classical text only: book pages (`.r-bookpage`, 1.18rem / line-height 2.15)
  and jarh-ta'dil quotes (`.r-quote`, 1.12rem / 2.1, gold right-border).
- Latin digits everywhere (consistency); Arabic for all words.

## 2. Component inventory (`app/ui.py` → `app/style.css`)
| Component | Class | Purpose |
|---|---|---|
| Card | `.r-card` (+`.flag` amber variant) | profile header, evaluation cards |
| Chip | `.r-chip` (filled verdict color) / `.outline` / `.tab` (tabaqah, green-soft) | verdicts, tabaqah, masum |
| Pill | `.r-pill` | facts (kunya, wafat, counts) |
| Quote | `.r-quote` | Amiri classical quotes w/ gold border |
| Book page | `.r-bookpage` | full-page reader, `<mark>` for search hits |
| Stat | `.r-stat` in `.r-statband` | home statistics band |
| Tile | `.r-tile` | book cards & home feature cards |
| Isnad node | `.isnad-node` (+`.imam` gold / `.unresolved` red border) | one narrator in a chain |
| Isnad connector | `.isnad-conn` (`.ok` ✓ / `.bad` ⚠ / `.warn`) | dashed line + link status between levels |
| Grade box | `.r-grade` | final chain verdict, colored by weakest narrator |
| Flag note | `.r-flagnote` | amber "تقويم غير محسوم" notice |

## 3. Navigation & layout
- **Top `st.segmented_control`** (🏠 الرئيسية · 🔎 الرواة · 📚 الكتب · 🔗 الأسانيد) — always visible,
  works on mobile (unlike sidebar nav). Sidebar holds only stats/about, starts collapsed.
- Max content width 1100px, RTL.
- **Deep links:** `?n=<d_id>` opens a narrator profile, `?book=<book_id>` opens a book. Shareable.
- **Mobile** (`@media max-width:640px`): all `st.columns` stack (`[data-testid="column"]{min-width:100%}`),
  buttons full-width, fonts/padding reduced, isnad nodes stretch full-width.

## 4. Pages (wireframes in words)
1. **Home** — hero title+subtitle → big search (typing replaces page with results list) →
   6-stat band (رواة/تقويم دراية/تقويم الخوئي/طبقات/أسانيد/مداخل) → 3 feature tiles with فتح buttons.
2. **Narrator Library** — radio بحث/تصفّح الكل; results = full-width rows `{emoji verdict} {name} · ط{n}`;
   browse = numbered 50/page with ◀▶. **Profile**: header card (name 1.65rem + chips: masum/Dirayah
   verdict/Khoei verdict/tabaqah-with-span + fact pills + tabaqah source line) → amber flag if the
   evaluation scrape was unresolved → one card per authority (📊 دراية النور, 📗 الخوئي (المفيد)) with
   aggregate + Amiri quote → 5 tabs: الشيوخ والتلاميذ (top-10 rows + عرض الكل expander) / شبكة الرواية
   (graphviz: green teachers ← blue narrator ← orange students) / الموضع الزمني (altair: narrator bar
   vs 12 Imam lifespans) / في الكتب (one expander per book + Mufid) / الأسماء.
3. **Books** — 3-col tile grid (title/author/entries/matched%) → inside: radio التراجم (search +
   expander cards with verdict emoji, ↩ link to profile) / الكتاب كاملاً (vol select, full-text search
   with snippet buttons, page slider + ◀▶, Amiri page card with highlight). ألف رجل = entries-only.
4. **Isnad Analyzer** — tabs: ✍️ free-text (DEFAULT; 3 example buttons fill the textarea → حلّل السند
   primary button → vertical stepper + grade + احتمالات أخرى لتحديد الرواة expander) / 📋 browse (book/narrator/masum
   filters → chain picker → same stepper). Stepper rules: عطف narrators share one level; connector shows
   ✓ الرواية بينهما ثابتة (relation exists) / ⚠ لم تثبت رواية بينهما / ⚠ + تباعد في الطبقات (spans don't overlap ±1);
   final Imam node gold; grade = weakest narrator with the culprit named.

## 5. Data sources shown
- Verdicts: `evaluations` (authority `dirayah3`, 1,993 — 100% scraped from Dirayah, no LLM) +
  Khoei via `mufid_matches.mufid_status` (thiqah/daif/majhul, read-time join, clearly labeled).
- 66 narrators flagged in `eval_flags` (unresolved scrape) → amber note.
- Tabaqah: `narrator_tabaqah` (tabaqa, senior/junior modifier, span low–high, source).
- Books: `book_entries` (21,777 parsed entries) + `book_pages` (11,587 full pages).
- Chains: `chains.levels_json` (183K, عطف-aware) + `relations` for link checks.

## 6. Streamlit constraints (for the designer)
- Buttons can't contain HTML → row chips are emoji+text inside the button label.
- One rerun per click; heavy lookups are `st.cache_data`-cached dicts.
- Native widgets (selectbox/slider/tabs) take theme colors from `.streamlit/config.toml` —
  custom CSS targets `data-testid` attributes and may need updates on Streamlit upgrades.
- Screenshots: run `streamlit run Dirayah3/app/rijal_app.py`, capture at 1280×900 (desktop)
  and 375×812 (mobile) — pages: home, profile (زرارة `?n=D01824`), books reader, isnad example.

## 7. Backlog / ideas for next design iteration
- Dark manuscript mode (ink paper inversion) via CSS `prefers-color-scheme`.
- PWA wrapper for installable mobile app; offline book reader.
- Full-graph explorer (clickable ego-network expansion).
- Tabaqah heat-strip on the browse list; filter library by tabaqah/verdict.
- Compare-two-narrators view; isnad PDF/image export; per-book reading progress.
- Retry the 66 flagged evaluations with معيار-name search.
