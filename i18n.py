"""i18n.py — bilingual (Arabic / English) UI layer for the Rijāl app.

• T: every UI-chrome string with 'ar' + 'en'. t(key, **fmt) reads st.session_state['lang'].
• Standard-term English maps (book titles, grades, ṭabaqāt, Imams, authorities) — the FIXED
  scholarly vocabulary that has settled English equivalents.
• disp_name(): Latin transliteration (translit.py) shown WITH the Arabic beside it in EN mode.

Primary-source content (jarḥ/taʿdīl verdicts, book page text) is NEVER translated here — it stays
verbatim Arabic, per the project's authenticity rule.
"""
import streamlit as st
import translit

def lang():
    return st.session_state.get('lang', 'ar')

def is_en():
    return lang() == 'en'

def dir_():
    return 'ltr' if is_en() else 'rtl'

def t(key, **kw):
    d = T.get(key, {})
    s = d.get(lang()) or d.get('ar') or key
    return s.format(**kw) if kw else s

# ---------------------------------------------------------------- name display
def disp_name(ar, html=False):
    """EN mode -> 'Translit (عربي)'. AR mode -> the Arabic as-is."""
    if not is_en() or not ar:
        return ar
    tr = translit.translit_name(ar)
    if not tr or tr == ar:
        return ar
    if html:
        return f"{tr} <span class='r-arabic'>({ar})</span>"
    return f"{tr} ({ar})"

# ---------------------------------------------------------------- standard-term maps (EN)
BOOK_EN = {
    'najashi': 'Rijāl al-Najāshī', 'fihrist_tusi': 'Al-Fihrist (al-Ṭūsī)',
    'rijal_tusi': 'Rijāl al-Ṭūsī', 'kashshi': 'Rijāl al-Kashshī',
    'qamoos_al_rijal': 'Qāmūs al-Rijāl (al-Tustarī)', 'khulasa': 'Khulāṣat al-Aqwāl (al-Ḥillī)',
    'ibn_dawud': 'Rijāl Ibn Dāwūd', 'ibn_ghadairi': 'Rijāl Ibn al-Ghaḍāʾirī',
    'barqi': 'Rijāl al-Barqī', 'alf_rajul': 'Alf Rajul (Ṭabaqāt)',
    'mujam_khoei': 'Muʿjam Rijāl al-Ḥadīth (al-Khūʾī)',
    'wafi_asaneed': 'Al-Wāfī fī Taḥqīq Asānīd al-Kāfī',
    'mufid_mujam': 'Al-Mufīd min Muʿjam Rijāl al-Ḥadīth (al-Jawāhirī)',
    'jami_ruwat': 'Jāmiʿ al-Ruwāt (al-Ardabīlī)', 'manhaj_maqal': 'Manhaj al-Maqāl (al-Astarābādī)',
    'uddat_rijal': 'ʿUddat al-Rijāl (al-Aʿrajī al-Kāẓimī)',
    'taliqat_zanjani': 'Al-Taʿlīqāt al-Rijāliyya (al-Shubayrī)', 'kashf_niqab': 'Kashf al-Niqāb (al-Shubayrī)',
}
BOOK_AUTHOR_EN = {
    'najashi': 'al-Najāshī (d. 450)', 'fihrist_tusi': 'al-Ṭūsī (d. 460)', 'rijal_tusi': 'al-Ṭūsī (d. 460)',
    'kashshi': 'al-Kashshī / al-Ṭūsī', 'qamoos_al_rijal': 'al-Tustarī', 'khulasa': 'al-ʿAllāma al-Ḥillī (d. 726)',
    'ibn_dawud': 'Ibn Dāwūd al-Ḥillī', 'ibn_ghadairi': 'Ibn al-Ghaḍāʾirī', 'barqi': 'al-Barqī',
    'alf_rajul': 'Sayyid Ghayth Shubbar', 'mujam_khoei': 'Sayyid al-Khūʾī (d. 1413)',
    'wafi_asaneed': 'Sayyid Ghayth Shubbar', 'qabasat': 'Shaykh Muslim al-Dāwarī',
    'mufid_mujam': 'Shaykh Muḥammad al-Jawāhirī',
}
def book_title(bid):
    import db
    return BOOK_EN.get(bid, db.BOOK_TITLES.get(bid, bid)) if is_en() else db.BOOK_TITLES.get(bid, bid)

# _dataset bio-location book_name (Arabic) -> EN (for the "also has a biography in" panel)
DATASET_BOOK_EN = {
    'رجال النجاشي': 'Rijāl al-Najāshī', 'الفهرست للطوسي': 'Al-Fihrist (al-Ṭūsī)', 'رجال الطوسي': 'Rijāl al-Ṭūsī',
    'اختیار معرفة الرجال': 'Rijāl al-Kashshī', 'الخلاصة للحلي': 'Khulāṣat al-Aqwāl', 'رجال ابن الغضائري': 'Rijāl Ibn al-Ghaḍāʾirī',
    'رجال البرقی-ابن داود': 'Rijāl al-Barqī / Ibn Dāwūd', 'معجم الرجال': 'Muʿjam Rijāl al-Ḥadīth', 'قاموس الرجال': 'Qāmūs al-Rijāl',
    'جامع الرواة': 'Jāmiʿ al-Ruwāt', 'منهج المقال': 'Manhaj al-Maqāl', 'عدة الرجال': 'ʿUddat al-Rijāl',
    'التعلیقات الرجالیة (1)': 'Al-Taʿlīqāt al-Rijāliyya', 'کشف النقاب': 'Kashf al-Niqāb',
}
def book_loc_name(book_code, book_name):
    if not is_en():
        return book_name
    return BOOK_EN.get(book_code) or DATASET_BOOK_EN.get(book_name) or translit.translit_name(book_name)

def pglabel(page):
    p = page if page not in (None, '') else ('؟' if not is_en() else '?')
    return f"p{p}" if is_en() else f"ص{p}"

TAB_EN = {1: 'First', 2: 'Second', 3: 'Third', 4: 'Fourth', 5: 'Fifth', 6: 'Sixth', 7: 'Seventh',
          8: 'Eighth', 9: 'Ninth', 10: 'Tenth', 11: 'Eleventh', 12: 'Twelfth'}
def tab_name(n):
    import db
    return TAB_EN.get(n, str(n)) if is_en() else db.TAB_AR.get(n, str(n))

MOD_EN = {'senior': 'senior', 'middle': 'middle', 'junior': 'junior', '': ''}
def mod_name(m):
    import db
    return MOD_EN.get(m or '', '') if is_en() else db.MOD_AR.get(m or '', '')

# reliability label (from db.reliability's Arabic label) -> EN
GRADE_EN = {
    'معصوم': 'Infallible (maʿṣūm)', 'ثقة': 'Thiqa — trustworthy', 'حسن/ممدوح': 'Ḥasan / praised',
    'موثّق': 'Muwaththaq — reliable', 'مختلف فيه': 'Disputed', 'ضعيف': 'Weak (ḍaʿīf)',
    'مجهول': 'Unknown (majhūl)', 'بلا تقويم': 'No appraisal',
}
def grade_label(ar_label):
    return GRADE_EN.get(ar_label, ar_label) if is_en() else ar_label

# chain-verdict labels (compute_grade) -> EN
CHAIN_GRADE_EN = {
    'صحيح': 'Ṣaḥīḥ (sound)', 'حسن / موثّق': 'Ḥasan / Muwaththaq', 'مختلف فيه': 'Disputed',
    'ضعيف فيه جهالة': 'Weak — contains majhūl', 'ضعيف': 'Weak', 'غير معلوم': 'Undetermined',
}
def chain_grade(ar):
    return CHAIN_GRADE_EN.get(ar, ar) if is_en() else ar

# official per-chain grading rollup buckets
OFFICIAL_GRADE_EN = {'صحيح': 'Ṣaḥīḥ', 'موثق/معتبر': 'Muwaththaq / Muʿtabar',
                     'ضعيف بجهالة': 'Weak (majhūl)', 'ضعيف': 'Weak'}

AUTHORITY_EN = {'dirayah3': 'Dirāya al-Nūr (authoritative appraisal)',
                'derived': 'derived from the rijāl books', 'auto_masum': 'Infallible'}

TAB_SRC_EN = {'alf_rajul': 'the book “Alf Rajul”', 'inferred': 'inferred from the narrator network & indicators',
              'inferred_llm': 'inferred from biographical texts'}

# madhhab field (freeform Arabic) -> EN, matched by substring
_MADHAB_EN = [('إمامي', 'Imāmī'), ('امامي', 'Imāmī'), ('عامي', 'ʿĀmmī (non-Imāmī)'), ('عامّي', 'ʿĀmmī (non-Imāmī)'),
              ('واقفي', 'Wāqifī'), ('فطحي', 'Faṭḥī'), ('زيدي', 'Zaydī'), ('ناووسي', 'Nāwūsī'),
              ('كيساني', 'Kaysānī'), ('بتري', 'Batrī'), ('اسماعيلي', 'Ismāʿīlī'), ('غالي', 'Ghālī')]
def madhab_label(v):
    if not is_en() or not v:
        return v
    base = v.split('(')[0]
    for ar, en in _MADHAB_EN:
        if ar in base:
            extra = ' — sound' if ('صحيح' in base) else (' — corrupt' if ('فاسد' in base) else '')
            return en + extra
    return translit.translit_name(base.strip()) or v

# Imam display names (timeline + top-Imams). Key = Arabic as stored.
IMAM_EN = {
    'النبي ﷺ': 'The Prophet ﷺ', 'عليّ ع': 'ʿAlī (a)', 'علي ع': 'ʿAlī (a)', 'الحسن ع': 'al-Ḥasan (a)',
    'الحسين ع': 'al-Ḥusayn (a)', 'السجاد ع': 'al-Sajjād (a)', 'الباقر ع': 'al-Bāqir (a)',
    'الصادق ع': 'al-Ṣādiq (a)', 'الكاظم ع': 'al-Kāẓim (a)', 'الرضا ع': 'al-Riḍā (a)',
    'الجواد ع': 'al-Jawād (a)', 'الهادي ع': 'al-Hādī (a)', 'العسكري ع': 'al-ʿAskarī (a)',
}
def imam_name(ar):
    if not is_en():
        return ar
    if ar in IMAM_EN:
        return IMAM_EN[ar]
    # top-Imam names come with «عليه السلام» stripped already; transliterate as fallback
    return translit.translit_name(ar) or ar

# ---------------------------------------------------------------- UI-chrome string table
T = {
    # nav
    'nav.home': {'ar': '🏠 الرئيسية', 'en': '🏠 Home'},
    'nav.narrators': {'ar': '🔎 الرواة', 'en': '🔎 Narrators'},
    'nav.books': {'ar': '📚 الكتب', 'en': '📚 Books'},
    'nav.isnad': {'ar': '🔗 الأسانيد', 'en': '🔗 Chains'},
    'nav.atlas': {'ar': '🗺️ موضوعات الرواة', 'en': '🗺️ Narrator Topics'},
    'nav.studies': {'ar': '📊 الدراسات', 'en': '📊 Studies'},
    'nav.label': {'ar': 'التنقل', 'en': 'Navigation'},
    'lang.label': {'ar': 'اللغة', 'en': 'Language'},

    # profile
    'p.back': {'ar': '↩ رجوع للنتائج', 'en': '↩ Back to results'},
    'p.notfound': {'ar': 'لم يُعثر على الراوي.', 'en': 'Narrator not found.'},
    'p.kunya': {'ar': 'الكنية: {v}', 'en': 'Kunya: {v}'},
    'p.madhab': {'ar': 'المذهب: {v}', 'en': 'School: {v}'},
    'p.born': {'ar': 'الولادة: {v} هـ', 'en': 'Born: {v} AH'},
    'p.died': {'ar': 'الوفاة: {v} هـ', 'en': 'Died: {v} AH'},
    'p.chains': {'ar': 'وروده في الأسانيد: {v}', 'en': 'Appears in chains: {v}'},
    'p.tabsrc': {'ar': 'مصدر الطبقة: {v}', 'en': 'Ṭabaqa source: {v}'},
    'p.masum': {'ar': '🌟 معصوم', 'en': '🌟 Infallible'},
    'p.flag': {'ar': 'لم يتيسّر التحقق الآلي من تقويم هذا الراوي في برنامج دراية النور، فيُرجى التحقق منه يدوياً. ({v})',
               'en': 'Automated verification of this narrator’s appraisal in Dirāya al-Nūr was not possible; please verify manually. ({v})'},
    'p.eval.title': {'ar': '📊 تقويم دراية النور', 'en': '📊 Dirāya al-Nūr appraisal'},
    'p.eval.result': {'ar': 'حصيلة التقويم:', 'en': 'Appraisal outcome:'},
    'p.eval.aggregate': {'ar': 'جمع التقويم:', 'en': 'Appraisal summary:'},
    'p.eval.none': {'ar': 'لا يوجد تقويم في دراية النور لهذا الراوي.',
                    'en': 'No Dirāya al-Nūr appraisal for this narrator.'},
    'p.grading.title': {'ar': '⚖️ أسانيده في التقييم الرسميّ (دراية)',
                        'en': '⚖️ His chains in the official grading (Dirāya)'},
    'p.grading.body': {'ar': 'وُزِّعت أسانيدُه ({n}) على التقييم الرسميّ: ',
                       'en': 'His chains ({n}) distributed across the official grading: '},
    'p.grading.imams': {'ar': 'عمّن يروي من المعصومين:', 'en': 'Which Infallibles he narrates from:'},
    'p.tab.teachers': {'ar': '🧑‍🏫 الشيوخ والتلاميذ', 'en': '🧑‍🏫 Teachers & students'},
    'p.tab.network': {'ar': '🕸️ شبكة الرواية', 'en': '🕸️ Transmission network'},
    'p.tab.timeline': {'ar': '📈 الخطّ الزمني', 'en': '📈 Timeline'},
    'p.tab.books': {'ar': '📚 في الكتب', 'en': '📚 In the books'},
    'p.tab.aliases': {'ar': '📛 الأسماء والألقاب', 'en': '📛 Names & epithets'},
    'p.teachers': {'ar': 'شيوخه (روى عنهم) — {n}', 'en': 'His teachers (narrated from) — {n}'},
    'p.students': {'ar': 'تلاميذه (رَوَوا عنه) — {n}', 'en': 'His students (narrated from him) — {n}'},
    'p.showall': {'ar': 'عرض الكل ({n})', 'en': 'Show all ({n})'},
    'p.notab': {'ar': 'لا توجد طبقة مسجّلة لهذا الراوي.', 'en': 'No recorded ṭabaqa for this narrator.'},
    'p.nobooktext': {'ar': 'لا توجد ترجمة مستخرجة في الكتب لهذا الراوي.',
                     'en': 'No extracted biography in the books for this narrator.'},
    'p.alsoin': {'ar': '📍 <b>وردت له ترجمة أيضًا في (فهرسة دراية المعتمدة):</b>',
                 'en': '📍 <b>Also has a biography in (Dirāya’s authoritative index):</b>'},
    'p.dirloc': {'ar': 'دراية: {v}ص{p}', 'en': 'Dirāya: {v}p{p}'},

    # network
    'net.slider': {'ar': 'عدد الشيوخ/التلاميذ المعروضين', 'en': 'Teachers/students shown'},
    'net.none': {'ar': 'لا توجد علاقات مسجّلة في الشبكة.', 'en': 'No recorded relations in the network.'},
    'net.aslist': {'ar': 'عرض البيانات كقائمة (لمتصفحي الشاشة)', 'en': 'Show as a list (for screen readers)'},
    'net.teachers': {'ar': 'الشيوخ ({n}):', 'en': 'Teachers ({n}):'},
    'net.students': {'ar': 'التلاميذ ({n}):', 'en': 'Students ({n}):'},
    'net.legend': {'ar': '🟢 شيوخه · 🟦 الراوي · 🟠 تلاميذه — السهم باتجاه «روى عنه» (من الشيخ إلى تلميذه)',
                   'en': '🟢 teachers · 🟦 the narrator · 🟠 students — arrow points teacher → student'},

    # timeline
    'tl.year': {'ar': 'السنة الهجرية', 'en': 'Year (AH)'},
    'tl.thisnar': {'ar': '⟵ هذا الراوي', 'en': '⟵ this narrator'},
    'tl.kind.imam': {'ar': 'إمام', 'en': 'Imam'},
    'tl.kind.nar': {'ar': 'الراوي', 'en': 'Narrator'},
    'tl.col.from': {'ar': 'من', 'en': 'From'},
    'tl.col.to': {'ar': 'إلى', 'en': 'To'},
    'tl.col.name': {'ar': 'الاسم', 'en': 'Name'},
    'tl.astable': {'ar': 'عرض البيانات كجدول (لمتصفحي الشاشة)', 'en': 'Show as a table (for screen readers)'},
    'tl.caption': {'ar': 'الطبقة {tab}{span} — موقع الراوي الزمني مقارنةً بحياة الأئمة عليهم السلام.',
                   'en': 'Ṭabaqa {tab}{span} — the narrator’s position in time against the Imams’ lifetimes.'},
    'tl.span': {'ar': ' (تمتد من الطبقة {lo} إلى {hi})', 'en': ' (spans ṭabaqāt {lo}–{hi})'},

    # home
    'home.title': {'ar': '📜 موسوعة الرجال', 'en': '📜 Encyclopedia of Rijāl'},
    'home.subtitle': {'ar': 'قاعدة بيانات رواة الحديث عند الإمامية — التقويم، الطبقات، الكتب، وتحليل الأسانيد',
                      'en': 'A database of Imāmī ḥadīth narrators — appraisal, ṭabaqāt, books, and chain analysis'},
    'home.intro1': {'ar': '🔎 ترجمة وافية لـ<b>{n}</b> راوٍ: أقوالُ علماء الرجال فيه نصًّا، وتقويمُه وطبقتُه، وشيوخُه وتلاميذُه وشبكةُ روايته',
                    'en': '🔎 A full profile for <b>{n}</b> narrators: the rijāl scholars’ verbatim opinions, appraisal, ṭabaqa, teachers, students, and transmission network'},
    'home.intro2': {'ar': '📚 كتب الرجال كاملةً: اقرأها صفحةً صفحة، وابحث في نصوصها، وانتقل من أيّ اسمٍ يرد فيها إلى ترجمة صاحبه بنقرة',
                    'en': '📚 The complete rijāl books: read them page by page, search their text, and jump from any name to its narrator’s profile in one click'},
    'home.intro3': {'ar': '🔗 محلّل الأسانيد: الصق أيّ سندٍ كما ورد في الكتاب، فيُحدَّد كلُّ راوٍ فيه ويُحكم عليه بأضعف رواته',
                    'en': '🔗 Chain analyzer: paste any isnād as it appears in the book — every narrator is identified and the chain graded by its weakest link'},
    'home.intro5': {'ar': '🗺️ موضوعات الرواة: أطلس تفاعليّ يكشف بصمة كلّ راوٍ — في أيّ الأبواب روى، وعمّن من المعصومين، وكم نسبةُ الصحيح في أسانيده',
                    'en': '🗺️ Narrator topics: an interactive atlas of each narrator’s fingerprint — which chapters he narrated in, from which Imams, and how much of his corpus grades ṣaḥīḥ'},
    'home.intro4': {'ar': '📊 دراساتٌ بحثيّة في الأسانيد والرجال: العلل وطرق الكتب، وشبكة الرواة وجغرافيا النقل، والقرآن في الرواية',
                    'en': '📊 Research studies on the chains and rijāl: defects and book-paths, the narrator network and the geography of transmission, and the Qurʾān in narration'},
    'home.verify': {'ar': '⚠️ تنبيه: هذه الموسوعة أداة بحثية تساعد في تقييم الأسانيد ومعرفة حال الرواة. يرجى دائماً الرجوع إلى المصدر الأصلي والتحقق منه لاحتمالية وقوع الخطأ.',
                    'en': '⚠️ Note: this encyclopedia is a research aid for assessing chains and narrators. Always return to the original source and verify, as errors are possible.'},
    'home.search': {'ar': 'ابحث عن راوٍ بالاسم أو الكنية أو اللقب', 'en': 'Search a narrator by name, kunya, or epithet'},
    'home.search.ph': {'ar': 'مثال: زرارة بن أعين · محمد بن يعقوب الكليني · أبو بصير — أو بالحروف اللاتينية: zurara',
                       'en': 'e.g. zurara · kulayni · ibn abi umayr — plain spelling, accents, or Arabic all work'},
    'home.nresults': {'ar': '{n} نتيجة', 'en': '{n} result(s)'},
    'home.sec.texts': {'ar': 'في نصوص كتب الرجال', 'en': 'In the rijāl book texts'},
    'home.stat.narrators': {'ar': 'راوياً', 'en': 'narrators'},
    'home.stat.evals': {'ar': 'تقويم دراية النور', 'en': 'Dirāya al-Nūr appraisals'},
    'home.stat.tabaqah': {'ar': 'راوياً معلوم الطبقة', 'en': 'narrators with known ṭabaqa'},
    'home.stat.chains': {'ar': 'سنداً', 'en': 'chains'},
    'home.stat.entries': {'ar': 'ترجمة من {n} كتب', 'en': 'biographies from {n} books'},
    'home.feat1.t': {'ar': '🔎 مكتبة الرواة', 'en': '🔎 Narrator library'},
    'home.feat1.d': {'ar': 'ترجمة وافية لكل راوٍ: تقويمه، وطبقته، وشيوخه وتلاميذه، وشبكة روايته، وخطّه الزمني.',
                     'en': 'A full profile for each narrator: appraisal, ṭabaqa, teachers & students, transmission network, and timeline.'},
    'home.feat2.t': {'ar': '📚 كتب الرجال', 'en': '📚 The rijāl books'},
    'home.feat2.d': {'ar': 'عشرة كتب رجالية كاملة: تصفّح تراجمها، واقرأها صفحةً صفحة، وابحث في نصوصها.',
                     'en': 'Complete rijāl books: browse their biographies, read page by page, and search their text.'},
    'home.feat3.t': {'ar': '🔗 محلّل الأسانيد', 'en': '🔗 Chain analyzer'},
    'home.feat3.d': {'ar': 'حلّل أي سند تنسخه نصاً: يُحدَّد كل راوٍ فيه ويُحكم على السند بأضعف رواته.',
                     'en': 'Analyze any chain you paste: each narrator is identified and the chain is graded by its weakest link.'},
    'home.open': {'ar': 'فتح', 'en': 'Open'},

    # library
    'lib.title': {'ar': '🔎 مكتبة الرواة', 'en': '🔎 Narrator library'},
    'lib.mode.search': {'ar': 'بحث', 'en': 'Search'},
    'lib.mode.browse': {'ar': 'تصفّح الكل', 'en': 'Browse all'},
    'lib.search': {'ar': 'ابحث باسم الراوي أو لقبه أو كنيته', 'en': 'Search by narrator name, epithet, or kunya'},
    'lib.search.ph': {'ar': 'مثال: زرارة بن أعين — أو zurara', 'en': 'e.g. zurara · hammad b isa · abu basir'},
    'lib.page': {'ar': 'صفحة {p} من {n} · {t} راوٍ', 'en': 'Page {p} of {n} · {t} narrators'},
    'lib.prev': {'ar': '◀ السابق', 'en': '◀ Prev'},
    'lib.next': {'ar': 'التالي ▶', 'en': 'Next ▶'},
    'lib.hint': {'ar': 'ابحث عن راوٍ لعرض ترجمته الكاملة، أو اختر «تصفّح الكل» لاستعراض الرواة جميعاً.',
                 'en': 'Search a narrator to see the full profile, or choose “Browse all” to page through everyone.'},

    # books
    'bk.title': {'ar': '📚 كتب الرجال', 'en': '📚 The rijāl books'},
    'bk.tilemeta': {'ar': '{n} ترجمة · {p}% منها موصولة بقاعدة الرواة',
                    'en': '{n} biographies · {p}% linked to the narrator database'},
    'bk.browse': {'ar': 'تصفّح الكتاب', 'en': 'Browse the book'},
    'bk.allbooks': {'ar': '⬅ كل الكتب', 'en': '⬅ All books'},
    'bk.alf': {'ar': 'كتاب «ألف رجل» مأخوذ كاملاً من قاعدة بيانات تطبيقه — وتراجمه الـ1015 كلّها في «التراجم».',
               'en': '“Alf Rajul” is taken entirely from its app database — all 1,015 of its biographies are under “Biographies”.'},
    'bk.view.bios': {'ar': '📑 التراجم', 'en': '📑 Biographies'},
    'bk.view.full': {'ar': '📖 الكتاب كاملاً', 'en': '📖 Full book'},
    'bk.search.bios': {'ar': 'ابحث في التراجم', 'en': 'Search the biographies'},
    'bk.search.bios.ph': {'ar': 'اسم راوٍ أو كلمة في النص', 'en': 'a narrator name or a word in the text'},
    'bk.nresults': {'ar': '{n} نتيجة', 'en': '{n} result(s)'},
    'bk.page': {'ar': 'صفحة {p} من {n} · {t} ترجمة', 'en': 'Page {p} of {n} · {t} biographies'},
    'bk.entry.full': {'ar': '↩ عرض ترجمة الراوي الكاملة', 'en': '↩ Open the narrator’s full profile'},
    'bk.openpage': {'ar': '📖 فتحها في صفحة الكتاب', 'en': '📖 Open in the book page'},
    'bk.vol': {'ar': 'الجزء {v}', 'en': 'Volume {v}'},
    'bk.vol.label': {'ar': 'الجزء', 'en': 'Volume'},
    'bk.toc.head': {'ar': '— فهرس المحتويات —', 'en': '— Table of contents —'},
    'bk.toc.goto': {'ar': 'انتقل إلى باب', 'en': 'Jump to a chapter'},
    'bk.fts': {'ar': 'بحث في نصّ الكتاب كاملاً', 'en': 'Search the full book text'},
    'bk.fts.ph': {'ar': 'كلمة أو عبارة', 'en': 'a word or phrase'},
    'bk.nhits': {'ar': '{n} موضع', 'en': '{n} location(s)'},
    'bk.loc': {'ar': 'ج{v} ص{p}', 'en': 'v{v} p{p}'},
    'bk.prevpage': {'ar': '◀ السابقة', 'en': '◀ Prev'},
    'bk.nextpage': {'ar': 'التالية ▶', 'en': 'Next ▶'},
    'bk.pageword': {'ar': 'الصفحة', 'en': 'Page'},
    'bk.pageof': {'ar': 'صفحة {p} من {n}', 'en': 'Page {p} of {n}'},

    # isnad
    'is.title': {'ar': '🔗 محلّل الأسانيد', 'en': '🔗 Chain analyzer'},
    'is.caption': {'ar': 'انسخ السند كما ورد في الكتاب، وسيُحدَّد كل راوٍ فيه ويُحكم على السند بأضعف رواته.',
                   'en': 'Paste the chain as it appears in the book; each narrator is identified and the chain is graded by its weakest link.'},
    'is.example': {'ar': 'مثال {n}', 'en': 'Example {n}'},
    'is.text': {'ar': 'نصّ السند', 'en': 'Chain text'},
    'is.text.ph': {'ar': 'محمد بن يعقوب عن علي بن إبراهيم عن أبيه …',
                   'en': 'Paste the Arabic chain, e.g. محمد بن يعقوب عن علي بن إبراهيم عن أبيه …'},
    'is.analyze': {'ar': '🔍 حلّل السند', 'en': '🔍 Analyze the chain'},
    'is.spinner': {'ar': 'جارٍ تحليل السند…', 'en': 'Analyzing the chain…'},
    'is.alts': {'ar': 'احتمالات أخرى لتحديد الرواة (إن أخطأ التحديد)',
                'en': 'Alternative identifications (if a narrator was misidentified)'},
    'is.altsline': {'ar': '(احتمالات أخرى: {alts})', 'en': '(other candidates: {alts})'},

    # chips
    'chip.tab': {'ar': 'الطبقة {name}', 'en': 'Ṭabaqa {name}'},
    'chip.tab.mod': {'ar': ' (من {mod}ها)', 'en': ' ({mod})'},
    'chip.tab.span': {'ar': ' · أدرك الطبقات {lo}–{hi}', 'en': ' · reached ṭabaqāt {lo}–{hi}'},
    'chip.tab.short': {'ar': 'ط{n}', 'en': 'ṭ{n}'},

    # isnad stepper (ui.py)
    'st.atf': {'ar': '(عطف — في الطبقة نفسها)', 'en': '(conjoined — same ṭabaqa)'},
    'st.unresolved': {'ar': '(لم يُحدَّد)', 'en': '(not identified)'},
    'st.conn.ok.n': {'ar': '✓ الرواية بينهما ثابتة (في {n} سنداً)', 'en': '✓ transmission attested ({n} chains)'},
    'st.conn.ok': {'ar': '✓ الرواية بينهما ثابتة', 'en': '✓ transmission attested'},
    'st.conn.bad': {'ar': '⚠ لم تثبت رواية بينهما في الأسانيد', 'en': '⚠ no attested transmission between them'},
    'st.conn.warn.gap': {'ar': 'لم تثبت رواية بينهما، مع تباعدٍ في طبقتيهما',
                         'en': 'no attested transmission, and a gap in their ṭabaqāt'},
    'st.grade': {'ar': 'حكم السند: {g}', 'en': 'Chain grade: {g}'},
    'st.why': {'ar': 'بأضعف رواته: {name} ({lab})', 'en': 'by its weakest narrator: {name} ({lab})'},

    # atlas
    'atlas.title': {'ar': '🗺️ موضوعات الرواة', 'en': '🗺️ Narrator Topics'},
    'atlas.intro1': {'ar': '🔎 <b>ما هذه الأداة؟</b> أداةٌ تفاعليّة تُصنِّف أسانيد الكتب الحديثيّة بحسب <b>موضوعها</b> (فقه، عقائد، دعاء، فضائل، أخلاق) وأبوابها (طهارة، صلاة، حج، نكاح…)، ثمّ تُظهر لكلّ راوٍ بصمتَه الموضوعيّة.',
                     'en': '🔎 <b>What is this?</b> An interactive tool that classifies the ḥadīth chains by <b>topic</b> (fiqh, creed, supplication, virtues, ethics) and chapter (purity, prayer, ḥajj, marriage…), then shows each narrator’s topical fingerprint.'},
    'atlas.intro2': {'ar': '🧭 <b>ماذا تفعل؟</b> ابحث عن أيّ راوٍ لترى: في أيّ الأبواب يروي، ونسبةَ روايته الفقهيّة، وتخصّصَه أو سعتَه، ومَن رماه الرجاليّون بالغلوّ (مع النصّ ومصدره).',
                     'en': '🧭 <b>What does it do?</b> Search any narrator to see: which chapters he transmits in, his fiqh ratio, his specialization or breadth, and who was accused of ghuluww (with the text and its source).'},
    'atlas.intro3': {'ar': '📊 <b>وفيها ستّ دراسات</b> قابلةٌ للفرز والتصفية: المكثرون، نسبة الفقه، الغلاة والفقه، خريطة ضعف الأسانيد، نقاط الاختناق، بصمة التخصّص.',
                     'en': '📊 <b>It includes six studies</b>, sortable and filterable: prolific narrators, fiqh ratio, ghulāt & fiqh, chain-weakness map, bottlenecks, and specialization fingerprint.'},
    'atlas.verify': {'ar': '⚠️ أداةٌ بحثيّة للاستئناس والاستكشاف لا للحكم النهائيّ — التصنيف مستخرَجٌ آليًّا من فهارس الكتب، ونسبةُ الفقه نسبيّةٌ (المدوّنة فقهيّة الطابع)، فيُرجى دائماً الرجوع إلى المصدر الأصليّ والتحقّق منه.',
                     'en': '⚠️ A research aid for exploration, not final judgment — the classification is derived automatically from the books’ indexes, and the fiqh ratio is relative (the corpus is fiqh-leaning). Always return to the original source and verify.'},
    'atlas.download': {'ar': '⬇ تحميل الأداة (HTML)', 'en': '⬇ Download the tool (HTML)'},
    'atlas.loadfail': {'ar': 'تعذّر تحميل الأداة.', 'en': 'Could not load the tool.'},

    # studies
    'studies.title': {'ar': '📊 الدراسات', 'en': '📊 Studies'},
    'studies.verify': {'ar': 'هذه دراساتٌ بحثيّة تجريبيّة مبنيّةٌ على تحليل الأسانيد، للاستئناس والاستكشاف لا للحكم النهائيّ — ويُرجى دائمًا الرجوع إلى المصدر الأصليّ والتحقّق منه.',
                       'en': 'These are experimental research studies built on chain analysis — for exploration, not final judgment. Always return to the original source and verify.'},
    'studies.arabic_note': {'ar': '', 'en': 'ℹ️ The study reports themselves are in-depth Arabic research documents and remain in Arabic; their titles and descriptions are translated below.'},
    'studies.back': {'ar': '↩ رجوع لقائمة الدراسات', 'en': '↩ Back to the studies list'},
    'studies.variant': {'ar': 'طول السلسلة', 'en': 'Chain length'},
    'studies.download': {'ar': '⬇ تحميل التقرير (HTML)', 'en': '⬇ Download the report (HTML)'},
    'studies.loadfail': {'ar': 'تعذّر تحميل هذه الدراسة.', 'en': 'Could not load this study.'},
    'studies.open': {'ar': 'فتح الدراسة', 'en': 'Open the study'},

    # study catalog group headers
    'sg.1': {'ar': '① دراسة موسّعة', 'en': '① Extended study'},
    'sg.2': {'ar': '② المشيخة وطرق الكتب', 'en': '② Mashyakha & book-paths'},
    'sg.3': {'ar': '③ الرواة والشبكة', 'en': '③ Narrators & the network'},
    'sg.4': {'ar': '④ تحليل الأسانيد والعلل', 'en': '④ Chain analysis & defects'},
    'sg.5': {'ar': '⑤ الموضوعات والفقه — تصنيف الأسانيد', 'en': '⑤ Topics & fiqh — chain classification'},

    # sidebar
    'side.stats': {'ar': '{nar} راوٍ · {books} كتب · {chains} سند',
                   'en': '{nar} narrators · {books} books · {chains} chains'},
    'side.evals': {'ar': 'التقويم: {evals} (دراية النور)', 'en': 'Appraisals: {evals} (Dirāya al-Nūr)'},
    'side.tabaqah': {'ar': 'الطبقات: {tab} راوياً', 'en': 'Ṭabaqāt: {tab} narrators'},
    'side.sources': {'ar': 'المصادر: دراية النور ٣ (CRCIS) · كتب الرجال العشرة · ألف رجل',
                     'en': 'Sources: Dirāya al-Nūr 3 (CRCIS) · the ten rijāl books · Alf Rajul'},
}

# ---------------------------------------------------------------- study catalog (EN parallel)
# Keyed by the study 'file'; page_studies() falls back to the Arabic title/desc when a key is absent.
STUDY_GROUP_EN = {'① دراسة موسّعة': 'sg.1', '② المشيخة وطرق الكتب': 'sg.2', '③ الرواة والشبكة': 'sg.3',
                  '④ تحليل الأسانيد والعلل': 'sg.4', '⑤ الموضوعات والفقه — تصنيف الأسانيد': 'sg.5'}
def group_label(ar_group):
    return t(STUDY_GROUP_EN[ar_group]) if (is_en() and ar_group in STUDY_GROUP_EN) else ar_group

STUDY_EN = {
    'study_methodology': ('An extended data study on chain-analysis methodology',
        'Scholarly families, book-transmission markers, implicit tawthīq, manuscript fingerprints, and systematic omission.'),
    'nuzul_atlas': ('Atlas of “nuzūl”',
        'A narrator transmitting from his peer is an indicator of copying from a written book.'),
    'book_transmission_fingerprints': ('Book-transmission fingerprints',
        'Recurring chains indicating a written source — known and inferred.'),
    'chains_2_bigrams': ('Recurrence of mashyakha chains',
        'The most recurring narrator chains — transmission fingerprints (bi-, tri-, four-grams).'),
    'implicit_tawthiq_final': ('Implicit tawthīq — the eminent narrating abundantly',
        'Narrators from whom the eminent and reliable transmit directly and often — an indicator of reliance.'),
    'contradiction_narrators': ('Narrators of contradiction',
        'Where a rijālī rejection contradicts abundant transmission by the eminent — surfaced, not decided.'),
    'practical_impact_ranking': ('Practical impact & bottlenecks',
        'The most influential narrators in fiqh chains, and the bottlenecks with no substitute.'),
    'identity_audit': ('Identity audit',
        'Candidates for unification and taṣḥīf, and distinguishing the homonymous (what must not be merged).'),
    'madhhab_network': ('Madhhab network',
        'How much the Imāmiyya transmit from others, and the most relied-upon among them.'),
    'compiler_preferences': ('Compilers’ preferences',
        'From whom al-Kulaynī, al-Ṣadūq, and al-Ṭūsī transmit most — and their appraisal distribution.'),
    'topic_isnad_correlation': ('Topic–chain correlation',
        'Distribution of narrators and their appraisal by fiqh book.'),
    'defects_report': ('Detecting chain defects',
        'Omission, taṣḥīf, and ṭabaqa conflicts, extracted from the chains.'),
    'defect_triage': ('Triage & classification of defects',
        'Classifying omission candidates: mursal, taʿlīq, mashyakha, or a real omission — with the likeliest missing link.'),
    'study_topic_rank': ('Prolific vs. sparse in the classification',
        'Ranking narrators by total appearances in topically-classified chains, and each chapter’s pillars.'),
    'study_fiqh_ratio': ('Fiqh ratio among the prolific',
        'The share of fiqh transmission vs. others, and the most relatively creed/virtue-leaning.'),
    'study_ghulat_fiqh': ('Ghulāt & fiqh',
        'Testing whether those accused of ghuluww transmit less in fiqh — with statistical significance (Mann–Whitney).'),
    'study_topic_weakness': ('Chain-weakness map by topic',
        'Which chapters pass most through the weak and unknown, down to the detailed chapter level.'),
    'study_topic_bottleneck': ('Topical bottlenecks',
        'The narrators through whom the largest share of each chapter’s chains passes (hard-to-replace nodes).'),
    'study_specialization': ('Topical specialization fingerprint',
        'A measure of a narrator’s concentration on one chapter — an indicator of an aṣl/book in that chapter.'),
    'study_imam_topics': ('Map of the Imams & topics',
        'Distribution of what is narrated from each Infallible across chapters, and the ṣaḥīḥ share of his chains.'),
    'study_grading_methods': ('Two grading methods — weakest narrator vs. the official grading',
        'Where “by its weakest narrator” agrees with Dirāya’s official grading and where they diverge — irsāl being the key.'),
    'dataset_validation': ('Data validation',
        'Comparing our previously-inferred ṭabaqāt with the full authoritative export: topics, grading, connection, matching.'),
    'bio_reconcile': ('Reconciling the rijāl books',
        'Fixing narrator biographies against Dirāya’s authoritative index, adding Jāmiʿ al-Ruwāt, Manhaj al-Maqāl & ʿUddat al-Rijāl.'),
    'study_repair_impact': ('Which narrator repairs the most chains?',
        'For each chain weak on rijālī grounds: who is its single unauthenticated narrator? Research targets ranked by impact on the official grading.'),
    'study_network_centrality': ('Pillars of the network & bottlenecks',
        'The hubs of every ṭabaqa, the men through whom most of each Imam’s corpus passes, and the great inter-generation bridges.'),
    'study_nisba_geography': ('Atlas of geographic nisbas',
        'Transmission’s migration from Kūfa to Qum and Baghdad — geographic nisbas across the ṭabaqāt, and each city’s school and its appraisal.'),
    'study_ayat_narrators': ('The Qurʾān in transmission',
        'Qurʾān citations in the ḥadīth books joined to their chains: which sūras each narrator’s and each Imam’s corpus carries.'),
}
STUDY_VARIANT_EN = {'ثنائية': 'bigrams', 'ثلاثية': 'trigrams', 'رباعية': 'four-grams'}
STUDY_BADGE_EN = {'تقريبيّ — مستوى المجلّد': 'approximate — volume level'}
def study_title(it):
    return STUDY_EN[it['file']][0] if (is_en() and it['file'] in STUDY_EN) else it['title']
def study_desc(it):
    return STUDY_EN[it['file']][1] if (is_en() and it['file'] in STUDY_EN) else it['desc']
def study_badge(b):
    return STUDY_BADGE_EN.get(b, b) if is_en() else b
def variant_label(v):
    return STUDY_VARIANT_EN.get(v, v) if is_en() else v
