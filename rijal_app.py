"""
موسوعة الرجال v3 — Shia narrator encyclopedia & isnad analyzer.
Manuscript-warm design · top navigation · mobile-friendly.
Run:  streamlit run app/rijal_app.py
"""
import os, base64, json as _json
import streamlit as st
import streamlit.components.v1 as _components
import graphviz, pandas as pd, altair as alt
import db, ui, i18n

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
             ('bk_page', None), ('is_res', None), ('study', None), ('lang', 'ar')]:
    ss.setdefault(k, v)

# NAV holds stable internal ids; display labels are localized via i18n ('nav.<id>').
NAV = ['home', 'narrators', 'books', 'isnad', 'atlas', 'studies']
ss.setdefault('nav', NAV[0])

# ---- deep links (must run before the nav widget) ----
# Consumed ONCE per browser session: link clicks reload the page (fresh session), while in-app
# navigation keeps the session — so a stale URL never drags the user back. The URL itself is
# kept in sync with the current location at the end of the script (shareable deep links).
qp = st.query_params
if not ss.get('_qp_consumed'):
    ss['_qp_consumed'] = True
    if qp.get('n'):
        ss['d_id'] = qp['n']; ss['nav'] = NAV[1]
    if qp.get('book'):
        ss['cur_book'] = qp['book']; ss['nav'] = NAV[2]
        if qp.get('p'):
            try: ss['bk_page'] = int(qp['p']); ss['bk_view'] = 'full'
            except ValueError: pass
    if qp.get('s'):
        ss['study'] = qp['s']; ss['nav'] = NAV[5]
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
    if worst is None: return (i18n.chain_grade('غير معلوم'), 'var(--majhul)', '')
    g, col = GRADE_LABEL[worst]
    why = i18n.t('st.why', name=i18n.disp_name(culprit[0], html=True),
                 lab=i18n.grade_label(culprit[1])) if culprit else ''
    return (i18n.chain_grade(g), col, why)

def narrator_brief(d_id):
    """(name, verdict, is_masum, tabaqa) from cached maps — light enough for per-node stepper use."""
    bm = db.brief_map().get(d_id)
    if not bm: return None
    name, masum = bm
    return (name, db.verdict_map().get(d_id), masum, db.tab_map().get(d_id))

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
            status = 'none'; note = ''; cc = 0
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
        st.warning(i18n.t('p.notfound')); return
    if st.button(i18n.t('p.back'), key=f"back_{d_id}"):
        ss['d_id'] = None; st.rerun()
    flag = db.eval_flag(d_id)

    chips = ''
    if n['is_masum']: chips += ui.chip(i18n.t('p.masum'), 'var(--gold)')
    if n['evals']: chips += ui.verdict_chip(n['evals'][0]['verdict'])
    chips += ui.tabaqah_chip(n['tabaqah'])
    pills = ''
    if n['kunya']:
        kunya = n['kunya'].split(chr(10))[0]
        # the field can carry a parenthetical source citation; drop it before transliterating in EN
        kunya = (kunya.split('(')[0].strip() if i18n.is_en() else kunya)[:42]
        pills += ui.pill(i18n.t('p.kunya', v=i18n.disp_name(kunya, html=True)))
    if n['madhab']: pills += ui.pill(i18n.t('p.madhab', v=i18n.madhab_label(n['madhab'].split('(')[0][:30])))
    if n['wiladat_year']: pills += ui.pill(i18n.t('p.born', v=n['wiladat_year']))
    if n['wafat_year']: pills += ui.pill(i18n.t('p.died', v=n['wafat_year']))
    if n['chain_count']: pills += ui.pill(i18n.t('p.chains', v=n['chain_count']))
    t = n['tabaqah']
    src_line = ''
    if t:
        src = i18n.TAB_SRC_EN.get(t['source'], t['source']) if i18n.is_en() else \
              {'alf_rajul': 'كتاب ألف رجل', 'inferred': 'مستنبطة من شبكة الرواة والقرائن',
               'inferred_llm': 'مستنبطة من نصوص التراجم'}.get(t['source'], t['source'])
        src_line = f"<div class='r-sub'>{i18n.t('p.tabsrc', v=src)}</div>"
    st.markdown(ui.card(
        f"<span class='r-name'>{i18n.disp_name(n['standard_name'], html=True)}</span><br>{chips}<br>{pills}{src_line}"
    ), unsafe_allow_html=True)

    if flag:
        st.markdown(ui.flagnote(i18n.t('p.flag', v=flag['detail'])), unsafe_allow_html=True)

    # evaluations — verbatim Dirayah fields (verdict text stays Arabic): evaluation_result + aggregate
    for ev in n['evals']:
        body = ''
        if ev['verdict']: body += f"<b>{i18n.t('p.eval.result')}</b> <span class='r-arabic'>{ev['verdict']}</span><br>"
        if ev['aggregate']: body += f"<b>{i18n.t('p.eval.aggregate')}</b> <span class='r-arabic'>{ev['aggregate']}</span><br>"
        if ev['jarh_tadil']: body += ui.quote(ev['jarh_tadil'])
        st.markdown(ui.card(f"<b>{i18n.t('p.eval.title')}</b><br>{body}"), unsafe_allow_html=True)
    if not n['evals'] and not n['is_masum']:
        st.caption(i18n.t('p.eval.none'))

    # official per-chain grading rollup (Dirayah SanadEvaluation)
    ng = db.narrator_grading(d_id)
    if ng and ng['total']:
        gt = ng['total']
        parts = []
        for arlbl, key, col in (("صحيح", 'sahih', 'var(--thiqa)'), ("موثق/معتبر", 'muwathaq', 'var(--muwathaq)'),
                                ("ضعيف بجهالة", 'daif_jahala', 'var(--majhul)'), ("ضعيف", 'daif', 'var(--daif)')):
            v = ng[key] or 0
            lbl = i18n.OFFICIAL_GRADE_EN[arlbl] if i18n.is_en() else arlbl
            if v: parts.append(f"<span style='color:{col};font-weight:700'>{lbl} {100*v/gt:.0f}%</span> <span class='r-sub'>({v:,})</span>")
        imams = ' · '.join(f"{i18n.imam_name(nm.replace(' عليه السلام','').replace(' عليها السلام',''))} <span class='r-sub'>({c:,})</span>"
                           for nm, c in (ng['top_imams'] or [])[:3])
        body = i18n.t('p.grading.body', n=f'{gt:,}') + ' · '.join(parts)
        if imams: body += f"<br><b>{i18n.t('p.grading.imams')}</b> {imams}"
        st.markdown(ui.card(f"<b>{i18n.t('p.grading.title')}</b><br>{body}"), unsafe_allow_html=True)

    tabs = st.tabs([i18n.t('p.tab.teachers'), i18n.t('p.tab.network'), i18n.t('p.tab.timeline'),
                    i18n.t('p.tab.books'), i18n.t('p.tab.aliases')])
    with tabs[0]:
        c1, c2 = st.columns(2)
        for col, lst, lbl, pre in ((c1, n['teachers'], i18n.t('p.teachers', n=len(n['teachers'])), 't'),
                                   (c2, n['students'], i18n.t('p.students', n=len(n['students'])), 's')):
            with col:
                st.markdown(f"**{lbl}**")
                for x in lst[:10]:
                    if st.button(f"{i18n.disp_name(x['standard_name'])}  ({x['chain_count']})",
                                 key=f"{pre}{d_id}{x['d_id']}", use_container_width=True):
                        goto(NAV[1], d_id=x['d_id'])
                if len(lst) > 10:
                    with st.expander(i18n.t('p.showall', n=len(lst))):
                        for x in lst[10:60]:
                            if st.button(f"{i18n.disp_name(x['standard_name'])}  ({x['chain_count']})",
                                         key=f"x{pre}{d_id}{x['d_id']}", use_container_width=True):
                                goto(NAV[1], d_id=x['d_id'])
    with tabs[1]:
        render_network(d_id)
    with tabs[2]:
        if t: render_timeline(t, n['wafat_year'], n['wiladat_year'])
        else: st.caption(i18n.t('p.notab'))
    with tabs[3]:
        shown = False
        for b in n['books']:
            shown = True
            loc = i18n.pglabel(b['page'])
            if b.get('bio_page'):                       # dual reference: our edition + Dirayah's
                vv = str(b.get('bio_vol') or '')
                vtxt = ((f"v{vv} " if i18n.is_en() else f"ج{vv} ") if vv not in ('', '1') else '')
                loc += ' · ' + i18n.t('p.dirloc', v=vtxt, p=b['bio_page'])
            with st.expander(f"{i18n.book_title(b['book_id'])} — {loc}"):
                st.markdown(ui.quote(db.linkify(b['text'], d_id) if b['text'] else '—'),
                            unsafe_allow_html=True)
        if not shown: st.caption(i18n.t('p.nobooktext'))
        # authoritative Dirayah bio-location index — additional rijāl books (location only, no full text yet)
        nbks = db.narrator_books(d_id)
        have = {b['book_id'] for b in n['books']}
        extra = [x for x in nbks if not (x['has_text'] and x['book_code'] in have)]
        if extra:
            vword = 'v' if i18n.is_en() else 'ج'
            def loc(x):
                v = f"{vword}{x['vol']} " if x['vol'] and str(x['vol']) not in ('', '1') else ''
                pg = i18n.pglabel(x['page']) if x['page'] else ''
                nm = i18n.book_loc_name(x['book_code'], x['book_name'])
                return (f"{nm}" + (f" — {v}{pg}" if (v or pg) else '')).strip()
            st.markdown(
                f"<div class='r-sub' style='margin-top:8px'>{i18n.t('p.alsoin')}<br>"
                + " · ".join(loc(x) for x in extra) + "</div>", unsafe_allow_html=True)
    with tabs[4]:
        if n['aliases']:
            st.markdown(" · ".join(i18n.disp_name(a, html=True) for a in n['aliases']), unsafe_allow_html=True)
        else:
            st.markdown("—")

def render_network(d_id):
    n_each = st.slider(i18n.t('net.slider'), 5, 80, 25, key=f"net_n_{d_id}")
    nodes, edges = db.network_edges(d_id, max_each=n_each)
    if len(nodes) <= 1:
        st.caption(i18n.t('net.none')); return
    g = graphviz.Digraph(); g.attr(rankdir='RL', bgcolor='transparent', nodesep='0.16', ranksep='0.6'
                                   , size='8,11', ratio='compress')
    g.attr('node', shape='box', style='rounded,filled', fontname='Arial', fontsize='11', margin='0.10,0.04')
    g.attr('edge', color='#bfae8e', arrowsize='0.7')
    col = {'me': '#175d4f', 'teacher': '#2e7d32', 'student': '#ef6c00'}
    fcol = {'me': '#e8f1ee', 'teacher': '#e8f5e9', 'student': '#fff3e0'}
    for nid, (name, role) in nodes.items():
        dn = i18n.translit.translit_name(name) if i18n.is_en() else name
        lbl = dn[:32] + ('…' if len(dn) > 32 else '')
        g.node(nid, lbl, color=col[role], fillcolor=fcol[role], fontcolor='#2b2317')
    # arrow flows teacher→student (knowledge transmission: «روى عنه»)
    for t, s, cnt in edges: g.edge(t, s)
    st.graphviz_chart(g, use_container_width=True)
    with st.expander(i18n.t('net.aslist')):
        teachers = [(n,name) for n,(name,r) in nodes.items() if r=='teacher']
        students = [(n,name) for n,(name,r) in nodes.items() if r=='student']
        if teachers:
            st.caption(i18n.t('net.teachers', n=len(teachers)))
            st.markdown(' · '.join(i18n.disp_name(d) for _,d in teachers))
        if students:
            st.caption(i18n.t('net.students', n=len(students)))
            st.markdown(' · '.join(i18n.disp_name(d) for _,d in students))
    st.caption(i18n.t('net.legend'))

IMAMS = [("النبي ﷺ", -52, 11), ("عليّ ع", -23, 40), ("الحسن ع", 3, 50), ("الحسين ع", 4, 61),
         ("السجاد ع", 38, 95), ("الباقر ع", 57, 114), ("الصادق ع", 83, 148), ("الكاظم ع", 127, 183),
         ("الرضا ع", 148, 203), ("الجواد ع", 195, 220), ("الهادي ع", 212, 254), ("العسكري ع", 232, 260)]
def render_timeline(tb, wafat, wiladat):
    lo, hi = tb['tabaqah_low'], tb['tabaqah_high']
    y0 = wiladat or db.TAB_YEARS[lo][0]; y1 = wafat or db.TAB_YEARS[hi][3]
    imam_kind = i18n.t('tl.kind.imam'); nar_kind = i18n.t('tl.kind.nar')
    rows = [{'from': a, 'to': b, 'name': i18n.imam_name(nm), 'kind': imam_kind} for nm, a, b in IMAMS]
    rows.append({'from': y0, 'to': y1, 'name': i18n.t('tl.thisnar'), 'kind': nar_kind})
    df = pd.DataFrame(rows); order = [r['name'] for r in rows]
    cf, ct, cn = i18n.t('tl.col.from'), i18n.t('tl.col.to'), i18n.t('tl.col.name')
    ch = alt.Chart(df).mark_bar(height=13, cornerRadius=3).encode(
        x=alt.X('from:Q', title=i18n.t('tl.year'), scale=alt.Scale(domain=[-60, 320])), x2='to:Q',
        y=alt.Y('name:N', sort=order, title=None),
        color=alt.Color('kind:N', scale=alt.Scale(domain=[imam_kind, nar_kind], range=['#b8860b', '#175d4f']), legend=None),
        tooltip=[alt.Tooltip('name:N', title=cn), alt.Tooltip('from:Q', title=cf),
                 alt.Tooltip('to:Q', title=ct)]).properties(height=350)
    st.altair_chart(ch, use_container_width=True)
    with st.expander(i18n.t('tl.astable')):
        show = df[["name", "from", "to"]].rename(columns={"name": cn, "from": cf, "to": ct})
        st.dataframe(show, use_container_width=True, hide_index=True)
    span = i18n.t('tl.span', lo=lo, hi=hi) if hi != lo else ''
    st.caption(i18n.t('tl.caption', tab=i18n.tab_name(tb['tabaqa']), span=span))

# ---------------------------------------------------------------- pages
def page_home():
    s = db.global_stats()
    st.markdown(f"<div class='r-hero'><h1>{i18n.t('home.title')}</h1>"
                f"<p>{i18n.t('home.subtitle')}</p></div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='r-intro'>"
        f"<div>{i18n.t('home.intro1', n=format(s['narrators'], ','))}</div>"
        f"<div>{i18n.t('home.intro2')}</div>"
        f"<div>{i18n.t('home.intro3')}</div>"
        f"<div>{i18n.t('home.intro4')}</div>"
        "</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='r-verify'>{i18n.t('home.verify')}</div>", unsafe_allow_html=True)
    q = st.text_input(i18n.t('home.search'), key="home_q", placeholder=i18n.t('home.search.ph'))
    if q:
        res = db.search_narrators(q)
        st.caption(i18n.t('home.nresults', n=len(res)))
        result_rows(res, 'h')
        hits = db.search_book_texts(q)                  # omnibox: also search the book texts
        if hits:
            st.markdown(f"**{i18n.t('home.sec.texts')}**")
            html = ''
            for h in hits:
                lbl = f"{i18n.book_title(h['book_id'])} — {i18n.disp_name(h['headword'], html=True)} ({i18n.pglabel(h['page'])})"
                href = f"?n={h['d_id']}" if h['d_id'] else f"?book={h['book_id']}"
                html += f"<a class='r-row' href='{href}'><span class='nm2'>📖 {lbl}</span></a>"
            st.markdown(html, unsafe_allow_html=True)
        return
    st.markdown(ui.statband([
        (f"{s['narrators']:,}", i18n.t('home.stat.narrators')), (f"{s['evals']:,}", i18n.t('home.stat.evals')),
        (f"{s['tabaqah']:,}", i18n.t('home.stat.tabaqah')),
        (f"{s['chains']:,}", i18n.t('home.stat.chains')),
        (f"{s['entries']:,}", i18n.t('home.stat.entries', n=s['books'])),
    ]), unsafe_allow_html=True)
    st.write("")
    c1, c2, c3 = st.columns(3)
    feats = [(c1, i18n.t('home.feat1.t'), i18n.t('home.feat1.d'), NAV[1]),
             (c2, i18n.t('home.feat2.t'), i18n.t('home.feat2.d'), NAV[2]),
             (c3, i18n.t('home.feat3.t'), i18n.t('home.feat3.d'), NAV[3])]
    for col, title, desc, target in feats:
        with col:
            st.markdown(ui.tile(title, '', desc), unsafe_allow_html=True)
            if st.button(i18n.t('home.open'), key=f"feat{target}", use_container_width=True):
                goto(target)

def page_library():
    st.subheader(i18n.t('lib.title'))
    MODES = ['search', 'browse']
    mode = st.radio("mode", MODES, horizontal=True, key="lib_mode", label_visibility="collapsed",
                    format_func=lambda m: i18n.t('lib.mode.search') if m == 'search' else i18n.t('lib.mode.browse'))
    if mode == 'search':
        q = st.text_input(i18n.t('lib.search'), key="lib_q", placeholder=i18n.t('lib.search.ph'))
        if q:
            res = db.search_narrators(q)
            st.caption(i18n.t('home.nresults', n=len(res)))
            result_rows(res, 'r')
    else:
        PER = 50; total = db.narrator_count(); pages = (total + PER - 1) // PER
        c1, c2, c3 = st.columns([1, 2, 1])
        if c1.button(i18n.t('lib.prev'), disabled=ss['lib_page'] <= 0): ss['lib_page'] -= 1; st.rerun()
        c2.markdown(f"<div style='text-align:center'>{i18n.t('lib.page', p=ss['lib_page']+1, n=pages, t=f'{total:,}')}</div>",
                    unsafe_allow_html=True)
        if c3.button(i18n.t('lib.next'), disabled=ss['lib_page'] >= pages - 1): ss['lib_page'] += 1; st.rerun()
        rows = db.browse_narrators(ss['lib_page'] * PER, PER)
        vm = db.verdict_map()
        html = ''.join(ui.narrator_row(r['d_id'], r['standard_name'], vm.get(r['d_id']),
                                       r['tabaqa'], num=ss['lib_page'] * PER + i + 1)
                       for i, r in enumerate(rows))
        st.markdown(html, unsafe_allow_html=True)
    st.divider()
    if ss['d_id']:
        render_profile(ss['d_id'])
    elif mode == 'search':
        st.info(i18n.t('lib.hint'))

def page_books():
    st.subheader(i18n.t('bk.title'))
    stats = db.book_stats()
    if not ss['cur_book']:
        cols = st.columns(3)
        authors = {'najashi': 'النجاشي (ت450)', 'fihrist_tusi': 'الطوسي (ت460)', 'rijal_tusi': 'الطوسي (ت460)',
                   'kashshi': 'الكشي/الطوسي', 'qamoos_al_rijal': 'التستري', 'khulasa': 'العلامة الحلي (ت726)',
                   'ibn_dawud': 'ابن داود الحلي', 'ibn_ghadairi': 'ابن الغضائري', 'barqi': 'البرقي',
                   'alf_rajul': 'السيد غيث شبر', 'mujam_khoei': 'السيد الخوئي (ت1413)',
                   'wafi_asaneed': 'السيد غيث شبر',
                   'qabasat': 'الشيخ مسلم الداوري',
                   'mufid_mujam': 'الشيخ محمد الجواهري'}
        for i, s in enumerate(stats):
            with cols[i % 3]:
                pct = round(100 * s['matched'] / s['total']) if s['total'] else 0
                author = i18n.BOOK_AUTHOR_EN.get(s['book_id'], '') if i18n.is_en() else authors.get(s['book_id'], '')
                st.markdown(ui.tile(i18n.book_title(s['book_id']), author,
                                    i18n.t('bk.tilemeta', n=f"{s['total']:,}", p=pct)), unsafe_allow_html=True)
                if st.button(i18n.t('bk.browse'), key=f"bk{s['book_id']}", use_container_width=True):
                    ss['cur_book'] = s['book_id']; ss['bk_page'] = None; st.rerun()
        return
    bid = ss['cur_book']
    c1, c2 = st.columns([4, 1])
    c1.markdown(f"### {i18n.book_title(bid)}")
    if c2.button(i18n.t('bk.allbooks')): ss['cur_book'] = None; st.rerun()
    VIEWS = ['bios'] if bid == 'alf_rajul' else ['bios', 'full']
    if bid == 'alf_rajul':
        st.caption(i18n.t('bk.alf'))
    view = st.radio("view", VIEWS, horizontal=True, key="bk_view", label_visibility="collapsed",
                    format_func=lambda v: i18n.t('bk.view.bios') if v == 'bios' else i18n.t('bk.view.full'))
    if view == 'bios':
        q = st.text_input(i18n.t('bk.search.bios'), key="bk_q", placeholder=i18n.t('bk.search.bios.ph'))
        if q and q.strip():
            entries = db.book_entries(bid, q)
            st.caption(i18n.t('bk.nresults', n=len(entries)))
        else:
            PER = 100
            total = db.book_entries_count(bid)
            pages = max(1, (total + PER - 1) // PER)
            ss.setdefault('be_page', 0)
            if ss.get('be_book') != bid:           # reset page when switching books
                ss['be_page'] = 0; ss['be_book'] = bid
            p1, p2, p3 = st.columns([1, 2, 1])
            if p1.button(i18n.t('lib.prev'), key="be_prev", disabled=ss['be_page'] <= 0):
                ss['be_page'] -= 1; st.rerun()
            p2.markdown(f"<div style='text-align:center'>{i18n.t('bk.page', p=ss['be_page']+1, n=pages, t=f'{total:,}')}</div>",
                        unsafe_allow_html=True)
            if p3.button(i18n.t('lib.next'), key="be_next", disabled=ss['be_page'] >= pages - 1):
                ss['be_page'] += 1; st.rerun()
            entries = db.book_entries(bid, '', limit=PER, offset=ss['be_page'] * PER)
        vm = db.verdict_map()
        vols = db.book_vols(bid)
        for e in entries:
            em = db.reliability(vm[e['d_id']])[2] if e['d_id'] in vm else ''
            loc = i18n.pglabel(e['page'])
            if e.get('bio_page'):                       # dual reference: our edition + Dirayah's
                vv = str(e.get('bio_vol') or '')
                vtxt = ((f"v{vv} " if i18n.is_en() else f"ج{vv} ") if vv not in ('', '1') else '')
                loc += ' · ' + i18n.t('p.dirloc', v=vtxt, p=e['bio_page'])
            with st.expander(f"{em} [{e['entry_no']}] {i18n.disp_name(e['headword'])} — {loc}"):
                st.markdown(ui.quote(db.linkify(e['text'], e['d_id']) if e['text'] else '—'),
                            unsafe_allow_html=True)
                bc1, bc2 = st.columns(2)
                if e['d_id'] and bc1.button(i18n.t('bk.entry.full'), key=f"be{e['rowid']}"):
                    goto(NAV[1], d_id=e['d_id'])
                can_jump = 'full' in VIEWS and e['page'] and (len(vols) <= 1 or e.get('bio_vol'))
                if can_jump and bc2.button(i18n.t('bk.openpage'), key=f"bp{e['rowid']}"):
                    ss['bk_view'] = 'full'
                    ss['bk_page'] = int(e['page'])
                    if len(vols) > 1 and e.get('bio_vol'):
                        try: ss['bk_vol'] = int(e['bio_vol'])
                        except (TypeError, ValueError): pass
                    st.rerun()
    else:
        vols = db.book_vols(bid)
        vol = st.selectbox(i18n.t('bk.vol.label'), vols, format_func=lambda v: i18n.t('bk.vol', v=v), key="bk_vol") if len(vols) > 1 else (vols[0] if vols else 1)
        mn, mx, cnt = db.book_page_range(bid, vol)
        toc = db.book_toc(bid, vol)
        if toc:
            opts = [i18n.t('bk.toc.head')] + [f"{lbl}  ({i18n.pglabel(pg)})" for lbl, pg in toc]
            pick = st.selectbox(i18n.t('bk.toc.goto'), opts, key=f"toc_{bid}_{vol}")
            if pick != opts[0]:
                pg = toc[opts.index(pick) - 1][1]
                if ss.get('bk_page') != pg and ss.get('_toc_last') != pick:
                    ss['bk_page'] = pg; ss['_toc_last'] = pick; st.rerun()
        sq = st.text_input(i18n.t('bk.fts'), key="bk_fts", placeholder=i18n.t('bk.fts.ph'))
        if sq:
            hits = db.book_pages_search(bid, sq)
            st.caption(i18n.t('bk.nhits', n=len(hits)))
            for v, p, snip in hits[:25]:
                if st.button(f"{i18n.t('bk.loc', v=v, p=p)}:  {snip}", key=f"fp{v}_{p}", use_container_width=True):
                    ss['bk_page'] = p; st.rerun()
        page = ss['bk_page'] if (ss['bk_page'] and mn <= ss['bk_page'] <= mx) else mn
        c1, c2, c3 = st.columns([1, 3, 1])
        if c1.button(i18n.t('bk.prevpage'), disabled=page <= mn): ss['bk_page'] = page - 1; st.rerun()
        # page-keyed number input: recreated whenever the page changes elsewhere (TOC/FTS/entry
        # jumps), so it never fights the current page the way a statically-keyed slider does
        newp = c2.number_input(i18n.t('bk.pageword'), mn, mx, page, key=f"bknum_{bid}_{vol}_{page}",
                               label_visibility="collapsed")
        if newp != page: ss['bk_page'] = int(newp); st.rerun()
        if c3.button(i18n.t('bk.nextpage'), disabled=page >= mx): ss['bk_page'] = page + 1; st.rerun()
        txt = db.book_page(bid, vol, page) or '—'
        if sq and sq.strip() and sq in txt:
            txt = txt.replace(sq, f"<mark>{sq}</mark>")
        st.markdown(f"<div class='r-sub' style='text-align:center'>{i18n.t('bk.pageof', p=page, n=mx)}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='r-bookpage'>{txt.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

EXAMPLES = [
    "محمد بن يعقوب عن علي بن إبراهيم عن أبيه عن ابن أبي عمير عن حماد بن عيسى عن حريز عن زرارة عن أبي جعفر",
    "محمد بن يعقوب عن علي بن إبراهيم عن أبيه عن حماد بن عيسى عن حريز عن زرارة عن أبي عبد الله",
    "محمد بن الحسن الطوسي عن المفيد عن الصدوق عن أبيه عن سعد بن عبد الله عن أحمد بن محمد بن عيسى",
]
def page_isnad():
    st.subheader(i18n.t('is.title'))
    st.caption(i18n.t('is.caption'))
    ec = st.columns(len(EXAMPLES))
    for i, ex in enumerate(EXAMPLES):
        if ec[i].button(i18n.t('is.example', n=i+1), key=f"ex{i}", use_container_width=True):
            ss['is_txt'] = ex; ss['is_res'] = None; st.rerun()
    txt = st.text_area(i18n.t('is.text'), key="is_txt", height=110, placeholder=i18n.t('is.text.ph'))
    if st.button(i18n.t('is.analyze'), type="primary", use_container_width=True) and txt.strip():
        with st.spinner(i18n.t('is.spinner')):
            ss['is_res'] = db.resolve_isnad(txt)
    if ss.get('is_res'):
        res = ss['is_res']
        levels = [[{'d_id': r['d_id'], 'name': r['name'], 'note': r.get('note')}] for r in res]
        flags = [bool(res[i+1]['link_ok']) for i in range(len(res) - 1)]
        cc_list = [res[i+1].get('chain_count', 0) for i in range(len(res) - 1)]
        render_stepper(levels, flags, chain_counts=cc_list)
        with st.expander(i18n.t('is.alts')):
            for r in res:
                alts = " · ".join(i18n.disp_name(n) for _, n in (r['alts'] or [])[:4])
                st.markdown(f"**{i18n.disp_name(r['segment'], html=True)}** ← {i18n.disp_name(r['name'], html=True)}  "
                            f"<span class='r-sub'>{i18n.t('is.altsline', alts=alts)}</span>",
                            unsafe_allow_html=True)

# ---------------------------------------------------------------- studies
_STUDY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'studies')
_STUDY_FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
                '<link href="https://fonts.googleapis.com/css2?family=Amiri&family=Cairo:wght@400;700;800&display=swap" rel="stylesheet">')
STUDY_GROUPS = [
    ("① دراسة موسّعة", [
        {"file": "study_methodology", "title": "دراسة بياناتية موسّعة في منهجية تحليل الأسانيد",
         "desc": "العوائل العلمية، علاماتُ النقل من الكتب، التوثيق الضمنيّ، بصماتُ المخطوطات، والإسقاط الممنهج."},
    ]),
    ("② المشيخة وطرق الكتب", [
        {"file": "nuzul_atlas", "title": "أطلس النزول",
         "desc": "روايةُ الراوي عن قرينه قرينةٌ على النقل من كتابٍ مكتوب."},
        {"file": "book_transmission_fingerprints", "title": "بصمات نقل الكتب",
         "desc": "السلاسل المتكرّرة الدالّة على مصدرٍ مكتوب — معروفٌ ومُستنبَط."},
        {"file": "chains_2_bigrams", "title": "تكرار سلاسل المشايخ",
         "desc": "أكثر سلاسل الرواة تكرارًا — بصماتُ النقل (ثنائية وثلاثية ورباعية).",
         "variants": [("ثنائية", "chains_2_bigrams"), ("ثلاثية", "chains_3_trigrams_with_dirayah"),
                      ("رباعية", "chains_4_fourgrams_with_dirayah")]},
    ]),
    ("③ الرواة والشبكة", [
        {"file": "implicit_tawthiq_final", "title": "التوثيق الضمنيّ — إكثار الأجلّاء",
         "desc": "رواةٌ يُكثر الأجلّاء والثقات الرواية المباشرة عنهم — قرينةُ اعتماد."},
        {"file": "contradiction_narrators", "title": "رواة التعارض",
         "desc": "تعارض المنع الرجاليّ مع إكثار الأجلّاء — يُبرَز ولا يُحسَم."},
        {"file": "practical_impact_ranking", "title": "الأثر العمليّ والاختناق",
         "desc": "أكثر الرواة تأثيرًا في الأسانيد الفقهيّة، ونقاطُ الاختناق التي لا بديل لها."},
        {"file": "study_repair_impact", "title": "أيّ راوٍ يُصلح أكثر الأسانيد؟",
         "desc": "لكل سندٍ ضعيفٍ رجاليًّا: مَن الراوي الوحيد غير الموثَّق فيه؟ ترتيبُ أهداف التحقيق بأثرها على التقييم الرسميّ."},
        {"file": "study_network_centrality", "title": "أعمدة الشبكة وعنق الزجاجة",
         "desc": "محاور كلّ طبقة، ومَن يمرّ بهم القدرُ الأكبر من تراث كلّ إمام، وجسورُ الأجيال الكبرى."},
        {"file": "study_nisba_geography", "title": "أطلس النِّسَب الجغرافية",
         "desc": "هجرةُ الرواية من الكوفة إلى قم وبغداد — النسبُ الجغرافية على الطبقات، ومدارسُ المدن وتقويمُها."},
        {"file": "identity_audit", "title": "تدقيق الهويّة",
         "desc": "مرشّحات الاتّحاد والتصحيف، وتمييزُ المشترَك (ما لا يُدمَج)."},
        {"file": "madhhab_network", "title": "شبكة المذاهب",
         "desc": "مقدار رواية الإماميّة عمّن سواهم، وأكثرُ مَن اعتُمد عليه منهم."},
        {"file": "compiler_preferences", "title": "تفضيلات المصنّفين",
         "desc": "مَن يُكثر عنهم الكلينيّ والصدوق والطوسيّ — وتوزيعُ تقويمهم."},
        {"file": "topic_isnad_correlation", "title": "ارتباط الموضوع بالسند",
         "desc": "توزيع الرواة وتقويمهم بحسب الكتاب الفقهيّ.", "badge": "تقريبيّ — مستوى المجلّد"},
    ]),
    ("④ تحليل الأسانيد والعلل", [
        {"file": "defects_report", "title": "كشف العلل في الأسانيد",
         "desc": "السقط والتصحيف وتعارض الطبقات، مستخرَجةً من الأسانيد."},
        {"file": "defect_triage", "title": "فرز العلل وتصنيفها",
         "desc": "تصنيف مرشّحات السقط: مُرسَل، تعليق، مشيخة، أم سقطٌ حقيقيّ — مع أرجح واسطة."},
    ]),
    ("⑤ الموضوعات والفقه — تصنيف الأسانيد", [
        {"file": "study_topic_rank", "title": "المكثرون والمقلّون في التصنيف",
         "desc": "ترتيب الرواة بمجموع ظهورهم في الأسانيد المصنَّفة موضوعيًّا، وأعمدةُ كلّ باب."},
        {"file": "study_fiqh_ratio", "title": "نسبة الفقه عند المكثرين",
         "desc": "حصّةُ الرواية الفقهيّة من غيرها، وأبرزُ المائلين نسبيًّا إلى العقائد والفضائل."},
        {"file": "study_ghulat_fiqh", "title": "الغلاة والفقه",
         "desc": "اختبارُ قِلّة رواية المَرميّين بالغلوّ في الفقه — بدلالةٍ إحصائيّة (مان-ويتني)."},
        {"file": "study_topic_weakness", "title": "خريطة ضعف الأسانيد بحسب الموضوع",
         "desc": "أيّ الأبواب أكثرُ مرورًا بالضعفاء والمجاهيل، حتى مستوى الباب التفصيليّ."},
        {"file": "study_topic_bottleneck", "title": "نقاط الاختناق الموضوعيّة",
         "desc": "الرواةُ الذين تمرّ بهم الحصّةُ الأكبر من أسانيد كلّ باب (العُقَد التي يصعب تعويضها)."},
        {"file": "study_specialization", "title": "بصمة التخصّص الموضوعيّ",
         "desc": "مقياسُ تركّز الراوي على بابٍ واحد — قرينةُ أصلٍ/كتابٍ في ذلك الباب."},
        {"file": "study_imam_topics", "title": "خريطة الأئمة والموضوعات",
         "desc": "توزيع ما رُوي عن كلّ معصومٍ على الأبواب، ونسبةُ الصحيح من أسانيده."},
        {"file": "study_grading_methods", "title": "منهجا التقييم — أضعف الرواة والتقييم الرسميّ",
         "desc": "أين يتوافق حكمُ «بأضعف رواته» مع تقييم دراية الرسميّ وأين يفترقان — والإرسالُ سرُّ الفرق."},
        {"file": "study_ayat_narrators", "title": "القرآن في الرواية",
         "desc": "استشهاداتُ القرآن في كتب الحديث موصولةً بالأسانيد: أيّ سورةٍ يحملها تراثُ كلّ راوٍ وكلّ إمام."},
        {"file": "dataset_validation", "title": "التحقّق من البيانات",
         "desc": "مقارنة طبقاتنا المستنبَطة سابقًا بالتصدير المعتمد الكامل: الموضوعات، التقييم، الاتصال، المطابقة."},
        {"file": "bio_reconcile", "title": "مطابقة كتب الرجال",
         "desc": "تثبيتُ تراجم الرواة بفهرسة دراية المعتمدة، وإضافةُ جامع الرواة ومنهج المقال وعدّة الرجال."},
    ]),
]
_STUDY_BY_FILE = {it['file']: it for _, items in STUDY_GROUPS for it in items}

def _study_html(file):
    try:
        html = open(os.path.join(_STUDY_DIR, f'{file}.html'), encoding='utf-8').read()
    except OSError:
        return None
    if 'fonts.googleapis' not in html:
        html = html.replace('</head>', _STUDY_FONTS + '</head>', 1)
    return html

def page_atlas():
    st.subheader(i18n.t('atlas.title'))
    st.markdown(
        "<div class='r-intro'>"
        f"<div>{i18n.t('atlas.intro1')}</div>"
        f"<div>{i18n.t('atlas.intro2')}</div>"
        f"<div>{i18n.t('atlas.intro3')}</div>"
        "</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='r-verify'>{i18n.t('atlas.verify')}</div>", unsafe_allow_html=True)
    html = _study_html('topic_atlas')
    if not html:
        st.warning(i18n.t('atlas.loadfail')); return
    st.download_button(i18n.t('atlas.download'), data=html.encode('utf-8'),
                       file_name="topic_atlas.html", mime="text/html", key="atlas_dl")
    _components.html(html, height=1250, scrolling=True)

def page_studies():
    st.subheader(i18n.t('studies.title'))
    st.markdown(f"<div class='r-verify'>{i18n.t('studies.verify')}</div>", unsafe_allow_html=True)
    if i18n.is_en():
        st.caption(i18n.t('studies.arabic_note'))
    sel = ss.get('study')
    if sel and sel in _STUDY_BY_FILE:
        it = _STUDY_BY_FILE[sel]
        if st.button(i18n.t('studies.back'), key="study_back"):
            ss['study'] = None; st.rerun()
        st.markdown(f"### {i18n.study_title(it)}")
        file = it['file']
        if it.get('variants'):
            vals = [v for _, v in it['variants']]
            arlbl = {v: lbl for lbl, v in it['variants']}
            pick = st.radio(i18n.t('studies.variant'), vals, horizontal=True, key="study_variant",
                            label_visibility="collapsed", format_func=lambda v: i18n.variant_label(arlbl[v]))
            file = pick
        html = _study_html(file)
        if not html:
            st.warning(i18n.t('studies.loadfail')); return
        st.download_button(i18n.t('studies.download'), data=html.encode('utf-8'),
                           file_name=f"{file}.html", mime="text/html", key="study_dl")
        _components.html(html, height=(1250 if file == 'topic_atlas' else 900), scrolling=True)
        return
    for group, items in STUDY_GROUPS:
        st.markdown(f"<div class='r-studygroup'>{i18n.group_label(group)}</div>", unsafe_allow_html=True)
        cols = st.columns(2)
        for i, it in enumerate(items):
            with cols[i % 2]:
                badge = f" · <span class='r-badge'>{i18n.study_badge(it['badge'])}</span>" if it.get('badge') else ''
                st.markdown(ui.tile(i18n.study_title(it), '', i18n.study_desc(it) + badge), unsafe_allow_html=True)
                if st.button(i18n.t('studies.open'), key=f"open_{it['file']}", use_container_width=True):
                    ss['study'] = it['file']; st.rerun()

# ---------------------------------------------------------------- language + nav + sidebar
_lc, _nc = st.columns([1, 4])
with _lc:
    st.segmented_control(i18n.t('lang.label'), ['ar', 'en'], key="lang", label_visibility="collapsed",
                         format_func=lambda l: 'عربي' if l == 'ar' else 'English')
# direction: verbatim-Arabic blocks stay RTL; the rest flips to LTR in English mode
if i18n.is_en():
    st.markdown("<style>.main .block-container, section[data-testid='stSidebar']{direction:ltr!important;text-align:left!important;}"
                "div[data-testid='stSegmentedControl']{direction:ltr!important;}"
                ".r-quote,.r-bookpage{direction:rtl!important;text-align:right!important;}</style>",
                unsafe_allow_html=True)
with _nc:
    nav = st.segmented_control(i18n.t('nav.label'), NAV, key="nav", label_visibility="collapsed",
                               format_func=lambda k: i18n.t('nav.' + k)) or NAV[0]

with st.sidebar:
    st.markdown(f"## {i18n.t('home.title')}")
    s = db.global_stats()
    st.caption(i18n.t('side.stats', nar=f"{s['narrators']:,}", books=s['books'], chains=f"{s['chains']:,}") + "\n\n"
               + i18n.t('side.evals', evals=f"{s['evals']:,}") + "\n\n"
               + i18n.t('side.tabaqah', tab=f"{s['tabaqah']:,}"))
    st.divider()
    st.caption(i18n.t('side.sources'))

{NAV[0]: page_home, NAV[1]: page_library, NAV[2]: page_books, NAV[3]: page_isnad,
 NAV[4]: page_atlas, NAV[5]: page_studies}[nav]()

# ---- keep the URL in sync with the current location (shareable deep links) ----
_want = {}
if nav == NAV[1] and ss.get('d_id'):
    _want['n'] = ss['d_id']
elif nav == NAV[2] and ss.get('cur_book'):
    _want['book'] = ss['cur_book']
    if ss.get('bk_view') == 'full' and ss.get('bk_page'):
        _want['p'] = str(ss['bk_page'])
elif nav == NAV[5] and ss.get('study'):
    _want['s'] = ss['study']
if {k: v for k, v in st.query_params.items()} != _want:
    st.query_params.clear()
    for _k, _v in _want.items():
        st.query_params[_k] = _v
