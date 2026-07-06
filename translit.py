"""translit.py — deterministic Arabic→Latin transliteration for narrator/book names.

Design goals (per project rule: authentic, never invented):
  • A curated ALA-LC-style dictionary of the recurring name-elements (given names, particles,
    nisbas) covers ~90%+ of all name-token occurrences with correct, consistent vocalization.
  • Structural rules compose them: «بن»→"b.", «ابن»→"Ibn", «أبو/أبي»→"Abū/Abī", «عبد X»→"ʿAbd al-X",
    the definite article «ال»→"al-", kinship/honorific tokens.
  • Rare unknown tokens fall back to a consonant-skeleton transliteration (rough but readable).
    The Arabic form is ALWAYS shown alongside in the app, so fallback imperfections are low-stakes.

Pure, dependency-free. translit_name(arabic) works on standard names, aliases, book-entry
headwords, and isnad segments alike. Nothing is machine-"guessed" for the curated core.
"""
import re

# ---- normalization (diacritics off, orthographic unification) ----
def _is_diac(ch):
    o = ord(ch)
    return ((0x0610 <= o <= 0x061A) or (0x064B <= o <= 0x065F) or o == 0x0670
            or (0x06D6 <= o <= 0x06ED) or o == 0x0640)

def _norm(s):
    out = []
    for ch in s or '':
        if _is_diac(ch): continue
        if ch in 'أإآٱ': ch = 'ا'
        elif ch in 'ىی': ch = 'ي'
        elif ch == 'ک': ch = 'ك'
        elif ch == 'ة': ch = 'ه'
        elif ch == 'ؤ': ch = 'و'
        elif ch == 'ئ': ch = 'ي'
        out.append(ch)
    return ''.join(out)

# ---- curated element dictionary (normalized token -> transliteration) ----
# Given names, particles and honorifics. Correct classical vocalization; ~90%+ token coverage.
ELEM = {
    # particles / structure
    'بن': 'b.', 'ابن': 'Ibn', 'ابو': 'Abū', 'ابي': 'Abī', 'اب': 'Abū',
    'ام': 'Umm', 'بنت': 'bint', 'ابنه': 'ibna', 'اخ': 'Akhū', 'اخو': 'Akhū',
    'عم': 'ʿamm', 'عمه': 'ʿammihi', 'ابيه': 'abīhi', 'ابوه': 'abūhu', 'اخيه': 'akhīhi',
    'جد': 'jadd', 'جده': 'jaddihi', 'والد': 'wālid', 'والده': 'wāliduhu', 'مولي': 'mawlā',
    'صاحب': 'ṣāḥib', 'غير': 'ghayr', 'من': 'min', 'عن': 'ʿan', 'او': 'aw', 'و': 'wa',
    'عليه': 'ʿalayhi', 'عليها': 'ʿalayhā', 'السلام': 'al-salām', 'ع': '(a)', 'ص': '(ṣ)',
    'رهط': 'raht', 'الجماعه': 'al-jamāʿa', 'المذكورون': 'al-madhkūrūn',
    # theophorics second element (after عبد)
    'الله': 'Allāh', 'الرحمن': 'al-Raḥmān', 'الرحيم': 'al-Raḥīm', 'العزيز': 'al-ʿAzīz',
    'الملك': 'al-Malik', 'الكريم': 'al-Karīm', 'الوهاب': 'al-Wahhāb', 'الحميد': 'al-Ḥamīd',
    'الجبار': 'al-Jabbār', 'الاعلي': 'al-Aʿlā', 'الغفار': 'al-Ghaffār', 'الصمد': 'al-Ṣamad',
    'العظيم': 'al-ʿAẓīm', 'الواحد': 'al-Wāḥid', 'الخالق': 'al-Khāliq', 'الحق': 'al-Ḥaqq',
    # common given names
    'محمد': 'Muḥammad', 'احمد': 'Aḥmad', 'علي': 'ʿAlī', 'الحسن': 'al-Ḥasan', 'الحسين': 'al-Ḥusayn',
    'جعفر': 'Jaʿfar', 'ابراهيم': 'Ibrāhīm', 'عبد': 'ʿAbd', 'عبيد': 'ʿUbayd',
    'اسماعيل': 'Ismāʿīl', 'اسحاق': 'Isḥāq', 'موسي': 'Mūsā', 'عيسي': 'ʿĪsā', 'يحيي': 'Yaḥyā',
    'يوسف': 'Yūsuf', 'يعقوب': 'Yaʿqūb', 'يونس': 'Yūnus', 'هارون': 'Hārūn', 'سليمان': 'Sulaymān',
    'سعيد': 'Saʿīd', 'سعد': 'Saʿd', 'عمرو': 'ʿAmr', 'عمر': 'ʿUmar', 'عثمان': 'ʿUthmān',
    'عمران': 'ʿImrān', 'عمار': 'ʿAmmār', 'عماره': 'ʿUmāra', 'زيد': 'Zayd', 'يزيد': 'Yazīd',
    'زياد': 'Ziyād', 'خالد': 'Khālid', 'داود': 'Dāwūd', 'صالح': 'Ṣāliḥ', 'العباس': 'al-ʿAbbās',
    'الفضل': 'al-Faḍl', 'بكر': 'Bakr', 'حماد': 'Ḥammād', 'الحارث': 'al-Ḥārith', 'حمزه': 'Ḥamza',
    'حفص': 'Ḥafṣ', 'حكيم': 'Ḥakīm', 'حبيب': 'Ḥabīb', 'حسان': 'Ḥassān', 'سالم': 'Sālim',
    'سلمه': 'Salama', 'سهل': 'Sahl', 'مسلم': 'Muslim', 'منصور': 'Manṣūr', 'معاويه': 'Muʿāwiya',
    'مالك': 'Mālik', 'ميمون': 'Maymūn', 'نصر': 'Naṣr', 'هشام': 'Hishām', 'هاشم': 'Hāshim',
    'وهب': 'Wahb', 'الوليد': 'al-Walīd', 'ايوب': 'Ayyūb', 'شعيب': 'Shuʿayb', 'صفوان': 'Ṣafwān',
    'طلحه': 'Ṭalḥa', 'طالب': 'Ṭālib', 'قيس': 'Qays', 'كثير': 'Kathīr', 'بشر': 'Bishr',
    'بشير': 'Bashīr', 'ثابت': 'Thābit', 'جابر': 'Jābir', 'جميل': 'Jamīl', 'درست': 'Durust',
    'رفاعه': 'Rifāʿa', 'زراره': 'Zurāra', 'زكريا': 'Zakariyyā', 'سفيان': 'Sufyān', 'سنان': 'Sinān',
    'سماعه': 'Samāʿa', 'شبيب': 'Shabīb', 'ضريس': 'Ḍurays', 'عاصم': 'ʿĀṣim', 'عامر': 'ʿĀmir',
    'عباد': 'ʿAbbād', 'عقبه': 'ʿUqba', 'العلاء': 'al-ʿAlāʾ', 'علاء': 'ʿAlāʾ', 'فضاله': 'Faḍāla',
    'القاسم': 'al-Qāsim', 'قاسم': 'Qāsim', 'مثني': 'Muthannā', 'محبوب': 'Maḥbūb', 'مروان': 'Marwān',
    'مغيره': 'Mughīra', 'المغيره': 'al-Mughīra', 'منذر': 'Mundhir', 'المنذر': 'al-Mundhir',
    'نوح': 'Nūḥ', 'هلال': 'Hilāl', 'وائل': 'Wāʾil', 'ورد': 'Ward', 'ياسر': 'Yāsir',
    'بريد': 'Burayd', 'بكير': 'Bukayr', 'حريز': 'Ḥarīz', 'فضيل': 'Fuḍayl', 'الفضيل': 'al-Fuḍayl',
    'الحكم': 'al-Ḥakam', 'حكم': 'Ḥakam', 'الربيع': 'al-Rabīʿ', 'ربيع': 'Rabīʿ', 'اعين': 'Aʿyan',
    'المفضل': 'al-Mufaḍḍal', 'مفضل': 'Mufaḍḍal', 'ادريس': 'Idrīs', 'انس': 'Anas',
    'اسباط': 'Asbāṭ', 'اسد': 'Asad', 'اسلم': 'Aslam', 'اشعث': 'Ashʿath', 'اصبغ': 'Aṣbagh',
    'بجيل': 'Bujayl', 'جبله': 'Jabala', 'جراح': 'Jarrāḥ', 'جندب': 'Jundab', 'حجاج': 'Ḥajjāj',
    'حذيفه': 'Ḥudhayfa', 'حسن': 'Ḥasan', 'حسين': 'Ḥusayn', 'حمدان': 'Ḥamdān', 'حمران': 'Ḥumrān',
    'حنان': 'Ḥanān', 'خلف': 'Khalaf', 'خيثمه': 'Khaythama', 'ذريح': 'Dharīḥ', 'رباط': 'Ribāṭ',
    'زرعه': 'Zurʿa', 'زهير': 'Zuhayr', 'سابور': 'Sābūr', 'سدير': 'Sadīr', 'سماك': 'Simāk',
    'سندي': 'Sindī', 'سوره': 'Sawra', 'سيف': 'Sayf', 'شمر': 'Shimr', 'صباح': 'Ṣabāḥ',
    'صدقه': 'Ṣadaqa', 'ضحاك': 'Ḍaḥḥāk', 'طاهر': 'Ṭāhir', 'طريف': 'Ṭarīf', 'ظبيان': 'Ẓabyān',
    'عبيده': 'ʿUbayda', 'عبده': 'ʿAbda', 'عدي': 'ʿAdī', 'عطيه': 'ʿAṭiyya', 'عطاء': 'ʿAṭāʾ',
    'عقيل': 'ʿAqīl', 'عكرمه': 'ʿIkrima', 'علقمه': 'ʿAlqama', 'عمير': 'ʿUmayr', 'عنبسه': 'ʿAnbasa',
    'عون': 'ʿAwn', 'غالب': 'Ghālib', 'غياث': 'Ghiyāth', 'فرات': 'Furāt', 'فروه': 'Farwa',
    'فطر': 'Fiṭr', 'فليح': 'Fulayḥ', 'قتاده': 'Qatāda', 'كامل': 'Kāmil', 'كردين': 'Kurdīn',
    'كليب': 'Kulayb', 'كميل': 'Kumayl', 'لوط': 'Lūṭ', 'ليث': 'Layth', 'مبارك': 'Mubārak',
    'مثيره': 'Muthīra', 'مدرك': 'Mudrik', 'مرازم': 'Marāzim', 'مرحوم': 'Marḥūm', 'مسعده': 'Masʿada',
    'مسعود': 'Masʿūd', 'مسكان': 'Miskān', 'مسمع': 'Mismaʿ', 'معلي': 'Muʿallā', 'معمر': 'Muʿammar',
    'معروف': 'Maʿrūf', 'مقاتل': 'Muqātil', 'مندل': 'Mindal', 'مهران': 'Mihrān', 'مهزم': 'Mihzam',
    'ميسر': 'Muyassar', 'ميسره': 'Maysara', 'نجيه': 'Najiyya', 'نعمان': 'Nuʿmān', 'نعيم': 'Nuʿaym',
    'هارونيه': 'Hārūniyya', 'هذيل': 'Hudhayl', 'هلقام': 'Hilqām', 'واصل': 'Wāṣil',
    'وليد': 'Walīd', 'يسع': 'Yasaʿ', 'يقطين': 'Yaqṭīn', 'ابان': 'Abān', 'اباذر': 'Abā Dharr',
    'الاعمش': 'al-Aʿmash', 'العجلان': 'al-ʿAjlān', 'العلا': 'al-ʿAlāʾ', 'المثني': 'al-Muthannā',
    'الطيار': 'al-Ṭayyār', 'الجارود': 'al-Jārūd', 'الاحول': 'al-Aḥwal', 'الازرق': 'al-Azraq',
    'الاصم': 'al-Aṣamm', 'الاسود': 'al-Aswad', 'البختري': 'al-Bakhtarī', 'الجهم': 'al-Jahm',
    'الخطاب': 'al-Khaṭṭāb', 'السري': 'al-Sarī', 'الطفيل': 'al-Ṭufayl', 'العاص': 'al-ʿĀṣ',
    'الغريفي': 'al-Gharīfī', 'المعلي': 'al-Muʿallā', 'المعروف': 'al-Maʿrūf', 'الهيثم': 'al-Haytham',
    'هيثم': 'Haytham', 'الاعرج': 'al-Aʿraj', 'السجاد': 'al-Sajjād', 'الباقر': 'al-Bāqir',
    'الصادق': 'al-Ṣādiq', 'الكاظم': 'al-Kāẓim', 'الرضا': 'al-Riḍā', 'الجواد': 'al-Jawād',
    'الهادي': 'al-Hādī', 'العسكري': 'al-ʿAskarī', 'النبي': 'al-Nabī', 'الصديق': 'al-Ṣiddīq',
    # nisbas (al- + root + ī); curated for the frequent ones
    'الكوفي': 'al-Kūfī', 'القمي': 'al-Qummī', 'البصري': 'al-Baṣrī', 'البغدادي': 'al-Baghdādī',
    'الرازي': 'al-Rāzī', 'النيسابوري': 'al-Nīsābūrī', 'الاسدي': 'al-Asadī', 'الازدي': 'al-Azdī',
    'الانصاري': 'al-Anṣārī', 'الهمداني': 'al-Hamdānī', 'الاشعري': 'al-Ashʿarī', 'البجلي': 'al-Bajalī',
    'الجعفي': 'al-Juʿfī', 'التميمي': 'al-Tamīmī', 'القرشي': 'al-Qurashī', 'الهاشمي': 'al-Hāshimī',
    'العلوي': 'al-ʿAlawī', 'الكندي': 'al-Kindī', 'العبدي': 'al-ʿAbdī', 'الطائي': 'al-Ṭāʾī',
    'الشيباني': 'al-Shaybānī', 'النخعي': 'al-Nakhaʿī', 'الواسطي': 'al-Wāsiṭī', 'الثقفي': 'al-Thaqafī',
    'المدني': 'al-Madanī', 'المكي': 'al-Makkī', 'الحلبي': 'al-Ḥalabī', 'الحضرمي': 'al-Ḥaḍramī',
    'الخزاز': 'al-Khazzāz', 'الصيرفي': 'al-Ṣayrafī', 'العطار': 'al-ʿAṭṭār', 'الخثعمي': 'al-Khathʿamī',
    'السلمي': 'al-Sulamī', 'الجهني': 'al-Juhanī', 'العجلي': 'al-ʿIjlī', 'المرادي': 'al-Murādī',
    'النهدي': 'al-Nahdī', 'الخراساني': 'al-Khurāsānī', 'السجستاني': 'al-Sijistānī', 'الطبري': 'al-Ṭabarī',
    'الحميري': 'al-Ḥimyarī', 'الجعفري': 'al-Jaʿfarī', 'العامري': 'al-ʿĀmirī', 'الغنوي': 'al-Ghanawī',
    'السكوني': 'al-Sakūnī', 'الضبي': 'al-Ḍabbī', 'المخزومي': 'al-Makhzūmī', 'الاموي': 'al-Umawī',
    'القطان': 'al-Qaṭṭān', 'الوشاء': 'al-Washshāʾ', 'الاحمسي': 'al-Aḥmasī', 'السابري': 'al-Sābirī',
    'البارقي': 'al-Bāriqī', 'الخزاعي': 'al-Khuzāʿī', 'الغفاري': 'al-Ghifārī', 'الزهري': 'al-Zuhrī',
    'الطحان': 'al-Ṭaḥḥān', 'الجمال': 'al-Jammāl', 'اللؤلؤي': 'al-Luʾluʾī', 'البزاز': 'al-Bazzāz',
    'البزنطي': 'al-Bazanṭī', 'الحذاء': 'al-Ḥadhdhāʾ', 'السراج': 'al-Sarrāj', 'النوفلي': 'al-Nawfalī',
    'السكري': 'al-Sukkarī', 'الديلمي': 'al-Daylamī', 'المزني': 'al-Muzanī', 'الجوهري': 'al-Jawharī',
    'العجمي': 'al-ʿAjamī', 'القلانسي': 'al-Qalānisī', 'الكاتب': 'al-Kātib', 'الطيالسي': 'al-Ṭayālisī',
    'الحناط': 'al-Ḥannāṭ', 'الخياط': 'al-Khayyāṭ', 'القاشاني': 'al-Qāshānī', 'الاصبهاني': 'al-Aṣbahānī',
    'المدائني': 'al-Madāʾinī', 'السمان': 'al-Sammān', 'اللحام': 'al-Laḥḥām', 'المسلي': 'al-Maslī',
    'الاحمري': 'al-Aḥmarī', 'الرواسي': 'al-Ruwāsī', 'الطاطري': 'al-Ṭāṭarī', 'القداح': 'al-Qaddāḥ',
    'النرسي': 'al-Narsī', 'العنزي': 'al-ʿAnazī', 'الجريري': 'al-Jarīrī', 'الكاهلي': 'al-Kāhilī',
    'الجرمي': 'al-Jarmī', 'الفزاري': 'al-Fazārī', 'الباهلي': 'al-Bāhilī', 'الحجازي': 'al-Ḥijāzī',
    'الحماني': 'al-Ḥimmānī', 'الخولاني': 'al-Khawlānī', 'الرقي': 'al-Raqqī', 'الشعيري': 'al-Shaʿīrī',
    'الابزاري': 'al-Abzārī', 'المنقري': 'al-Minqarī', 'المسمعي': 'al-Mismaʿī', 'القندي': 'al-Qandī',
    'بياع': 'bayyāʿ', 'الاعلي': 'al-Aʿlā', 'صاحبها': 'ṣāḥibuhā',
    # tail-token corrections (frequent names/nisbas whose fallback misreads)
    'الكليني': 'al-Kulaynī', 'حيان': 'Ḥayyān', 'التيمي': 'al-Taymī', 'الفيض': 'al-Fayḍ',
    'نافع': 'Nāfiʿ', 'البهراني': 'al-Bahrānī', 'الاشتري': 'al-Ashtarī', 'شيبه': 'Shayba',
    'نعامه': 'Naʿāma', 'اسامه': 'Usāma', 'الفريابي': 'al-Firyābī', 'النهشلي': 'al-Nahshalī',
    'الجرجاني': 'al-Jurjānī', 'مسافر': 'Musāfir', 'حجر': 'Ḥajar', 'الساوي': 'al-Sāwī',
    'الدهني': 'al-Duhnī', 'صهيب': 'Ṣuhayb', 'الصيداني': 'al-Ṣaydānī', 'المقدسي': 'al-Maqdisī',
    'الزراري': 'al-Zurārī', 'شاذان': 'Shādhān', 'يسار': 'Yasār', 'نهيك': 'Nuhayk',
    'رزين': 'Razīn', 'ابصير': 'Abī Baṣīr', 'بصير': 'Baṣīr', 'الجمال': 'al-Jammāl',
    'الطاطري': 'al-Ṭāṭarī', 'حبيش': 'Ḥubaysh', 'اباذي': 'Ābādhī', 'الفقيه': 'al-Faqīh',
    'الهمذاني': 'al-Hamadhānī', 'العجلي': 'al-ʿIjlī', 'الجهني': 'al-Juhanī', 'الدباج': 'al-Dabbāj',
    'المقري': 'al-Muqriʾ', 'الطنافسي': 'al-Ṭanāfisī',
}
# ELEM keys must be in NORMALIZED form (input is normalized before lookup); apply it once.
ELEM = {_norm(k): v for k, v in ELEM.items()}

# ---- consonant-skeleton fallback for unknown tokens ----
_CONS = {'ا': 'ā', 'ب': 'b', 'ت': 't', 'ث': 'th', 'ج': 'j', 'ح': 'ḥ', 'خ': 'kh',
         'د': 'd', 'ذ': 'dh', 'ر': 'r', 'ز': 'z', 'س': 's', 'ش': 'sh', 'ص': 'ṣ',
         'ض': 'ḍ', 'ط': 'ṭ', 'ظ': 'ẓ', 'ع': 'ʿ', 'غ': 'gh', 'ف': 'f', 'ق': 'q',
         'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n', 'ه': 'h', 'و': 'w', 'ي': 'y',
         'ء': 'ʾ'}
_LONG = {'ا': 'ā', 'و': 'ū', 'ي': 'ī'}
_VOWELISH = set('āūīaeiouʿ')

def _fallback(tok):
    """Rough but readable: map consonants, long vowels for ا/و/ي, insert 'a' between bare consonants."""
    if not tok: return ''
    chars = list(tok)
    out = []
    for i, ch in enumerate(chars):
        if ch in _LONG and i > 0:
            out.append(_LONG[ch]); continue
        c = _CONS.get(ch, '')
        if not c: continue
        # insert a helper short vowel between two consonants that would otherwise collide
        if out and out[-1] and out[-1][-1] not in _VOWELISH and c[0] not in _VOWELISH and c != 'ʿ':
            out.append('a')
        out.append(c)
    s = ''.join(out)
    return s[:1].upper() + s[1:] if s else s

def _translit_token(tok, first):
    if tok in ELEM:
        return ELEM[tok]
    if tok == 'الله':
        return 'Allāh'
    if len(tok) > 2 and tok.startswith('ال'):
        root = tok[2:]
        r = ELEM.get(root) or _fallback(root)
        r = r[:1].upper() + r[1:] if r else r
        return 'al-' + r
    return _fallback(tok)

# theophoric second-elements that bind to a preceding عبد
_THEO = {_norm(x) for x in ('الله', 'الرحمن', 'الرحيم', 'العزيز', 'الملك', 'الكريم', 'الوهاب',
         'الحميد', 'الجبار', 'الأعلى', 'الغفار', 'الصمد', 'العظيم', 'الواحد', 'الخالق', 'الحق')}

def translit_name(name):
    """Arabic name/segment -> Latin (ALA-LC-ish). Deterministic; empty in -> empty out."""
    if not name: return ''
    norm = _norm(name)
    # keep separators (comma is used in some alias forms)
    norm = norm.replace('،', ',').replace('؛', ';')
    toks = norm.split()
    out = []
    i = 0
    while i < len(toks):
        tok = toks[i].strip(',;')
        trail = toks[i][len(tok):]
        if not tok:
            i += 1; continue
        # عبد + theophoric  ->  ʿAbd Allāh / ʿAbd al-Raḥmān
        if tok in ('عبد', 'عبيد') and i + 1 < len(toks) and toks[i + 1] in _THEO:
            base = 'ʿAbd' if tok == 'عبد' else 'ʿUbayd'
            out.append(base + ' ' + ELEM[toks[i + 1]] + trail)
            i += 2; continue
        piece = _translit_token(tok, first=(i == 0))
        out.append(piece + trail)
        i += 1
    return ' '.join(out).replace(' ,', ',').strip()
