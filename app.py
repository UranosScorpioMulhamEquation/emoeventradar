from datetime import datetime, date, time
import os
from typing import Dict, List, Tuple, Any
import base64
import geonamescache
import pytz
import streamlit as st
import swisseph as swe
from timezonefinder import TimezoneFinder

# ==========================================
# 0. تهيئة الصفحة ومسار ملفات الـ Ephemeris
# ==========================================
st.set_page_config(
    page_title="النظام المتقدم لتنجيم الحدث العاطفي",
    layout="wide",
)

EPHE_PATH = "./ephe"
if not os.path.exists(EPHE_PATH):
    os.makedirs(EPHE_PATH)

swe.set_ephe_path(EPHE_PATH)

st.title("النظام المتقدم لتحليل خارطة الحدث العاطفي 💖 ( برمجة الفلكي استرو رادار )")
st.markdown("تحليل تنجيمي عميق يغطي دلالات الانفصال، الانسحاب، المشاجرات، الأسباب الدقيقة (خيانة، إهمال، تواصل، احتياجات)، وتحديد أدوار الأطراف الثالثة بدقة مع إدخال أهم الكويكبات و تحديد الوقت المتوقع للرجوع.")
st.markdown("---")

# ==========================================
# 1. خدمات البيانات الجغرافية والزمنية
# ==========================================
@st.cache_data
def load_geo_data() -> Tuple[geonamescache.GeonamesCache, Dict[str, str], List[str], Dict[str, List[Dict[str, Any]]]]:
    gc = geonamescache.GeonamesCache()
    countries = gc.get_countries()
    cities = gc.get_cities()

    country_map = {c["name"]: code for code, c in countries.items()}
    sorted_countries = sorted(list(country_map.keys()))

    cities_by_country: Dict[str, List[Dict[str, Any]]] = {}
    for c_code in country_map.values():
        c_cities = [city for city in cities.values() if city["countrycode"] == c_code]
        c_cities_sorted = sorted(c_cities, key=lambda x: x["population"], reverse=True)
        cities_by_country[c_code] = c_cities_sorted

    return gc, country_map, sorted_countries, cities_by_country

gc, country_map, country_list, cities_by_country = load_geo_data()

@st.cache_resource
def get_tz_finder() -> TimezoneFinder:
    return TimezoneFinder()

tf = get_tz_finder()

def get_utc_julian_day(date_obj: date, time_obj: time, tz_str: str) -> float:
    local_tz = pytz.timezone(tz_str)
    dt = datetime.combine(date_obj, time_obj)
    local_dt = local_tz.localize(dt)
    utc_dt = local_dt.astimezone(pytz.utc)
    return swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0,
    )

# ==========================================
# القواميس الفلكية والكويكبات العاطفية
# ==========================================
SIGN_NAMES = [
    "الحمل", "الثور", "الجوزاء", "السرطان", "الأسد", "العذراء",
    "الميزان", "العقرب", "القوس", "الجدي", "الدلو", "الحوت"
]

SIGN_MODALITY = {
    "الحمل": "كاردينالي", "الثور": "ثابت", "الجوزاء": "متحرك",
    "السرطان": "كاردينالي", "الأسد": "ثابت", "العذراء": "متحرك",
    "الميزان": "كاردينالي", "العقرب": "ثابت", "القوس": "متحرك",
    "الجدي": "كاردينالي", "الدلو": "ثابت", "الحوت": "متحرك"
}

RULERS = {
    "الحمل": "المريخ", "الثور": "الزهرة", "الجوزاء": "عطارد",
    "السرطان": "القمر", "الأسد": "الشمس", "العذراء": "عطارد",
    "الميزان": "الزهرة", "العقرب": "المريخ", "القوس": "المشتري",
    "الجدي": "زحل", "الدلو": "زحل", "الحوت": "المشتري"
}

EVENT_TYPES = {
    "1 - حدث فراق (Separation)": "فراق",
    "2 - حدث لقاء (Meeting)": "لقاء",
    "3 - حدث مشاجرة (Dispute/Fight)": "مشاجرة",
    "4 - حدث عدم تواصل مؤقت / انسحاب (Withdrawal)": "انسحاب"
}

# ==========================================
# الشريط الجانبي للإدخالات
# ==========================================
st.sidebar.header("⚙️ إعدادات حدث اللحظة العاطفية")

selected_event_key = st.sidebar.selectbox(
    "اختر غرض الحدث العاطفي:", list(EVENT_TYPES.keys())
)
event_purpose = EVENT_TYPES[selected_event_key]

now_local = datetime.now()
ev_date = st.sidebar.date_input("تاريخ وقوع الحدث:", value=now_local.date())
ev_time = st.sidebar.time_input("وقت وقوع الحدث (المحلي):", value=now_local.time())

selected_country_name = st.sidebar.selectbox("اختر الدولة:", country_list, index=country_list.index("United Arab Emirates") if "United Arab Emirates" in country_list else 0)
country_code = country_map[selected_country_name]

country_cities = cities_by_country.get(country_code, [])
city_names = [c["name"] for c in country_cities]

if city_names:
    selected_city_name = st.sidebar.selectbox("اختر المدينة:", city_names)
    selected_city = next(c for c in country_cities if c["name"] == selected_city_name)
    lat = float(selected_city["latitude"])
    lon = float(selected_city["longitude"])
    tz_str = tf.timezone_at(lng=lon, lat=lat)
    if not tz_str:
        tz_str = "UTC"
else:
    lat = st.sidebar.number_input("خط العرض (Latitude):", value=25.2048, format="%.4f")
    lon = st.sidebar.number_input("خط الطول (Longitude):", value=55.2708, format="%.4f")
    tz_str = st.sidebar.text_input("المنطقة الزمنية (Timezone):", value="Asia/Dubai")

st.sidebar.write(f"🌍 الإحداثيات: {lat:.2f}, {lon:.2f} | التوقيت: {tz_str}")

def get_sign_and_deg(lon_deg):
    sign_idx = int(lon_deg / 30)
    deg_in_sign = lon_deg % 30
    sign_name = SIGN_NAMES[sign_idx % 12]
    return sign_name, deg_in_sign

if st.button("🔮 تحليل خريطة الحدث العاطفي"):
    try:
        jd = get_utc_julian_day(ev_date, ev_time, tz_str)
    except Exception as e:
        st.error(f"خطأ في حساب التوقيت والمنطقة الزمنية: {e}")
        st.stop()

    # الكواكب الأساسية والخارجية المؤثرة نفسياً
    planets = {
        "الشمس": swe.SUN,
        "القمر": swe.MOON,
        "عطارد": swe.MERCURY,
        "الزهرة": swe.VENUS,
        "المريخ": swe.MARS,
        "المشتري": swe.JUPITER,
        "زحل": swe.SATURN,
        "أورانوس (Uranus)": swe.URANUS,
        "نبتون (Neptune)": swe.NEPTUNE,
        "بلوتو (Pluto)": swe.PLUTO,
        "تشيرون (Chiron)": swe.CHIRON,
        "سيريس (Ceres)": swe.CERES,
        "بالاس (Pallas)": swe.PALLAS,
        "جونو (Juno)": swe.JUNO,
        "فيستا (Vesta)": swe.VESTA,
    }

    ast_offset = getattr(swe, 'SE_AST_OFFSET', 10000)
    asteroid_ids = {
        "إيروس (Eros - الشغف والرغبة)": ast_offset + 433,
        "بسايكي (Psyche - الارتباط الروحي)": ast_offset + 16,
        "أمور (Amor - الحب الأفلاطوني)": ast_offset + 1221
    }

    planet_data = {}
    for p_name, p_id in planets.items():
        res, _ = swe.calc_ut(jd, p_id)
        planet_data[p_name] = {
            "lon": res[0],
            "sign": get_sign_and_deg(res[0])[0],
            "deg": get_sign_and_deg(res[0])[1],
            "retro": res[3] < 0,
            "speed": res[3]
        }

    for a_name, a_id in asteroid_ids.items():
        try:
            res, _ = swe.calc_ut(jd, a_id)
            planet_data[a_name] = {
                "lon": res[0],
                "sign": get_sign_and_deg(res[0])[0],
                "deg": get_sign_and_deg(res[0])[1],
                "retro": res[3] < 0,
                "speed": res[3]
            }
        except:
            continue

    # حساب البيوت بنظام ريغومونتانوس الكلاسيكي
    houses_cusps, ascmc = swe.houses_ex(jd, lat, lon, b"R")
    asc_lon = houses_cusps[0]
    asc_sign, asc_deg = get_sign_and_deg(asc_lon)

    def find_house(p_lon):
        for i in range(12):
            c_start = houses_cusps[i]
            c_end = houses_cusps[(i + 1) % 12]
            if c_start < c_end:
                if c_start <= p_lon < c_end:
                    return i + 1
            else:
                if p_lon >= c_start or p_lon < c_end:
                    return i + 1
        return 1

    for p_name in planet_data:
        planet_data[p_name]["house"] = find_house(planet_data[p_name]["lon"])

    party1_ruler = RULERS[asc_sign]
    desc_cusp_lon = houses_cusps[6]
    desc_sign, _ = get_sign_and_deg(desc_cusp_lon)
    party2_ruler = RULERS[desc_sign]

    st.success("✨ تم حساب الخريطة الفلكية بنجاح عبر محرك Swiss Ephemeris وفق نظام ريغومونتانوس!")

    # عرض المؤشرات الأساسية
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### 🧑 الطرف الأول (صاحب الحدث / الطالع)")
        st.write(f"- **الطالع:** {asc_sign} ({asc_deg:.2f}°)")
        st.write(f"- **حاكم الطرف الأول:** {party1_ruler} (في البرج: {planet_data[party1_ruler]['sign']}، البيت {planet_data[party1_ruler]['house']})")
        st.write(f"- **القمر (المشاعر الحالية):** {planet_data['القمر']['sign']} ({planet_data['القمر']['deg']:.2f}°) في البيت {planet_data['القمر']['house']}")
        if "إيروس (Eros - الشغف والرغبة)" in planet_data:
            st.write(f"- **إيروس (الشغف):** {planet_data['إيروس (Eros - الشغف والرغبة)']['sign']} (البيت {planet_data['إيروس (Eros - الشغف والرغبة)']['house']})")

    with col2:
        st.markdown(f"### 👩‍❤️‍👨 الطرف الثاني (الشريك / البيت السابع)")
        st.write(f"- **رأس السابع:** {desc_sign}")
        st.write(f"- **حاكم الطرف الثاني:** {party2_ruler} (في البرج: {planet_data[party2_ruler]['sign']}، البيت {planet_data[party2_ruler]['house']})")
        st.write(f"- **الزهرة (دلالة الحب):** {planet_data['الزهرة']['sign']} (البيت {planet_data['الزهرة']['house']})")
        if "بسايكي (Psyche - الارتباط الروحي)" in planet_data:
            st.write(f"- **بسايكي (الارتباط):** {planet_data['بسايكي (Psyche - الارتباط الروحي)']['sign']} (البيت {planet_data['بسايكي (Psyche - الارتباط الروحي)']['house']})")

    st.markdown("---")
    st.markdown("### 🔬 محرك التشخيص النفسي والفلكي للأسباب (Detailed Diagnostic Engine)")

    def check_aspect(lon1, lon2):
        diff = abs(lon1 - lon2) % 360
        if diff > 180:
            diff = 360 - diff
        
        if abs(diff - 120) <= 6.0:
            return True, "تثليث (Trine)", "positive", abs(diff - 120)
        elif abs(diff - 60) <= 6.0:
            return True, "تسديس (Sextile)", "positive", abs(diff - 60)
        elif abs(diff - 0) <= 8.0:
            return True, "اقتران (Conjunction)", "neutral", abs(diff - 0)
        elif abs(diff - 90) <= 6.0:
            return True, "تربيع (Square)", "negative", abs(diff - 90)
        elif abs(diff - 180) <= 6.0:
            return True, "مقابلة (Opposition)", "negative", abs(diff - 180)
        return False, None, None, 0.0

    p1_lon = planet_data[party1_ruler]["lon"]
    p2_lon = planet_data[party2_ruler]["lon"]
    venus_lon = planet_data["الزهرة"]["lon"]
    mars_lon = planet_data["المريخ"]["lon"]
    mercury_lon = planet_data["عطارد"]["lon"]
    moon_lon = planet_data["القمر"]["lon"]
    saturn_lon = planet_data["زحل"]["lon"]
    neptune_lon = planet_data["نبتون (Neptune)"]["lon"]
    pluto_lon = planet_data["بلوتو (Pluto)"]["lon"]

    has_aspect, asp_name, asp_type, asp_orb = check_aspect(p1_lon, p2_lon)
    moon_aspect_p2, moon_asp_name, moon_asp_type, moon_orb = check_aspect(p2_lon, moon_lon)

    # تحليل دقيق للأسباب بناءً على الاتصالات والبيوت والكويكبات
    detailed_causes = []
    
    # 1. فحص سوء التواصل (Mercury aspects or Mercury in 3rd/6th/12th or retrograde)
    merc_sat_asp, _, _, _ = check_aspect(mercury_lon, saturn_lon)
    merc_mars_asp, _, m_asp_type, _ = check_aspect(mercury_lon, mars_lon)
    if planet_data["عطارد"]["retro"] or merc_sat_asp or (merc_mars_asp and m_asp_type == "negative"):
        detailed_causes.append({
            "category": "أسلوب تواصل غير مقبول أو حاد",
            "desc": "وجود عطارد في وضعية متراجعة أو تحت ضغط زحل والمريخ يشير إلى جارحة في الكلام، جفاف في الحوار، أو سوء فهم لفظي متكرر تسبب في تأجيج الخلاف."
        })

    # 2. فحص سوء الفهم (Neptune afflictions to Mercury or Moon)
    nep_merc_asp, _, _, _ = check_aspect(mercury_lon, neptune_lon)
    if nep_merc_asp or planet_data["عطارد"]["house"] in [12, 8]:
        detailed_causes.append({
            "category": "سوء فهم وضبابية في النوايا",
            "desc": "تأثير نبتون على أدوات التواصل يوضح وجود أوهام، تفسيرات خاطئة للمواقف، أو إخفاء مقصود للحقائق أدى لضياع المعنى الحقيقي بين الطرفين."
        })

    # 3. فحص الخيانة أو اكتشاف سر (Pluto/Neptune in 8th/12th or hard aspect to Venus/Moon)
    plu_ven_asp, _, _, _ = check_aspect(venus_lon, pluto_lon)
    nep_ven_asp, _, _, _ = check_aspect(venus_lon, neptune_lon)
    h8_planets = [p for p, info in planet_data.items() if info["house"] == 8]
    h12_planets = [p for p, info in planet_data.items() if info["house"] == 12]
    if plu_ven_asp or nep_ven_asp or h8_planets or h12_planets:
        detailed_causes.append({
            "category": "اكتشاف سر، غموض، أو شبهة خيانة",
            "desc": f"تفعيل البيوت الثامنة والثانية عشرة أو اتصالات بلوتو ونبتون بالزهرة تكشف عن صدمة متعلقة بانكشاف أسرار مخفية، سلوكيات خلف الكواليس، أو شعور بالخيانة وفقدان الثقة المطلقة."
        })

    # 4. فحص الإهمال (Saturn or Sun afflicted in personal houses)
    sat_p1_asp, _, _, _ = check_aspect(p1_lon, saturn_lon)
    sat_p2_asp, _, _, _ = check_aspect(p2_lon, saturn_lon)
    if sat_p1_asp or sat_p2_asp or planet_data["زحل"]["house"] in [1, 7, 4]:
        detailed_causes.append({
            "category": "إهمال وبرود عاطفي",
            "desc": "ثقل طاقة زحل وضغوطه على حكام الخريطة تدل على البرود، الإهمال المتبادل، تهرب أحد الطرفين من المسؤوليات العاطفية، وتحول العلاقة إلى عبء ثقيل."
        })

    # 5. عدم تلبية الاحتياجات العاطفية (Moon/Venus afflicted by Saturn/Uranus)
    ura_moon_asp, _, _, _ = check_aspect(moon_lon, planet_data["أورانوس (Uranus)"]["lon"])
    if ura_moon_asp or moon_asp_type == "negative" or planet_data["القمر"]["house"] == 12:
        detailed_causes.append({
            "category": "عدم تلبية الاحتياجات العاطفية والنفسية",
            "desc": "وجود تباعد أو تربيعات قاسية تخص القمر والزهرة يعكس شعوراً عميقاً بالحرمان العاطفي، غياب الأمان النفسي، وعدم شعور الطرف الآخر بالتقدير العاطفي الكافي."
        })

    # 6. عدم تلبية الرغبات الجسدية (Mars/Eros afflicted)
    mars_ven_asp, _, m_v_type, _ = check_aspect(venus_lon, mars_lon)
    eros_name = "إيروس (Eros - الشغف والرغبة)"
    eros_afflicted = False
    if eros_name in planet_data:
        e_lon = planet_data[eros_name]["lon"]
        e_sat, _, _, _ = check_aspect(e_lon, saturn_lon)
        if e_sat or (mars_ven_asp and m_v_type == "negative"):
            eros_afflicted = True

    if eros_afflicted or (mars_ven_asp and m_v_type == "negative"):
        detailed_causes.append({
            "category": "عدم تلبية الرغبات والاندفاع الجسدي (البرود الجنسي)",
            "desc": "تعرض دلالات الشغف والرغبة (المريخ والزهرة وكويكب إيروس) لضغوط زحل أو زوايا الاحتكاك يوضح وجود فجوة في التوافق الحميمي، برود بدني، أو كبح للرغبات الطبيعية."
        })

    if not detailed_causes:
        detailed_causes.append({
            "category": "توتر عام وضغط ظروف",
            "desc": "الحدث ناتج عن تراكم ضغوط عامة غير معلنة أدت إلى تأزم الموقف بشكل مفاجئ."
        })

    st.info(f"📌 **طبيعة الحدث المحدد:** {selected_event_key}")
    
    st.markdown("#### ⚙️ التشخيص التفصيلي لأسباب الحدث العاطفي:")
    for cause in detailed_causes:
        st.markdown(f"- **{cause['category']}:** {cause['desc']}")

    # ==========================================
    # تحليل الأطراف الثالثة وتحديد هويتهم بدقة
    # ==========================================
    st.markdown("---")
    st.markdown("### 👥 تحليل الأطراف الثالثة وتحديد هويتهم")

    third_parties_found = []
    
    # بيت 3: إخوة، جيران، أو محيط قريب
    h3_planets = [p for p, info in planet_data.items() if info["house"] == 3]
    if h3_planets:
        third_parties_found.append(("العائلة القريبة / الإخوة أو الجيران (البيت الثالث)", f"وجود كواكب ({', '.join(h3_planets)}) يدل على تدخل الأقارب من الدرجة الثانية أو محيط السكن المباشر."))

    # بيت 4: الأهل والوالدين
    h4_planets = [p for p, info in planet_data.items() if info["house"] == 4]
    if h4_planets:
        third_parties_found.append(("الأهل والوالدين أو العائلة (البيت الرابع)", f"وجود كواكب ({', '.join(h4_planets)}) يشير إلى تدخل الأسر أو ضغوط العائلة والمنزل في مسار العلاقة."))

    # بيت 5: علاقة جانبية / معجب سابق / طرف ثالث عاطفي
    h5_planets = [p for p, info in planet_data.items() if info["house"] == 5]
    if h5_planets:
        third_parties_found.append(("طرف ثالث عاطفي / معجب / أو علاقة جانبية (البيت الخامس)", f"وجود كواكب ({', '.join(h5_planets)}) في بيت العواطف والملذات يدل على دخول شخص ثالث منافس أو وجود إلهاء عاطفي خارجي."))

    # بيت 7 (غير حاكم الشريك): شريك عمل أو طرف منافس معلن
    h7_other = [p for p, info in planet_data.items() if info["house"] == 7 and p != party2_ruler]
    if h7_other:
        third_parties_found.append(("شخص منافس أو طرف معلن (البيت السابع)", f"وجود كواكب إضافية ({', '.join(h7_other)}) يعكس وجود شخص آخر ينافس على مساحة الشريك."))

    # بيت 11: الأصدقاء والمحيط الاجتماعي
    h11_planets = [p for p, info in planet_data.items() if info["house"] == 11]
    if h11_planets:
        third_parties_found.append(("الأصدقاء وشبكة العلاقات الاجتماعية (البيت الحادي عشر)", f"وجود كواكب ({', '.join(h11_planets)}) يوضح دور الأصدقاء أو النصائح الخارجية في توجيه دفة الحدث."))

    # بيت 12: أعداء سريون أو طرف خفي
    h12_planets = [p for p, info in planet_data.items() if info["house"] == 12]
    if h12_planets:
        third_parties_found.append(("أطراف سرية خفية / أعداء مخفيون (البيت الثاني عشر)", f"وجود كواكب ({', '.join(h12_planets)}) يشير إلى مؤامرات خفية، أطراف تعمل بالسر، أو تأثيرات سلبية غير مبررة."))

    if third_parties_found:
        st.warning("⚠️ **تم رصد أطراف ثالثة مؤثرة في الخريطة:**")
        for tp_title, tp_desc in third_parties_found:
            st.markdown(f"- **{tp_title}:** {tp_desc}")
    else:
        st.success("✅ الخريطة نظيفة تماماً من تدخلات الأطراف الثالثة؛ النزاع أو الانسحاب محصور كلياً وثنائياً بين الطرفين.")

    # ==========================================
    # تحليل العودة والزمن المتوقع
    # ==========================================
    can_return = False
    return_reasons = []
    timing_res = "غير متاح"

    if event_purpose in ["فراق", "انسحاب"]:
        st.markdown("---")
        st.markdown("### 🔄 تحليل إمكانية عودة التواصل (Reconciliation Analysis)")

        p1_sign = planet_data[party1_ruler]["sign"]
        p2_sign = planet_data[party2_ruler]["sign"]
        if RULERS.get(p1_sign) == party2_ruler and RULERS.get(p2_sign) == party1_ruler:
            can_return = True
            return_reasons.append("يوجد استقبال متبادل تام بين حاكم الطرفين (دلالة فلكية قاطعة على رغبة مشتركة بالعودة والصلح).")

        if has_aspect and asp_type == "positive":
            can_return = True
            return_reasons.append(f"وجود اتصال إيجابي قادم ({asp_name}) بين حاكم الطرفين يدعم فرصة اللقاء.")
        elif moon_aspect_p2 and moon_asp_type == "positive":
            can_return = True
            return_reasons.append(f"القمر يصنع اتصالاً إيجابياً ({moon_asp_name}) مع حاكم الشريك، وهو وسيط ممتاز لإتمام الصلح.")

        if can_return:
            st.success("🌟 **إمكانية العودة والتواصل: واردة وبقوة وفق المعطيات الفلكية!**")
            for rr in return_reasons:
                st.markdown(f"- {rr}")

            def calculate_timing(house_num, sign_name, orb_deg):
                if house_num in [1, 4, 7, 10]:
                    h_type = "زاوية"
                elif house_num in [2, 5, 8, 11]:
                    h_type = "تابعة"
                else:
                    h_type = "هابطة"
                
                mod = SIGN_MODALITY.get(sign_name, "كاردينالي")
                table = {
                    "زاوية": {"كاردينالي": "أيام", "متحرك": "أسابيع", "ثابت": "أشهر"},
                    "تابعة": {"كاردينالي": "أسابيع", "متحرك": "أشهر", "ثابت": "سنين"},
                    "هابطة": {"كاردينالي": "أشهر", "متحرك": "سنين", "ثابت": "وقت غير محدد"}
                }
                unit = table.get(h_type, {}).get(mod, "أيام")
                return f"حوالي {orb_deg:.1f} {unit}"

            timing_res = calculate_timing(planet_data["القمر"]["house"], planet_data["القمر"]["sign"], moon_orb if moon_aspect_p2 else asp_orb)
            st.info(f"⏳ **الوقت المتوقع لعودة التواصل والصلح:** {timing_res}")
        else:
            st.error("🛑 **إمكانية العودة والتواصل: ضعيفة أو متعذرة في الوقت الحالي.**")
            st.markdown("- غياب الاتصالات الإيجابية القادمة أو الاستقبال المتبادل يعكس تمسك كل طرف بموقفه أو الحاجة لفترة طويلة جداً من الانفصال.")

    # ==========================================
    # تصدير تقرير HTML للجنة المختصين
    # ==========================================
    st.markdown("---")
    st.markdown("### 🖨️ تصدير التقرير الفلكي لخريطة الحدث العاطفي")

    causes_html = "".join([f"<li><strong>{c['category']}:</strong> {c['desc']}</li>" for c in detailed_causes])
    tp_html = "".join([f"<li><strong>{title}:</strong> {desc}</li>" for title, desc in third_parties_found]) if third_parties_found else "<li>لا توجد أطراف ثالثة مؤثرة؛ الحدث ثنائي بالكامل.</li>"
    return_html = f"""
    <div class='box'>
        <h3>🔄 إمكانية العودة والتواصل والوقت المتوقع</h3>
        <p><strong>الحالة:</strong> {'واردة وبقوة' if can_return else 'ضعيفة أو متعذرة'}</p>
        <p><strong>الوقت المتوقع للعودة:</strong> {timing_res}</p>
        <ul>{"".join([f"<li>{rr}</li>" for rr in return_reasons])}</ul>
    </div>
    """ if event_purpose in ["فراق", "انسحاب"] else ""

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>التقرير الفلكي المتقدم للحدث العاطفي</title>
        <style>
            body {{ font-family: 'Tahoma', Arial, sans-serif; margin: 40px; color: #222; line-height: 1.8; background: #fff; }}
            h1, h2, h3 {{ color: #3b093c; }}
            .header {{ text-align: center; border-bottom: 3px solid #3b093c; padding-bottom: 20px; margin-bottom: 30px; }}
            .box {{ background: #fdfdfd; border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            .footer {{ text-align: center; margin-top: 50px; font-size: 13px; color: #666; border-top: 1px solid #ddd; padding-top: 15px; }}
            @media print {{
                body {{ margin: 20px; }}
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>💖 التقرير الفلكي الاحترافي للحدث العاطفي</h1>
            <p><strong>برمجة استرو رادار</strong></p>
            <p>تاريخ ووقت الحدث: {ev_date} {ev_time} | الموقع الجغرافي: {selected_country_name}</p>
        </div>

        <div class="box">
            <h3>📌 معطيات الخريطة الفلكية الأساسية</h3>
            <p><strong>نوع الحدث العاطفي:</strong> {selected_event_key}</p>
            <p><strong>الطالع:</strong> {asc_sign} ({asc_deg:.2f}°)</p>
            <p><strong>حاكم الطرف الأول (الطالع):</strong> {party1_ruler} (في برج {planet_data[party1_ruler]['sign']} - البيت {planet_data[party1_ruler]['house']})</p>
            <p><strong>رأس البيت السابع (الشريك):</strong> {desc_sign}</p>
            <p><strong>حاكم الطرف الثاني (الشريك):</strong> {party2_ruler} (في برج {planet_data[party2_ruler]['sign']} - البيت {planet_data[party2_ruler]['house']})</p>
        </div>

        <div class="box">
            <h3>⚙️ التشخيص الفلكي والنفسي لأسباب الحدث</h3>
            <ul>{causes_html}</ul>
        </div>

        <div class="box">
            <h3>👥 تقرير الأطراف الثالثة والمحيط</h3>
            <ul>{tp_html}</ul>
        </div>

        {return_html}

        <div class="footer">
            <p>تم استخراج هذا التقرير الفلكي المتقدم وفق أحدث أصول ومراجع التنجيم الساعي الغربي وريغومونتانوس.</p>
        </div>
    </body>
    </html>
    """

    st.download_button(
        label="📥 تحميل التقرير الكامل (HTML)",
        data=html_content,
        file_name=f"Expert_Emotional_Event_Report_{ev_date}.html",
        mime="text/html",
        use_container_width=True
    )