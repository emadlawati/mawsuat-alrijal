"""Data-access layer for the Rijal app. Cached SQLite queries over rijal_core.db."""
import os, re, sqlite3, json
import streamlit as st

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.join(os.path.dirname(_HERE), 'rijal_core.db')   # local development (live data)
_PUBLIC = os.path.join(_HERE, 'rijal_public.db')                # deployed copy (next to the app)
DB = _CORE if os.path.exists(_CORE) else _PUBLIC

# book_id (as used in book_entries) -> Arabic title
BOOK_TITLES = {
    'najashi': 'رجال النجاشي', 'fihrist_tusi': 'فهرست الطوسي', 'rijal_tusi': 'رجال الطوسي',
    'kashshi': 'رجال الكشّي', 'qamoos_al_rijal': 'قاموس الرجال', 'khulasa': 'خلاصة الأقوال (الحلّي)',
    'ibn_dawud': 'رجال ابن داود', 'ibn_ghadairi': 'رجال ابن الغضائري', 'barqi': 'رجال البرقي',
    'alf_rajul': 'ألف رجل (الطبقات)', 'mujam_khoei': 'معجم رجال الحديث (الخوئي)',
    'qabasat': 'قبسات من علم الرجال',
}
TAB_AR = {1:'الأولى',2:'الثانية',3:'الثالثة',4:'الرابعة',5:'الخامسة',6:'السادسة',7:'السابعة',
          8:'الثامنة',9:'التاسعة',10:'العاشرة',11:'الحادية عشرة',12:'الثانية عشرة'}
MOD_AR = {'senior':'كبار','middle':'أواسط','junior':'صغار','':''}
AUTHORITY_AR = {'dirayah3':'دراية النور (تقويم معتمد)','derived':'مستنبَط من كتب الرجال','auto_masum':'معصوم'}

def _is_diac(ch):
    o = ord(ch)
    return ((0x0610 <= o <= 0x061A) or (0x064B <= o <= 0x065F) or o == 0x0670
            or (0x06D6 <= o <= 0x06ED) or o == 0x0640)

@st.cache_resource
def _conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

_DIAC = re.compile('[ؐ-ًؚ-ٰٟۖ-ۭـ]')
def norm(s):
    if not s: return ''
    s = ''.join(c for c in s if not _is_diac(c))
    for a in 'أإآٱ': s = s.replace(a, 'ا')
    s = s.replace('ى','ي').replace('ة','ه')
    return ' '.join(s.split())

# ---------- reliability ----------
def reliability(verdict):
    """Return (label, color, emoji) from a Dirayah verdict string."""
    v = verdict or ''
    if 'معصوم' in v: return ('معصوم', '#b8860b', '🌟')
    if 'ثقة' in v or 'ثقه' in v: return ('ثقة', '#2e7d32', '🟢')
    if 'حسن' in v or 'ممدوح' in v: return ('حسن/ممدوح', '#689f38', '🟩')
    if 'موثق' in v: return ('موثّق', '#00897b', '🟦')
    if 'مختلف' in v or 'اختلاف' in v: return ('مختلف فيه', '#ef6c00', '🟧')
    if 'ضعيف' in v or 'ضعیف' in v: return ('ضعيف', '#c62828', '🔴')
    if 'مجهول' in v or 'مهمل' in v: return ('مجهول', '#757575', '⚪')
    return (v or 'بلا تقويم', '#9e9e9e', '⚫')

# ---------- search ----------
@st.cache_data
def narrator_index():
    """List of (d_id, standard_name, search_blob, sand_count) for fast in-memory search."""
    c = _conn(); rows = []
    names = {}
    for d, nm in c.execute("SELECT d_id, name FROM names"):
        names.setdefault(d, []).append(nm)
    for r in c.execute("SELECT d_id, standard_name, kunya, sand_count FROM narrators"):
        d = r['d_id']
        blob = ' '.join([r['standard_name'] or ''] + names.get(d, []) + [r['kunya'] or ''])
        rows.append((d, r['standard_name'], norm(blob), r['sand_count'] or 0))
    return rows

def search_narrators(q, limit=60):
    if not q or len(q.strip()) < 2: return []
    qn = norm(q); terms = qn.split()
    out = []
    for d, name, blob, sc in narrator_index():
        if all(t in blob for t in terms):
            score = 3 if blob.startswith(qn) else (2 if qn in blob else 1)
            # exact normalized name beats prefix; tie-break by prominence (sand_count)
            if norm(name) == qn: score = 4
            out.append((score, sc, d, name))
    out.sort(key=lambda x: (-x[0], -x[1]))   # score desc, then prominence desc
    return [(d, name) for _, _, d, name in out[:limit]]

# ---------- narrator profile ----------
@st.cache_data
def narrator(d_id):
    c = _conn()
    r = c.execute("SELECT * FROM narrators WHERE d_id=?", (d_id,)).fetchone()
    if not r: return None
    d = dict(r)
    d['aliases'] = [x['name'] for x in c.execute(
        "SELECT name FROM names WHERE d_id=? AND name_type IN ('standard','alias') ORDER BY name_type", (d_id,))]
    d['evals'] = [dict(x) for x in c.execute("SELECT * FROM evaluations WHERE d_id=?", (d_id,))]
    tb = c.execute("SELECT * FROM narrator_tabaqah WHERE d_id=?", (d_id,)).fetchone()
    d['tabaqah'] = dict(tb) if tb else None
    d['teachers'] = [dict(x) for x in c.execute("""
        SELECT n.d_id, n.standard_name, r.chain_count FROM relations r
        JOIN narrators n ON n.d_id=r.teacher_did WHERE r.student_did=? ORDER BY r.chain_count DESC""", (d_id,))]
    d['students'] = [dict(x) for x in c.execute("""
        SELECT n.d_id, n.standard_name, r.chain_count FROM relations r
        JOIN narrators n ON n.d_id=r.student_did WHERE r.teacher_did=? ORDER BY r.chain_count DESC""", (d_id,))]
    d['books'] = [dict(x) for x in c.execute("""
        SELECT book_id, entry_no, page, text FROM book_entries
        WHERE d_id=? AND text IS NOT NULL ORDER BY book_id""", (d_id,))]
    d['chain_count'] = c.execute("SELECT COUNT(DISTINCT chain_id) FROM chain_narrators WHERE d_id=?", (d_id,)).fetchone()[0]
    return d

# ---------- books ----------
@st.cache_data
def book_stats():
    c = _conn(); out = []
    for bid in BOOK_TITLES:
        r = c.execute("""SELECT COUNT(*) t, SUM(CASE WHEN d_id IS NOT NULL THEN 1 ELSE 0 END) m
                         FROM book_entries WHERE book_id=?""", (bid,)).fetchone()
        out.append({'book_id': bid, 'title': BOOK_TITLES[bid], 'total': r['t'], 'matched': r['m'] or 0})
    return out

def book_entries_count(book_id):
    return _conn().execute("SELECT COUNT(*) FROM book_entries WHERE book_id=?", (book_id,)).fetchone()[0]

def book_entries(book_id, q='', limit=300, offset=0):
    c = _conn()
    if q and len(q.strip()) >= 2:
        ids = [r['rowid'] for r in c.execute(
            "SELECT rowid FROM book_entries_fts WHERE book_entries_fts MATCH ? AND book_id=? LIMIT ?",
            (q+'*', book_id, limit))]
        if ids:
            qmarks = ','.join('?'*len(ids))
            rows = c.execute(f"SELECT rowid,d_id,entry_no,headword,page,text FROM book_entries WHERE rowid IN ({qmarks})", ids).fetchall()
            return [dict(x) for x in rows]
        # fallback LIKE on headword
        qn = '%'+q.strip()+'%'
        return [dict(x) for x in c.execute(
            "SELECT rowid,d_id,entry_no,headword,page,text FROM book_entries WHERE book_id=? AND headword LIKE ? LIMIT ?",
            (book_id, qn, limit))]
    return [dict(x) for x in c.execute(
        "SELECT rowid,d_id,entry_no,headword,page,text FROM book_entries WHERE book_id=? ORDER BY CAST(entry_no AS INTEGER) LIMIT ? OFFSET ?",
        (book_id, limit, offset))]

# ---------- chains / isnad ----------
def search_chains(book_id=None, narrator_did=None, masum_only=False, limit=100):
    c = _conn(); where=[]; args=[]
    if book_id: where.append("c.book_id=?"); args.append(book_id)
    if masum_only: where.append("c.ends_in_masum=1")
    if narrator_did:
        where.append("c.chain_id IN (SELECT chain_id FROM chain_narrators WHERE d_id=?)"); args.append(narrator_did)
    w = ('WHERE '+' AND '.join(where)) if where else ''
    rows = c.execute(f"""SELECT c.chain_id,c.book_name,c.vol,c.start_page,c.narrator_count,c.level_count,c.ends_in_masum
        FROM chains c {w} ORDER BY c.chain_id LIMIT ?""", args+[limit]).fetchall()
    return [dict(x) for x in rows]

@st.cache_data
def chain_detail(chain_id):
    c = _conn()
    r = c.execute("SELECT * FROM chains WHERE chain_id=?", (chain_id,)).fetchone()
    if not r: return None
    d = dict(r)
    try: d['levels'] = json.loads(r['levels_json'] or '[]')
    except Exception: d['levels'] = []
    return d

@st.cache_data
def chain_books():
    c = _conn()
    return [r[0] for r in c.execute("SELECT DISTINCT book_name FROM chains ORDER BY book_name") if r[0]]

# ---------- browse narrators (paginated, numbered) ----------
@st.cache_data
def narrator_count():
    return _conn().execute("SELECT COUNT(*) FROM narrators").fetchone()[0]

@st.cache_data
def browse_narrators(offset, limit=50, sort='name'):
    c = _conn()
    order = "standard_name COLLATE NOCASE" if sort == 'name' else "d_id"
    rows = c.execute(f"""SELECT n.d_id, n.standard_name, e.verdict, t.tabaqa
        FROM narrators n LEFT JOIN evaluations e ON e.d_id=n.d_id
        LEFT JOIN narrator_tabaqah t ON t.d_id=n.d_id
        ORDER BY {order} LIMIT ? OFFSET ?""", (limit, offset)).fetchall()
    return [dict(r) for r in rows]

# ---------- full book pages ----------
@st.cache_data
def book_toc(book_id, vol):
    """Table of contents [(label, page)] for the reader's jump-navigation."""
    c = _conn()
    try:
        return [(r[0], r[1]) for r in c.execute(
            "SELECT label, page FROM book_toc WHERE book_id=? AND vol=? ORDER BY rowid", (book_id, vol))]
    except Exception:
        return []

@st.cache_data
def book_vols(book_id):
    c = _conn()
    return [r[0] for r in c.execute("SELECT DISTINCT vol FROM book_pages WHERE book_id=? ORDER BY vol", (book_id,))]

@st.cache_data
def book_page_range(book_id, vol):
    c = _conn()
    r = c.execute("SELECT MIN(page), MAX(page), COUNT(*) FROM book_pages WHERE book_id=? AND vol=?", (book_id, vol)).fetchone()
    return (r[0], r[1], r[2])

@st.cache_data
def book_page(book_id, vol, page):
    c = _conn()
    r = c.execute("SELECT text FROM book_pages WHERE book_id=? AND vol=? AND page=?", (book_id, vol, page)).fetchone()
    return r[0] if r else None

def book_pages_search(book_id, q, limit=50):
    """Search full book pages; return [(vol,page,snippet)]."""
    c = _conn(); out = []
    qn = q.strip()
    for vol, page, text in c.execute("SELECT vol,page,text FROM book_pages WHERE book_id=? AND text LIKE ? LIMIT ?",
                                     (book_id, '%'+qn+'%', limit)):
        i = text.find(qn); s = max(0, i-40)
        out.append((vol, page, ('…' if s else '')+text[s:i+len(qn)+50].replace('\n',' ')+'…'))
    return out

# ---------- isnad free-text resolver ----------
_CONN_RE = re.compile(r'\s*(?:حدّثنا|حدثنا|حدّثني|حدثني|أخبرنا|اخبرنا|أخبرني|اخبرني|أنبأنا|انبأنا|'
                      r'روى\s+عن|يرفعه\s+إلى|رفعه\s+إلى|عن|قال\s+حدثني|سمعت|وعنه|عنه)\s+')
def split_isnad(text):
    """Split an isnad into narrator name segments on transmission verbs and عن."""
    text = re.sub(r'[«»"\(\)\[\]]', ' ', text or '')
    parts = _CONN_RE.split(text)
    segs = []
    for p in parts:
        p = re.sub(r'\s+', ' ', p).strip(' .،:؛-')
        # split عطف on ' و ' when both sides look like names
        for sub in re.split(r'\s+و\s+(?=[ء-ي])', p) if ' و ' in p else [p]:
            sub = sub.strip(' .،:')
            if sub and re.search(r'[ء-ي]', sub) and len(sub) >= 2:
                segs.append(sub)
    return segs

@st.cache_resource
def _relset():
    c = _conn()
    return {(t, s) for t, s in c.execute("SELECT teacher_did, student_did FROM relations")}

@st.cache_resource
def _relcount():
    c = _conn()
    return {(t, s): cc for t, s, cc in c.execute("SELECT teacher_did, student_did, chain_count FROM relations")}

# common Imam kunyas / titles -> d_id (isnads almost always end here)
IMAM_KUNYA = {
    'ابي عبد الله':'D01491','الصادق':'D01491','جعفر بن محمد':'D01491',
    'ابي جعفر':'D03976','الباقر':'D03976','ابي جعفر الثاني':'D03977','الجواد':'D03977','ابي جعفر الجواد':'D03977',
    'ابي الحسن':'D04338','ابي ابراهيم':'D04338','الكاظم':'D04338','موسي بن جعفر':'D04338',
    'ابي الحسن الرضا':'D03100','الرضا':'D03100','علي بن موسي':'D03100',
    'ابي الحسن الثالث':'D03055','الهادي':'D03055','ابي الحسن العسكري':'D03055',
    'ابي محمد':'D00840','العسكري':'D00840','الحسن بن علي العسكري':'D00840',
    'امير المؤمنين':'D02847','علي بن ابي طالب':'D02847','ابي الحسن علي':'D02847',
    'زين العابدين':'D02928','السجاد':'D02928','علي بن الحسين':'D02928',
}
_REL_FATHER = re.compile(r'^(?:عن\s+)?(?:ابيه|أبيه|ابوه|أبوه|والده)$')
def resolve_isnad(text, topk=6):
    """Resolve each segment to a d_id via search + relation-aware Viterbi (A عن B => B teaches A).
    Handles Imam kunyas and the relative reference 'أبيه' (= father of the previous narrator)."""
    segs = split_isnad(text)
    nsegs = [norm(s) for s in segs]
    cand = []   # per segment: list of (d_id, name)
    rel = _relset()
    c = _conn()
    for i, s in enumerate(segs):
        ns = nsegs[i]
        if IMAM_KUNYA.get(ns):                      # Imam by kunya/name
            d = IMAM_KUNYA[ns]; nm = c.execute("SELECT standard_name FROM narrators WHERE d_id=?", (d,)).fetchone()
            cand.append([(d, nm[0] if nm else s)]); continue
        if _REL_FATHER.match(ns) and i > 0:         # 'أبيه' -> previous narrator's father (a teacher of theirs)
            cand.append('FATHER'); continue
        hits = search_narrators(s, limit=topk)
        cand.append(hits if hits else [(None, s)])
    # Greedy left-to-right: segment i is the TEACHER of segment i-1 (A عن B). Pick the candidate that
    # teaches the previously-resolved narrator; resolve 'أبيه' to that narrator's father (one of his teachers).
    def teachers_of(did, like=None, limit=8):
        rows = c.execute("""SELECT n.d_id,n.standard_name FROM relations r JOIN narrators n ON n.d_id=r.teacher_did
            WHERE r.student_did=? ORDER BY r.chain_count DESC LIMIT ?""", (did, limit)).fetchall()
        return [(r[0], r[1]) for r in rows]
    out = []; prev = None
    for i in range(len(cand)):
        ci = cand[i]; seg = segs[i]
        if ci == 'FATHER':
            seg = 'أبيه'; ci = [(None, 'أبيه')]
            if prev:
                pn = c.execute("SELECT standard_name FROM narrators WHERE d_id=?", (prev,)).fetchone()
                ftok = ''
                if pn:
                    tk = norm(pn[0]).split()
                    for k, tt in enumerate(tk):
                        if tt == 'بن' and k+1 < len(tk): ftok = tk[k+1]; break
                ts = teachers_of(prev)
                matched = [(d, nm) for d, nm in ts if ftok and norm(nm).split() and norm(nm).split()[0].startswith(ftok[:4])]
                ci = matched or ts or [(None, 'أبيه')]
        # choose candidate best connected to prev (teaches prev) — prefer the strongest (most chains) link
        pick = ci[0]
        if prev:
            rc = _relcount()
            connected = [(d, nm) for d, nm in ci if d and (d, prev) in rel]
            if connected:
                pick = max(connected, key=lambda x: rc.get((x[0], prev), 0))
        d, name = pick
        link_ok = ((d, prev) in rel) if (i > 0 and d and prev) else (None if i == 0 else False)
        out.append({'segment': seg, 'd_id': d, 'name': name, 'alts': ci[:6], 'link_ok': link_ok})
        prev = d if d else prev
    return out

# ---------- broken-link check for existing chains ----------
def chain_links(levels):
    """For consecutive levels, does ANY narrator in level i+1 teach ANY in level i? (chain flows L0<-L1<-...)"""
    rel = _relset(); flags=[]
    for i in range(len(levels)-1):
        upper=[x['d_id'] for x in levels[i]]; lower=[x['d_id'] for x in levels[i+1]]
        ok=any((t,s) in rel for t in lower for s in upper)
        flags.append(ok)
    return flags

# ---------- network graph ----------
def network_edges(d_id, max_each=8):
    c=_conn(); nodes={}; edges=[]
    me=c.execute("SELECT standard_name FROM narrators WHERE d_id=?", (d_id,)).fetchone()
    nodes[d_id]=(me[0] if me else d_id, 'me')
    for r in c.execute("""SELECT n.d_id,n.standard_name,rl.chain_count FROM relations rl
        JOIN narrators n ON n.d_id=rl.teacher_did WHERE rl.student_did=? ORDER BY rl.chain_count DESC LIMIT ?""",(d_id,max_each)):
        nodes[r['d_id']]=(r['standard_name'],'teacher'); edges.append((r['d_id'],d_id,r['chain_count']))
    for r in c.execute("""SELECT n.d_id,n.standard_name,rl.chain_count FROM relations rl
        JOIN narrators n ON n.d_id=rl.student_did WHERE rl.teacher_did=? ORDER BY rl.chain_count DESC LIMIT ?""",(d_id,max_each)):
        nodes[r['d_id']]=(r['standard_name'],'student'); edges.append((d_id,r['d_id'],r['chain_count']))
    return nodes, edges

# tabaqah calibration (image 1): tab -> (min_birth, max_birth, min_death, max_death)
TAB_YEARS = {1:(-51,-15,19,55),2:(-14,22,56,92),3:(23,59,93,129),4:(60,96,135,166),5:(97,133,167,204),
             6:(135,171,205,241),7:(172,209,242,279),8:(210,246,280,316),9:(247,284,317,354),
             10:(285,322,355,392),11:(323,359,393,430),12:(361,397,431,467)}

# ---------- Khoei/Mufid second authority (authentic book data from المفيد من معجم رجال الحديث) ----------
MUFID_VERDICT_AR = {'thiqah': 'ثقة', 'daif': 'ضعيف', 'majhul': 'مجهول'}

@st.cache_data
def mufid_eval(d_id):
    """DISABLED: the Mufid->d_id matching proved unreliable (contradictory many-to-one rows).
    Kept as a stub returning None until the Mufid matching is redone properly."""
    return None

@st.cache_data
def eval_flag(d_id):
    """Amber flag for the 66 unresolved Dirayah evaluation scrapes."""
    c = _conn()
    try:
        r = c.execute("SELECT issue, detail FROM eval_flags WHERE d_id=?", (d_id,)).fetchone()
    except Exception:
        return None
    return dict(r) if r else None

@st.cache_data
def tabaqah_spans():
    """d_id -> (low, high) span for isnad-gap hints."""
    c = _conn()
    return {r[0]: (r[1], r[2]) for r in c.execute(
        "SELECT d_id, tabaqah_low, tabaqah_high FROM narrator_tabaqah WHERE tabaqah_low IS NOT NULL")}

def tabaqah_gap(teacher_did, student_did):
    """True if the teacher/student tabaqah spans are too far apart (no overlap within ±1)."""
    sp = tabaqah_spans()
    t = sp.get(teacher_did); s = sp.get(student_did)
    if not t or not s: return False
    return (t[0] - s[1] > 1) or (s[0] - t[1] > 1)

# ---------- cached lookup maps for list rendering ----------
@st.cache_data
def verdict_map():
    """d_id -> Dirayah verdict (for compact chips in lists)."""
    c = _conn()
    return {r[0]: r[1] for r in c.execute("SELECT d_id, verdict FROM evaluations")}

@st.cache_data
def tab_map():
    """d_id -> primary tabaqa int."""
    c = _conn()
    return {r[0]: r[1] for r in c.execute("SELECT d_id, tabaqa FROM narrator_tabaqah")}

@st.cache_data
def global_stats():
    c = _conn()
    return {
        'narrators': c.execute("SELECT COUNT(*) FROM narrators").fetchone()[0],
        'evals': c.execute("SELECT COUNT(DISTINCT d_id) FROM evaluations").fetchone()[0],
        'tabaqah': c.execute("SELECT COUNT(*) FROM narrator_tabaqah").fetchone()[0],
        'chains': c.execute("SELECT COUNT(*) FROM chains").fetchone()[0],
        'books': c.execute("SELECT COUNT(DISTINCT book_id) FROM book_entries").fetchone()[0],
        'entries': c.execute("SELECT COUNT(*) FROM book_entries").fetchone()[0],
    }
