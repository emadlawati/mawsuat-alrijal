"""
موسوعة الرجال v3 — Shia narrator encyclopedia & isnad analyzer.
Manuscript-warm design · top navigation · mobile-friendly.
Run:  streamlit run app/rijal_app.py
"""
import os, base64, json as _json
import streamlit as st
import streamlit.components.v1 as _components
import graphviz, pandas as pd, altair as alt
import db, ui

st.set_page_config(page_title="موسوعة الرجال", page_icon="📜", layout="wide",
                   initial_sidebar_state="collapsed")
ui.load_css()

# ---- PWA wiring (installable on phone). Self-contained; to remove: `git revert` this commit. ----
def _inject_pwa():
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        manifest = _json.load(open(os.path.join(here, 'manifest.json'), encoding='utf-8'))
        svg = open(os.path.join(here, 'icon.svg'), encoding='utf-8').read()
    except Exception:
        return
    icon_uri = 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode('utf-8')).decode()
    manifest['icons'] = [{'src': icon_uri, 'sizes': 'any', 'type': 'image/svg+xml', 'purpose': 'any'}]
    man_uri = 'data:application/manifest+json;base64,' + base64.b64encode(
        _json.dumps(manifest, ensure_ascii=False).encode('utf-8')).decode()
    theme = manifest.get('theme_color', '#faf7f1')
    title = manifest.get('short_name', 'موسوعة الرجال')
    _components.html(f"""<script>
    (function() {{
      var d = window.parent.document;
      if (d.getElementById('pwa-meta')) return;
      var m = d.createElement('meta'); m.id = 'pwa-meta'; d.head.appendChild(m);
      function add(tag, attrs) {{
        var el = d.createElement(tag);
        for (var k in attrs) el.setAttribute(k, attrs[k]);
        d.head.appendChild(el);
      }}
      add('link', {{rel: 'manifest', href: '{man_uri}'}});
      add('link', {{rel: 'apple-touch-icon', href: '{icon_uri}'}});
      add('meta', {{name: 'theme-color', content: '{theme}'}});
      add('meta', {{name: 'apple-mobile-web-app-capable', content: 'yes'}});
      add('meta', {{name: 'mobile-web-app-capable', content: 'yes'}});
      add('meta', {{name: 'apple-mobile-web-app-status-bar-style', content: 'default'}});
      add('meta', {{name: 'apple-mobile-web-app-title', content: '{title}'}});
    }})();
    </script>""", height=0)

_inject_pwa()
# ---- end PWA wiring ----

ss = st.session_state
for k, v in [('d_id', None), ('cur_book', None), ('chain_id', None), ('lib_page', 0),
             ('bk_page', None), ('is_res', None)]:
    ss.setdefault(k, v)

NAV = ["🏠 الرئيسية", "🔎 الرواة", "📚 الكتب", "🔗 الأسانيد"]
ss.setdefault('nav', NAV[0])

# ---- deep links (must run before the nav widget) ----
qp = st.query_params
if qp.get('n'):
    ss['d_id'] = qp['n']; ss['nav'] = NAV[1]; st.query_params.clear()
if qp.get('book'):
    ss['cur_book'] = qp['book']; ss['nav'] = NAV[2]; st.query_params.clear()
if 'nav_goto' in ss:
    ss['nav'] = ss.pop('nav_goto')

def goto(section, **state):
    for k, v in state.items(): ss[k] = v
    ss['nav_goto'] = section
    st.rerun()

# ---------------------------------------------------------------- shared renderers
GRADE_RANK = {'معصوم': 5, 'ثقة': 5, 'موثّق': 4, 'حسن/ممدوح': 4, 'مختلف فيه': 2, 'مجهول': 1, 'ضعيف': 0}
GRADE_LABEL = {5: ('صحيح', 'var(--thiqa)'), 4: ('حسن / موثّق', 'var(--hasan)'),
               2: ('مختلف فيه', 'var(--mukhtalaf)'), 1: ('ضعيف فيه جهالة', 'var(--majhul)'),
               0: ('ضعيف', 'var(--daif)')}

def compute_grade(members):
    """members: list of (display_name, verdict_or_None, is_masum). -> (grade, color, why)"""
    worst = None; culprit = None
    for name, verdict, masum in members:
        if masum: continue
        lab = db.reliability(verdict)[0] if verdict else 'مجهول'
        rank = GRADE_RANK.get(lab, 1)
        if worst is None or rank < worst:
            worst, culprit = rank, (name, lab)
    if worst is None: return ('غير معلوم', 'var(--majhul)', '')
    g, col = GRADE_LABEL[worst]
    why = f"بأضعف رواته: {culprit[0]} ({culprit[1]})" if culprit else ''
    return (g, col, why)

def narrator_brief(d_id):
    """(name, verdict, is_masum, tabaqa) with caching via db maps."""
    n = db.narrator(d_id)
    if not n: return None
    v = n['evals'][0]['verdict'] if n['evals'] else None
    t = n['tabaqah']['tabaqa'] if n['tabaqah'] else None
    return (n['standard_name'], v, bool(n['is_masum']), t)

def render_stepper(levels, link_flags=None, chain_counts=None):
    """levels: [[{'d_id','name'}...]] top=author side, bottom=Imam side. Returns members for grading."""
    html = []; members = []
    for i, lvl in enumerate(levels):
        nodes = []
        any_imam = False
        for nar in lvl:
            d = nar.get('d_id')
            note = nar.get('note')  # e.g., '(عمه — تقدير)'
            if d:
                b = narrator_brief(d)
                if b:
                    name, v, masum, tab = b
                    any_imam = any_imam or masum
                    members.append((name, v, masum))
                    nodes.append(ui.isnad_node(nar.get('name') or name, d, v, tab, masum, note=note))
                    continue
            members.append((nar.get('name') or '؟', None, False))
            nodes.append(ui.isnad_node(nar.get('name') or '؟', note=note))
        html.append(ui.isnad_level(nodes, atf=len(lvl) > 1))
        if i < len(levels) - 1:
            status = 'none'; note = ''
            if link_flags is not None and i < len(link_flags):
                ok = link_flags[i]
                if ok: status = 'ok'
                else:
                    status = 'bad'
                    u = lvl[0].get('d_id'); w = levels[i+1][0].get('d_id')
                    if u and w and db.tabaqah_gap(w, u):
                        status, note = 'warn', 'لم تثبت رواية بينهما، مع تباعدٍ في طبقتيهما'
            if chain_counts and i < len(chain_counts):
                cc = chain_counts[i]
            html.append(ui.isnad_conn(status, note, chain_count=cc))
    st.markdown(f"<div>{''.join(html)}</div>", unsafe_allow_html=True)
    g, col, why = compute_grade(members)
    st.markdown(ui.grade_box(g, col, why), unsafe_allow_html=True)

def result_rows(results, key_prefix, limit=30):
    """Search/browse result rows — each opens the profile in a NEW browser tab."""
    vm = db.verdict_map(); tm = db.tab_map()
    html = ''.join(ui.narrator_row(d, name, vm.get(d), tm.get(d)) for d, name in results[:limit])
    st.markdown(html, unsafe_allow_html=True)

# ---------------------------------------------------------------- narrator profile
def render_profile(d_id):
    n = db.narrator(d_id)
    if not n:
        st.warning("لم يُعثر على الراوي."); return
    mufid = db.mufid_eval(d_id)
    flag = db.eval_flag(d_id)

    chips = ''
    if n['is_masum']: chips += ui.chip('🌟 معصوم', 'var(--gold)')
    if n['evals']: chips += ui.verdict_chip(n['evals'][0]['verdict'])
    if mufid: chips += ui.verdict_chip(mufid['verdict_ar'], prefix='الخوئي: ')
    chips += ui.tabaqah_chip(n['tabaqah'])
    pills = ''
    if n['kunya']: pills += ui.pill("الكنية: " + n['kunya'].split(chr(10))[0][:42])
    if n['madhab']: pills += ui.pill("المذهب: " + n['madhab'].split('(')[0][:30])
    if n['wiladat_year']: pills += ui.pill(f"الولادة: {n['wiladat_year']} هـ")
    if n['wafat_year']: pills += ui.pill(f"الوفاة: {n['wafat_year']} هـ")
    if n['chain_count']: pills += ui.pill(f"وروده في الأسانيد: {n['chain_count']}")
    t = n['tabaqah']
    src_line = ''
    if t:
        src = {'alf_rajul': 'كتاب ألف رجل', 'inferred': 'مستنبطة من شبكة الرواة والقرائن',
               'inferred_llm': 'مستنبطة من نصوص التراجم'}.get(t['source'], t['source'])
        src_line = f"<div class='r-sub'>مصدر الطبقة: {src}</div>"
    st.markdown(ui.card(
        f"<span class='r-name'>{n['standard_name']}</span><br>{chips}<br>{pills}{src_line}"
    ), unsafe_allow_html=True)

    if flag:
        st.markdown(ui.flagnote("لم يتيسّر التحقق الآلي من تقويم هذا الراوي في برنامج دراية النور، "
                                f"فيُرجى التحقق منه يدوياً. ({flag['detail']})"), unsafe_allow_html=True)

    # evaluations — show BOTH Dirayah fields: evaluation_result (حصيلة التقويم) + aggregate (جمع التقويم)
    for ev in n['evals']:
        body = ''
        if ev['verdict']: body += f"<b>حصيلة التقويم:</b> {ev['verdict']}<br>"
        if ev['aggregate']: body += f"<b>جمع التقويم:</b> {ev['aggregate']}<br>"
        if ev['jarh_tadil']: body += ui.quote(ev['jarh_tadil'])
        st.markdown(ui.card(f"<b>📊 تقويم دراية النور</b><br>{body}"), unsafe_allow_html=True)
    if mufid:
        body = f"<b>الحكم:</b> {mufid['verdict_ar']}<br>"
        if mufid['text']: body += ui.quote(mufid['text'][:600])
        st.markdown(ui.card(f"<b>📗 الخوئي (المفيد من معجم رجال الحديث)</b><br>{body}"), unsafe_allow_html=True)
    if not n['evals'] and not mufid and not n['is_masum']:
        st.caption("لا يوجد تقويم في دراية النور ولا في المفيد لهذا الراوي.")

    tabs = st.tabs(["🧑‍🏫 الشيوخ والتلاميذ", "🕸️ شبكة الرواية", "📈 الخطّ الزمني", "📚 في الكتب", "📛 الأسماء والألقاب"])
    with tabs[0]:
        c1, c2 = st.columns(2)
        for col, lst, lbl, pre in ((c1, n['teachers'], 'شيوخه (روى عنهم)', 't'),
                                   (c2, n['students'], 'تلاميذه (رَوَوا عنه)', 's')):
            with col:
                st.markdown(f"**{lbl} — {len(lst)}**")
                for x in lst[:10]:
                    if st.button(f"{x['standard_name']}  ({x['chain_count']})",
                                 key=f"{pre}{d_id}{x['d_id']}", use_container_width=True):
                        goto(NAV[1], d_id=x['d_id'])
                if len(lst) > 10:
                    with st.expander(f"عرض الكل ({len(lst)})"):
                        for x in lst[10:60]:
                            if st.button(f"{x['standard_name']}  ({x['chain_count']})",
                                         key=f"x{pre}{d_id}{x['d_id']}", use_container_width=True):
                                goto(NAV[1], d_id=x['d_id'])
    with tabs[1]:
        render_network(d_id)
    with tabs[2]:
        if t: render_timeline(t, n['wafat_year'], n['wiladat_year'])
        else: st.caption("لا توجد طبقة مسجّلة لهذا الراوي.")
    with tabs[3]:
        shown = False
        for b in n['books']:
            shown = True
            with st.expander(f"{db.BOOK_TITLES.get(b['book_id'], b['book_id'])} — ص{b['page'] or '؟'}"):
                st.markdown(ui.quote(b['text'] or '—'), unsafe_allow_html=True)
        if mufid and mufid['text']:
            shown = True
            with st.expander("المفيد من معجم رجال الحديث (الخوئي)"):
                st.markdown(ui.quote(mufid['text']), unsafe_allow_html=True)
        if not shown: st.caption("لا توجد ترجمة مستخرجة في الكتب لهذا الراوي.")
    with tabs[4]:
        st.markdown(" · ".join(n['aliases']) if n['aliases'] else "—")

def render_network(d_id):
    n_each = st.slider("عدد الشيوخ/التلاميذ المعروضين", 5, 80, 25, key=f"net_n_{d_id}")
    nodes, edges = db.network_edges(d_id, max_each=n_each)
    if len(nodes) <= 1:
        st.caption("لا توجد علاقات مسجّلة في الشبكة."); return
    g = graphviz.Digraph(); g.attr(rankdir='RL', bgcolor='transparent', nodesep='0.16', ranksep='0.6'
                                   , size='8,11', ratio='compress')
    g.attr('node', shape='box', style='rounded,filled', fontname='Arial', fontsize='11', margin='0.10,0.04')
    g.attr('edge', color='#bfae8e', arrowsize='0.7')
    col = {'me': '#175d4f', 'teacher': '#2e7d32', 'student': '#ef6c00'}
    fcol = {'me': '#e8f1ee', 'teacher': '#e8f5e9', 'student': '#fff3e0'}
    for nid, (name, role) in nodes.items():
        lbl = name[:28] + ('…' if len(name) > 28 else '')
        g.node(nid, lbl, color=col[role], fillcolor=fcol[role], fontcolor='#2b2317')
    # arrow flows teacher→student (knowledge transmission: «روى عنه»)
    for t, s, cnt in edges: g.edge(t, s)
    st.graphviz_chart(g, use_container_width=True)
    with st.expander("عرض البيانات كقائمة (لمتصفحي الشاشة)"):
        teachers = [(n,d) for n,(_,r) in nodes.items() if r=='teacher']
        students = [(n,d) for n,(_,r) in nodes.items() if r=='student']
        if teachers:
            st.caption(f"الشيوخ ({len(teachers)}):")
            st.markdown(' · '.join(d[:28] for _,d in teachers))
        if students:
            st.caption(f"التلاميذ ({len(students)}):")
            st.markdown(' · '.join(d[:28] for _,d in students))
    st.caption("🟢 شيوخه · 🟦 الراوي · 🟠 تلاميذه — السهم باتجاه «روى عنه» (من الشيخ إلى تلميذه)")

IMAMS = [("النبي ﷺ", -52, 11), ("عليّ ع", -23, 40), ("الحسن ع", 3, 50), ("الحسين ع", 4, 61),
         ("السجاد ع", 38, 95), ("الباقر ع", 57, 114), ("الصادق ع", 83, 148), ("الكاظم ع", 127, 183),
         ("الرضا ع", 148, 203), ("الجواد ع", 195, 220), ("الهادي ع", 212, 254), ("العسكري ع", 232, 260)]
def render_timeline(tb, wafat, wiladat):
    lo, hi = tb['tabaqah_low'], tb['tabaqah_high']
    y0 = wiladat or db.TAB_YEARS[lo][0]; y1 = wafat or db.TAB_YEARS[hi][3]
    rows = [{'من': a, 'إلى': b, 'الاسم': nm, 'نوع': 'إمام'} for nm, a, b in IMAMS]
    rows.append({'من': y0, 'إلى': y1, 'الاسم': '⟵ هذا الراوي', 'نوع': 'الراوي'})
    df = pd.DataFrame(rows); order = [r['الاسم'] for r in rows]
    ch = alt.Chart(df).mark_bar(height=13, cornerRadius=3).encode(
        x=alt.X('من:Q', title='السنة الهجرية', scale=alt.Scale(domain=[-60, 320])), x2='إلى:Q',
        y=alt.Y('الاسم:N', sort=order, title=None),
        color=alt.Color('نوع:N', scale=alt.Scale(domain=['إمام', 'الراوي'], range=['#b8860b', '#175d4f']), legend=None),
        tooltip=['الاسم', 'من', 'إلى']).properties(height=350)
    st.altair_chart(ch, use_container_width=True)
    with st.expander("عرض البيانات كجدول (لمتصفحي الشاشة)"):
        st.dataframe(df[["الاسم","من","إلى"]], use_container_width=True, hide_index=True)
    st.caption(f"الطبقة {db.TAB_AR.get(tb['tabaqa'], tb['tabaqa'])}"
               + (f" (تمتد من الطبقة {lo} إلى {hi})" if hi != lo else "")
               + " — موقع الراوي الزمني مقارنةً بحياة الأئمة عليهم السلام.")

# ---------------------------------------------------------------- pages
def page_home():
    s = db.global_stats()
    st.markdown("<div class='r-hero'><h1>📜 موسوعة الرجال</h1>"
                "<p>قاعدة بيانات رواة الحديث عند الإمامية — التقويم، الطبقات، الكتب، وتحليل الأسانيد</p></div>",
                unsafe_allow_html=True)
    q = st.text_input("ابحث عن راوٍ بالاسم أو الكنية أو اللقب", key="home_q",
                      placeholder="مثال: زرارة بن أعين · محمد بن يعقوب الكليني · أبو بصير")
    if q:
        res = db.search_narrators(q)
        st.caption(f"{len(res)} نتيجة")
        result_rows(res, 'h')
        return
    st.markdown(ui.statband([
        (f"{s['narrators']:,}", "راوياً"), (f"{s['evals']:,}", "تقويم دراية النور"),
        (f"{s['tabaqah']:,}", "راوياً معلوم الطبقة"),
        (f"{s['chains']:,}", "سنداً"), (f"{s['entries']:,}", "ترجمة من {} كتب".format(s['books'])),
    ]), unsafe_allow_html=True)
    st.write("")
    c1, c2, c3 = st.columns(3)
    feats = [(c1, "🔎 مكتبة الرواة", "ترجمة وافية لكل راوٍ: تقويمه، وطبقته، وشيوخه وتلاميذه، وشبكة روايته، وخطّه الزمني.", NAV[1]),
             (c2, "📚 كتب الرجال", "عشرة كتب رجالية كاملة: تصفّح تراجمها، واقرأها صفحةً صفحة، وابحث في نصوصها.", NAV[2]),
             (c3, "🔗 محلّل الأسانيد", "حلّل أي سند تنسخه نصاً، أو تصفّح ١٨٣ ألف سند مستخرج، مع الحكم على السند بأضعف رواته.", NAV[3])]
    for col, title, desc, target in feats:
        with col:
            st.markdown(ui.tile(title, '', desc), unsafe_allow_html=True)
            if st.button("فتح", key=f"feat{target}", use_container_width=True):
                goto(target)

def page_library():
    st.subheader("🔎 مكتبة الرواة")
    mode = st.radio("وضع العرض", ["بحث", "تصفّح الكل"], horizontal=True, key="lib_mode",
                    label_visibility="collapsed")
    if mode == "بحث":
        q = st.text_input("ابحث باسم الراوي أو لقبه أو كنيته", key="lib_q", placeholder="مثال: زرارة بن أعين")
        if q:
            res = db.search_narrators(q)
            st.caption(f"{len(res)} نتيجة")
            result_rows(res, 'r')
    else:
        PER = 50; total = db.narrator_count(); pages = (total + PER - 1) // PER
        c1, c2, c3 = st.columns([1, 2, 1])
        if c1.button("◀ السابق", disabled=ss['lib_page'] <= 0): ss['lib_page'] -= 1; st.rerun()
        c2.markdown(f"<div style='text-align:center'>صفحة {ss['lib_page']+1} من {pages} · {total:,} راوٍ</div>",
                    unsafe_allow_html=True)
        if c3.button("التالي ▶", disabled=ss['lib_page'] >= pages - 1): ss['lib_page'] += 1; st.rerun()
        rows = db.browse_narrators(ss['lib_page'] * PER, PER)
        vm = db.verdict_map()
        html = ''.join(ui.narrator_row(r['d_id'], r['standard_name'], vm.get(r['d_id']),
                                       r['tabaqa'], num=ss['lib_page'] * PER + i + 1)
                       for i, r in enumerate(rows))
        st.markdown(html, unsafe_allow_html=True)
    st.divider()
    if ss['d_id']:
        render_profile(ss['d_id'])
    elif mode == "بحث":
        st.info("ابحث عن راوٍ لعرض ترجمته الكاملة، أو اختر «تصفّح الكل» لاستعراض الرواة جميعاً.")

def page_books():
    st.subheader("📚 كتب الرجال")
    stats = db.book_stats()
    if not ss['cur_book']:
        cols = st.columns(3)
        authors = {'najashi': 'النجاشي (ت450)', 'fihrist_tusi': 'الطوسي (ت460)', 'rijal_tusi': 'الطوسي (ت460)',
                   'kashshi': 'الكشي/الطوسي', 'qamoos_al_rijal': 'التستري', 'khulasa': 'العلامة الحلي (ت726)',
                   'ibn_dawud': 'ابن داود الحلي', 'ibn_ghadairi': 'ابن الغضائري', 'barqi': 'البرقي',
                   'alf_rajul': 'السيد غيث شبر', 'mujam_khoei': 'السيد الخوئي (ت1413)',
                   'wafi_asaneed': 'السيد غيث شبر',
                   'qabasat': 'الشيخ مسلم الداوري'}
        for i, s in enumerate(stats):
            with cols[i % 3]:
                pct = round(100 * s['matched'] / s['total']) if s['total'] else 0
                st.markdown(ui.tile(s['title'], authors.get(s['book_id'], ''),
                                    f"{s['total']:,} ترجمة · {pct}% منها موصولة بقاعدة الرواة"), unsafe_allow_html=True)
                if st.button("تصفّح الكتاب", key=f"bk{s['book_id']}", use_container_width=True):
                    ss['cur_book'] = s['book_id']; ss['bk_page'] = None; st.rerun()
        return
    bid = ss['cur_book']
    title = db.BOOK_TITLES.get(bid, bid)
    c1, c2 = st.columns([4, 1])
    c1.markdown(f"### {title}")
    if c2.button("⬅ كل الكتب"): ss['cur_book'] = None; st.rerun()
    if bid == 'alf_rajul':
        st.caption("كتاب «ألف رجل» مأخوذ كاملاً من قاعدة بيانات تطبيقه — وتراجمه الـ1015 كلّها في «التراجم».")
        views = ["📑 التراجم"]
    else:
        views = ["📑 التراجم", "📖 الكتاب كاملاً"]
    view = st.radio("وضع العرض", views, horizontal=True, key="bk_view", label_visibility="collapsed")
    if view == "📑 التراجم":
        q = st.text_input("ابحث في التراجم", key="bk_q", placeholder="اسم راوٍ أو كلمة في النص")
        if q and q.strip():
            entries = db.book_entries(bid, q)
            st.caption(f"{len(entries)} نتيجة")
        else:
            PER = 100
            total = db.book_entries_count(bid)
            pages = max(1, (total + PER - 1) // PER)
            ss.setdefault('be_page', 0)
            if ss.get('be_book') != bid:           # reset page when switching books
                ss['be_page'] = 0; ss['be_book'] = bid
            p1, p2, p3 = st.columns([1, 2, 1])
            if p1.button("◀ السابق", key="be_prev", disabled=ss['be_page'] <= 0):
                ss['be_page'] -= 1; st.rerun()
            p2.markdown(f"<div style='text-align:center'>صفحة {ss['be_page']+1} من {pages} · {total:,} ترجمة</div>",
                        unsafe_allow_html=True)
            if p3.button("التالي ▶", key="be_next", disabled=ss['be_page'] >= pages - 1):
                ss['be_page'] += 1; st.rerun()
            entries = db.book_entries(bid, '', limit=PER, offset=ss['be_page'] * PER)
        vm = db.verdict_map()
        for e in entries:
            em = db.reliability(vm[e['d_id']])[2] if e['d_id'] in vm else ''
            with st.expander(f"{em} [{e['entry_no']}] {e['headword']} — ص{e['page'] or '؟'}"):
                st.markdown(ui.quote(e['text'] or '—'), unsafe_allow_html=True)
                if e['d_id'] and st.button("↩ عرض ترجمة الراوي الكاملة", key=f"be{e['rowid']}"):
                    goto(NAV[1], d_id=e['d_id'])
    else:
        vols = db.book_vols(bid)
        vol = st.selectbox("الجزء", vols, format_func=lambda v: f"الجزء {v}", key="bk_vol") if len(vols) > 1 else (vols[0] if vols else 1)
        mn, mx, cnt = db.book_page_range(bid, vol)
        toc = db.book_toc(bid, vol)
        if toc:
            opts = ["— فهرس المحتويات —"] + [f"{lbl}  (ص{pg})" for lbl, pg in toc]
            pick = st.selectbox("انتقل إلى باب", opts, key=f"toc_{bid}_{vol}")
            if pick != opts[0]:
                pg = toc[opts.index(pick) - 1][1]
                if ss.get('bk_page') != pg and ss.get('_toc_last') != pick:
                    ss['bk_page'] = pg; ss['_toc_last'] = pick; st.rerun()
        sq = st.text_input("بحث في نصّ الكتاب كاملاً", key="bk_fts", placeholder="كلمة أو عبارة")
        if sq:
            hits = db.book_pages_search(bid, sq)
            st.caption(f"{len(hits)} موضع")
            for v, p, snip in hits[:25]:
                if st.button(f"ج{v} ص{p}:  {snip}", key=f"fp{v}_{p}", use_container_width=True):
                    ss['bk_page'] = p; st.rerun()
        page = ss['bk_page'] if (ss['bk_page'] and mn <= ss['bk_page'] <= mx) else mn
        c1, c2, c3 = st.columns([1, 3, 1])
        if c1.button("◀ السابقة", disabled=page <= mn): ss['bk_page'] = page - 1; st.rerun()
        newp = c2.slider("الصفحة", mn, mx, page, key="bk_slider", label_visibility="collapsed")
        if newp != page: ss['bk_page'] = newp; st.rerun()
        if c3.button("التالية ▶", disabled=page >= mx): ss['bk_page'] = page + 1; st.rerun()
        txt = db.book_page(bid, vol, page) or '—'
        if sq and sq.strip() and sq in txt:
            txt = txt.replace(sq, f"<mark>{sq}</mark>")
        st.markdown(f"<div class='r-sub' style='text-align:center'>صفحة {page} من {mx}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='r-bookpage'>{txt.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

EXAMPLES = [
    "محمد بن يعقوب عن علي بن إبراهيم عن أبيه عن ابن أبي عمير عن حماد بن عيسى عن حريز عن زرارة عن أبي جعفر",
    "محمد بن يعقوب عن علي بن إبراهيم عن أبيه عن حماد بن عيسى عن حريز عن زرارة عن أبي عبد الله",
    "محمد بن الحسن الطوسي عن المفيد عن الصدوق عن أبيه عن سعد بن عبد الله عن أحمد بن محمد بن عيسى",
]
def page_isnad():
    st.subheader("🔗 محلّل الأسانيد")
    t1, t2 = st.tabs(["✍️ تحليل سند منسوخ", "📋 تصفّح الأسانيد"])
    with t1:
        st.caption("انسخ السند كما ورد في الكتاب، وسيُحدَّد كل راوٍ فيه ويُحكم على السند بأضعف رواته.")
        ec = st.columns(len(EXAMPLES))
        for i, ex in enumerate(EXAMPLES):
            if ec[i].button(f"مثال {i+1}", key=f"ex{i}", use_container_width=True):
                ss['is_txt'] = ex; ss['is_res'] = None; st.rerun()
        txt = st.text_area("نصّ السند", key="is_txt", height=110,
                           placeholder="محمد بن يعقوب عن علي بن إبراهيم عن أبيه …")
        if st.button("🔍 حلّل السند", type="primary", use_container_width=True) and txt.strip():
            with st.spinner("جارٍ تحليل السند…"):
                ss['is_res'] = db.resolve_isnad(txt)
        if ss.get('is_res'):
            res = ss['is_res']
            levels = [[{'d_id': r['d_id'], 'name': r['name'], 'note': r.get('note')}] for r in res]
            flags = [bool(res[i+1]['link_ok']) for i in range(len(res) - 1)]
            cc_list = [res[i+1].get('chain_count', 0) for i in range(len(res) - 1)]
            render_stepper(levels, flags, chain_counts=cc_list)
            with st.expander("احتمالات أخرى لتحديد الرواة (إن أخطأ التحديد)"):
                for r in res:
                    alts = " · ".join(n for _, n in (r['alts'] or [])[:4])
                    st.markdown(f"**{r['segment']}** ← {r['name']}  <span class='r-sub'>(احتمالات أخرى: {alts})</span>",
                                unsafe_allow_html=True)
    with t2:
        c1, c2, c3 = st.columns([2, 2, 1])
        books = ['(كل الكتب)'] + db.chain_books()
        bk = c1.selectbox("الكتاب", books, key="ch_book")
        nq = c2.text_input("ابحث عن راوٍ في الأسانيد", key="ch_nar", placeholder="اكتب اسم الراوي ثم اختر")
        masum = c3.checkbox("ينتهي بمعصوم", value=True, key="ch_masum")
        nar_did = None
        if nq:
            hits = db.search_narrators(nq, limit=8)
            if hits:
                pick = st.selectbox("اختر الراوي", hits, format_func=lambda x: x[1], key="ch_pick_nar")
                nar_did = pick[0]
        chains = db.search_chains(narrator_did=nar_did, masum_only=masum, limit=300)
        if not bk.startswith('('): chains = [c for c in chains if c['book_name'] == bk]
        chains = chains[:80]
        st.caption(f"{len(chains)} سند")
        opts = {f"#{c['chain_id']} — {c['book_name']} ص{c['start_page']} ({c['narrator_count']} راوٍ)": c['chain_id'] for c in chains}
        if opts:
            sel = st.selectbox("اختر سنداً", list(opts), key="ch_pick")
            ss['chain_id'] = opts[sel]
        if ss['chain_id']:
            ch = db.chain_detail(ss['chain_id'])
            if ch:
                st.markdown(f"<span class='r-sub'>{ch['book_name']} — ج{ch.get('vol') or ''} "
                            f"ص{ch.get('start_page') or ''} · {ch['narrator_count']} راوٍ · {ch['level_count']} طبقة</span>",
                            unsafe_allow_html=True)
                flags = db.chain_links(ch['levels'])
                render_stepper(ch['levels'], flags)

# ---------------------------------------------------------------- nav + sidebar
nav = st.segmented_control("التنقل", NAV, key="nav", label_visibility="collapsed") or NAV[0]

with st.sidebar:
    st.markdown("## 📜 موسوعة الرجال")
    s = db.global_stats()
    st.caption(f"{s['narrators']:,} راوٍ · {s['books']} كتب · {s['chains']:,} سند\n\n"
               f"التقويم: {s['evals']:,} راوياً (دراية النور)\n\n"
               f"الطبقات: {s['tabaqah']:,} راوياً")
    st.divider()
    st.caption("المصادر: دراية النور ٣ (CRCIS) · كتب الرجال العشرة · ألف رجل")

{NAV[0]: page_home, NAV[1]: page_library, NAV[2]: page_books, NAV[3]: page_isnad}[nav]()
