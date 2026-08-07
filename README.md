# TripSmith — AI Travel Itinerary Planner

ผู้ช่วยวางแผนทริปท่องเที่ยวด้วย **Gemini API** ผ่าน **Google Gen AI SDK (`google-genai`)**
ต่อยอดจาก Lab **GSP1150 · Introduction to Gemini 3**

บอกปลายทาง + จำนวนวัน + เดือนที่ไป + ความสนใจ → แอปจะดึงข้อมูลสดด้วย Google Search,
สร้างแผนเที่ยวรายวันเป็น **JSON ที่พร้อมใช้งานต่อ**, และเปิดโหมดแชทปรับแผนแบบ real-time

> 📄 ออกแบบก่อนเขียนโค้ดใน [SPEC.md](./SPEC.md) (Spec-Driven)

## ฟีเจอร์จาก Lab ที่ใช้

| # | ฟีเจอร์ | ใช้ที่ไหน |
|---|---------|-----------|
| 1 | **System Instructions** | กำหนดบทบาท "ไกด์ท่องเที่ยวมือโปร 15 ปี" (`SYSTEM_INSTRUCTION`) |
| 2 | **Structured Output (JSON + schema)** | `generate_itinerary()` ใช้ `response_schema=Itinerary` (pydantic) |
| 3 | **Grounding (Google Search)** | `fetch_insights()` ดึงเทศกาล/สภาพอากาศ/ทิปล่าสุด + citations |
| 4 | **Multi-turn chat + Streaming** *(เสริม)* | `chat_session()` จำบริบท + สตรีมคำตอบทีละ chunk |
| 5 | **thinking_level (low vs high)** *(เสริม)* | `compare_thinking()` เทียบผลบน Gemini 3 |

ครบ **5 ฟีเจอร์** (โจทย์กำหนด ≥ 3)

## วิธีรัน

```bash
# 1. ติดตั้ง dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. ตั้งค่า API key
cp .env.example .env
#   แล้วแก้ .env ใส่ GEMINI_API_KEY (ขอได้ที่ https://aistudio.google.com/apikey)

# 3. รัน
python app.py plan "Kyoto, Japan" --days 3 --month November \
    --interests "food, temples, photography" --budget mid --out itinerary.json
```

### คำสั่งทั้งหมด

```bash
python app.py plan "Chiang Mai, Thailand" --days 2 --month December   # pipeline เต็ม
python app.py insights "Kyoto, Japan" --month November                # เฉพาะข้อมูลสด (grounding)
python app.py chat                                                     # แชทหลายเทิร์น + streaming
python app.py thinking "Plan a rainy 5-day Tokyo trip on a tight budget"  # เทียบ thinking_level
```

## ตัวอย่าง Input / Output

**Input**
```bash
python app.py plan "Kyoto, Japan" --days 2 --month November --interests "temples, food" --budget mid
```

**Output (ตัดมาบางส่วน)**
```
Fetching current insights for Kyoto, Japan (November)...
- Autumn foliage (kōyō) peaks mid-to-late November — Tofuku-ji & Arashiyama are prime.
- Weather: cool 8–17°C, bring layers; some evening illuminations run late Nov.
...
Sources:
  - Japan Guide — https://www.japan-guide.com/...

Generating itinerary...
{
  "destination": "Kyoto, Japan",
  "trip_month": "November",
  "num_days": 2,
  "summary": "A 2-day autumn-focused Kyoto trip balancing iconic temples and local food...",
  "days": [
    {
      "day": 1,
      "theme": "Eastern Kyoto temples & foliage",
      "activities": [
        {
          "time_of_day": "morning",
          "title": "Kiyomizu-dera at opening",
          "description": "Arrive by 8am to beat crowds and catch autumn colors.",
          "approx_cost_usd": 3.0,
          "duration_hours": 2.0
        }
      ]
    }
  ],
  "packing_tips": ["Warm layers", "Comfortable walking shoes"],
  "estimated_total_cost_usd": 180.0
}
```

## เหตุผลการตั้งค่า temperature

| งาน | temperature | เหตุผล |
|-----|-------------|--------|
| **Insights (grounded)** | `0.2` | เป็นงานอิงข้อเท็จจริง (เทศกาล/อากาศ/วันที่) ต้องการความแม่นยำและลด hallucination จึงตั้งต่ำ |
| **Itinerary generation** | `0.7` | ต้องการความหลากหลายและสร้างสรรค์ในการจัดกิจกรรม แต่ยังต้องสมเหตุสมผล จึงใช้ค่ากลางค่อนสูง |
| **Chat refinement** | `0.6` | สมดุลระหว่างความยืดหยุ่นในการเสนอไอเดียใหม่กับความสอดคล้องกับแผนเดิม |

## โครงสร้างไฟล์

```
├─ SPEC.md            # สเปกที่เขียนก่อนลงมือ (Spec-Driven)
├─ README.md          # ไฟล์นี้
├─ app.py             # แอปหลัก (CLI)
├─ requirements.txt   # dependencies
├─ .env.example       # ตัวอย่าง config (ค่าว่าง)
└─ .gitignore
```

## หมายเหตุเรื่อง Gemini 3

ค่า default คือ `gemini-2.5-flash` (เสถียร รองรับ grounding + structured output ครบ)
ฟีเจอร์ `thinking_level` เป็นของ **Gemini 3** — ตั้ง `GEMINI_MODEL=gemini-3-pro-preview` ใน `.env`
เพื่อใช้คำสั่ง `thinking` (โค้ดมี fallback ถ้าโมเดลไม่รองรับ)

## ส่วนที่ใช้ AI

- ใช้ **Claude Code** ช่วยยกร่างโครงสร้างโปรเจกต์, SPEC, และโค้ด `app.py` ตาม use case ที่ออกแบบเอง
- Logic การเลือกฟีเจอร์ (grounding → structured pipeline), schema ของ `Itinerary`,
  และค่า temperature ต่อแต่ละงาน เป็นการตัดสินใจออกแบบของผู้ทำ แล้วให้ AI ช่วยลงรายละเอียด
- โค้ดถูกตรวจทานและปรับให้รันได้จริงกับ Google Gen AI SDK ล่าสุด
