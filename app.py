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
st.markdown("تحليل تنجيمي عميق يغطي دلالات الانفصال، الانسحاب، المشاجرات، الأسباب الدقيقة، وتحديد أدوار الأطراف الثالثة بدقة مع حساب الإقبال والإنصراف والوقت المتوقع للرجوع.")
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
    lon_deg = lon_deg % 360
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

    # ==========================================
    # التصحيح الدقيق: مصفوفة البيوت في pyswisseph من 0 إلى 11
    # الفهرس 0 = البيت الأول (الطالع) | الفهرس 6 = البيت السابع
    # ==========================================
    houses_cusps, ascmc = swe.houses_ex(jd, lat, lon, b"R")
    
    asc_lon = houses_cusps[0]  
    asc_sign, asc_deg = get_sign_and_deg(asc_lon)

    def find_house(p_lon):
        p_lon = p_lon % 360
        for i in range(12):
            c_start = houses_cusps[i] % 360
            next_idx = (i + 1) % 12
            c_end = houses_cusps[next_idx] % 360
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
    desc_cusp_lon = houses_cusps[6]  # البيت السابع هو الفهرس 6 آمن ودقيق
    desc_sign, _ = get_sign_and_deg(desc_cusp_lon)
    party2_ruler = RULERS[desc_sign]

    st.success("✨ تم حساب الخريطة الفلكية بنجاح عبر محرك Swiss Ephemeris وفق نظام ريغومونتانوس (تم تصحيح فهرسة البيوت 0-11 بنجاح)!")

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

    def check_aspect(p1_name, p2_name):
        lon1 = planet_data[p1_name]["lon"]
        lon2 = planet_data[p2_name]["lon"]
        speed1 = planet_data[p1_name]["speed"]
        speed2 = planet_data[p2_name]["speed"]
        
        diff = abs(lon1 - lon2) % 360
        if diff > 180:
            diff = 360 - diff
        
        aspects_def = [
            ("اقتران (Conjunction)", 0, 5.0, "positive"),
            ("تثليث (Trine)", 120, 5.0, "positive"),
            ("تسديس (Sextile)", 60, 4.0, "positive"),
            ("تربيع (Square)", 90, 5.0, "negative"),
            ("مقابلة (Opposition)", 180, 5.0, "negative")
        ]
        
        for asp_name, target, max_orb, asp_type in aspects_def:
            orb = abs(diff - target)
            if orb <= max_orb:
                is_applying = (lon1 < lon2 and speed1 > speed2) or (lon1 > lon2 and speed1 < speed2)
                status = "Applying" if is_applying else "Separating"
                return True, asp_name, asp_type, orb, status
                
        return False, None, None, 0.0, None

    p1_name = party1_ruler
    p2_name = party2_ruler
    
    has_aspect, asp_name, asp_type, asp_orb, asp_status = check_aspect(p1_name, p2_name)
    _, moon_asp_name, moon_asp_type, moon_orb, moon_status = check_aspect("القمر", p2_name)

    detailed_causes = []

    if event_purpose == "لقاء":
        if not planet_data["عطارد"]["retro"]:
            detailed_causes.append({
                "category": "انسجام الحوار والتواصل الفكري",
                "desc": "حركة عطارد المباشرة وتواجده في موقع مناسب يعكس حواراً سلساً وتفاهماً واضحاً أثناء اللقاء، مما أتاح للطرفين التعبير عن المشاعر بوضوح."
            })
        else:
            detailed_causes.append({
                "category": "لقاء لاستعادة ذكريات أو حوار سابق",
                "desc": "تراجع عطارد أثناء اللقاء يشير إلى أن اللقاء تم لإعادة فتح مواضيع قديمة، أو لاسترجاع ذكريات سابقة بين الطرفين."
            })

        _, v_m_name, v_m_type, _, _ = check_aspect("الزهرة", "المريخ")
        if v_m_type in ["positive", "neutral"]:
            detailed_causes.append({
                "category": "شغف وانجذاب عاطفي وجسدي قوي",
                "desc": f"الاتصال الإيجابي ({v_m_name}) بين الزهرة والمريخ يمنح اللقاء طاقة عالية من الشغف المتبادل والجاذبية العاطفية القوية."
            })
        else:
            detailed_causes.append({
                "category": "بحث عن الأمان والتقارب العاطفي",
                "desc": "تتواجد الزهرة والقمر في مواقع تدعم التقارب النفسي والبحث عن الراحة العاطفية وكسر الحواجز بين الطرفين."
            })

        if has_aspect:
            detailed_causes.append({
                "category": "تلاقي الإرادات وتوافق التوقيت",
                "desc": f"وجود اتصال فلكي ({asp_name} - {asp_status}) بين حاكم الطالع وحاكم البيت السابع يعكس توافق النوايا ورغبة الطرفين الصادقة في تجسيد هذا اللقاء."
            })
        else:
            detailed_causes.append({
                "category": "لقاء مدفوع بالظروف أو بمبادرة أحد الأطراف",
                "desc": "اللقاء جرى بناءً على ترتيبات مواتية أو دافع نفسي قوي لدى أحد الطرفين لتجديد التواصل."
            })

    elif event_purpose == "مشاجرة":
        detailed_causes.append({
            "category": "تصادم في وجهات النظر واحتكاك لفظي حاد",
            "desc": "طبيعة الخريطة تشير إلى توتر في لغة الحوار أو اختلاف في التوقعات اللحظية أدى إلى مشاجرة وسوء فهم مباشر."
        })
        mars_sat_asp, _, _, _, _ = check_aspect("المريخ", "زحل")
        if mars_sat_asp or planet_data["المريخ"]["house"] in [1, 7]:
            detailed_causes.append({
                "category": "عناد وطاقة غضب مكبوتة",
                "desc": "وجود اتصالات ضاغطة تخص المريخ تعكس حدة في ردود الفعل، عناداً متبادلاً، وعدم تنازل أي طرف عن موقفه."
            })

    elif event_purpose == "انسحاب":
        detailed_causes.append({
            "category": "رغبة في الهدوء والابتعاد المؤقت",
            "desc": "الانسحاب جاء نتيجة حاجة ملحة لالتقاط الأنفاس، الهروب من الضغوط، أو تفادي تفاقم النقاشات الحادة."
        })
        moon_nep_asp, _, _, _, _ = check_aspect("القمر", "نبتون (Neptune)")
        if moon_nep_asp or planet_data["القمر"]["house"] in [12, 8]:
            detailed_causes.append({
                "category": "حساسية مفرطة وانكفاء عاطفي",
                "desc": "المشاعر الحالية تميل للصمت، الانعزال الداخلي، والتقوقع خوفاً من التعرض لخيبة أمل جديدة."
            })

    else:
        merc_sat_asp, _, _, _, _ = check_aspect("عطارد", "زحل")
        merc_mars_asp, _, m_asp_type, _, _ = check_aspect("عطارد", "المريخ")
        if planet_data["عطارد"]["retro"] or merc_sat_asp or (merc_mars_asp and m_asp_type == "negative") or planet_data["عطارد"]["house"] in [3, 6, 12]:
            detailed_causes.append({
                "category": "أسلوب تواصل غير مقبول أو حاد",
                "desc": "وجود عطارد في وضعية متراجعة أو تحت ضغط زحل والمريخ يشير إلى جارحة في الكلام، جفاف في الحوار، أو سوء فهم لفظي متكرر."
            })

        plu_ven_asp, _, _, _, _ = check_aspect("الزهرة", "بلوتو (Pluto)")
        h8_planets = [p for p, info in planet_data.items() if info["house"] == 8]
        h12_planets = [p for p, info in planet_data.items() if info["house"] == 12]
        if plu_ven_asp or len(h8_planets) > 0 or len(h12_planets) > 0:
            detailed_causes.append({
                "category": "اكتشاف سر، غموض، أو شبهة خيانة",
                "desc": "تفعيل البيوت الثامنة والثانية عشرة أو اتصالات بلوتو بالزهرة تكشف عن صدمة متعلقة بانكشاف أسرار مخفية وفقدان الثقة."
            })

    st.info(f"📌 **طبيعة الحدث المحدد:** {selected_event_key}")
    st.markdown("#### ⚙️ التشخيص التفصيلي لحدث اللحظة العاطفية:")
    for cause in detailed_causes:
        st.markdown(f"- **{cause['category']}:** {cause['desc']}")

    st.markdown("---")
    st.markdown("### 👥 تحليل الأطراف الثالثة وتحديد هويتهم")

    third_parties_found = []
    for h_num, title_prefix, desc_text in [
        (3, "محيط الأقارب أو الجيران / نقاشات ودية أو نميمة", "البيت الثالث"),
        (4, "أجواء المنزل أو ضغوط العائلة والوالدين", "البيت الرابع"),
        (5, "غيرة أو طرف منافس عاطفي / معجب خارجي", "البيت الخامس"),
        (7, "شخص منافس أو طرف معلن أو وسطاء خير", "البيت السابع"),
        (11, "الأصدقاء المشتركون والشبكة الاجتماعية", "البيت الحادي عشر"),
        (12, "أعداء مخفيون أو وشاية سرية أو خلوة", "البيت الثاني عشر")
    ]:
        h_planets = [p for p, info in planet_data.items() if info["house"] == h_num and p not in [party1_ruler, party2_ruler, "الشمس", "القمر"]]
        if h_planets:
            third_parties_found.append((f"{title_prefix} ({desc_text})", f"وجود كواكب مؤثرة ({', '.join(h_planets)}) يعكس تدخلاً أو تأثيراً مباشراً من هذا القطاع."))

    if third_parties_found:
        st.warning("⚠️ **تم رصد أطراف ثالثة مؤثرة في الخريطة:**")
        for tp_title, tp_desc in third_parties_found:
            st.markdown(f"- **{tp_title}:** {tp_desc}")
    else:
        st.success("✅ الخريطة نظيفة تماماً من تدخلات الأطراف الثالثة؛ الحدث محصور كلياً وثنائياً بين الطرفين.")

    # ==========================================
    # 🔄 التحليل المتطور للعودة والزمن المتوقع
    # ==========================================
    can_return = False
    return_reasons = []
    timing_res = "غير متاح"

    if event_purpose in ["فراق", "انسحاب", "مشاجرة"]:
        st.markdown("---")
        st.markdown("### 🔄 تحليل إمكانية عودة التواصل (Reconciliation Analysis)")

        p1_sign = planet_data[party1_ruler]["sign"]
        p2_sign = planet_data[party2_ruler]["sign"]
        
        if planet_data[party2_ruler]["retro"]:
            can_return = True
            return_reasons.append(f"حاكم الشريك ({party2_ruler}) في حالة تراجع، وهذه دلالة قوية على إعادة التفكير ورغبة الشريك في التراجع عن قرار الابتعاد.")

        if RULERS.get(p1_sign) == party2_ruler or RULERS.get(p2_sign) == party1_ruler:
            can_return = True
            return_reasons.append("وجود استقبال ومودة بين حكّام الخريطة يدعم بقوة رغبة الأطراف في إعادة فتح قنوات التواصل.")

        if has_aspect and asp_type == "positive" and asp_status == "Applying":
            can_return = True
            return_reasons.append(f"وجود اتصال إيجابي قادم ومنطبق ({asp_name}) بين حاكم الطالع وحاكم الشريك يفتح باب الصلح واللقاء قريباً.")

        if moon_asp_type == "positive" and moon_status == "Applying":
            can_return = True
            return_reasons.append(f"القمر يصنع اتصالاً إيجابياً مقبلاً ({moon_asp_name}) مع حاكم الشريك، مما يسارع في الصلح.")

        if can_return:
            st.success("🌟 **إمكانية العودة والتواصل: واردة وبقوة وفق المعطيات الفلكية!**")
            for rr in return_reasons:
                st.markdown(f"- {rr}")

            def calculate_precise_timing(orb_val, sign_name):
                mod = SIGN_MODALITY.get(sign_name, "كاردينالي")
                if mod == "كاردينالي":
                    unit = "أيام"
                elif mod == "متحرك":
                    unit = "أسابيع أو أشهر قليلة"
                else:
                    unit = "أشهر طويلة"
                return f"حوالي {orb_val:.1f} {unit}"

            timing_res = calculate_precise_timing(moon_orb if moon_status == "Applying" else asp_orb, planet_data["القمر"]["sign"])
            st.info(f"⏳ **الوقت المتوقع لعودة التواصل والصلح:** {timing_res}")
        else:
            st.error("🛑 **إمكانية العودة والتواصل: ضعيفة أو متعذرة في الوقت الحالي.**")
            st.markdown("- غياب الاتصالات الإيجابية المقبلة (Applying) أو وجود الاتصالات منصرفة يعكس تمسك كل طرف بموقفه الحالي.")

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
    """ if event_purpose in ["فراق", "انسحاب", "مشاجرة"] else ""

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
            <h3>⚙️ التشخيص الفلكي والنفسي لحدث اللحظة العاطفية</h3>
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
