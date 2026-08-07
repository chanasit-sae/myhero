# TripSmith — AI Travel Trip Planner

ผู้ช่วยวางแผนทริปท่องเที่ยวด้วย **Gemini API** ผ่าน **Google Gen AI SDK (`google-genai`)**
ต่อยอดจาก Lab **GSP1150 · Introduction to Gemini 3** (โมเดล **Gemini 3.1 Pro / Gemini 3.5 Flash**)

บอกปลายทาง + จำนวนวัน + เดือนที่ไป + ความสนใจ → แอปจะเช็คอากาศด้วย function calling,
สร้างแผนเที่ยวรายวันเป็น **JSON ที่พร้อมใช้งานต่อ**, ดูรูปสถานที่ได้ และแชทปรับแผนแบบ real-time

> 📄 ออกแบบก่อนเขียนโค้ดใน [SPEC.md](./SPEC.md) (Spec-Driven)

## ฟีเจอร์จาก Lab GSP1150 ที่ใช้

| # | ฟีเจอร์ | อยู่ใน Lab? | ใช้ที่ไหน |
|---|---------|:---:|-----------|
| 1 | **System Instructions** | ✅ | บทบาท "ไกด์ท่องเที่ยวที่มีประสบการณ์" (`SYSTEM_INSTRUCTION`) |
| 2 | **Function calling** | ✅ | `fetch_weather()` ให้โมเดลเรียก `get_weather` เอง (แบบเดียวกับ Lab) |
| 3 | **Multimodality** | ✅ | `analyze_photo()` ส่งรูป/URL ให้โมเดลวิเคราะห์ (แบบ meal.png ใน Lab) |
| 4 | **Multi-turn chat + Streaming** | ✅ | `chat_session()` จำบริบท + สตรีมคำตอบทีละ chunk |
| 5 | **thinking_level (low/high)** | ✅ | `compare_thinking()` คุมระดับการคิดของ Gemini 3 |
| 6 | **Structured Output (JSON+schema)** | (โจทย์บังคับ) | `generate_trip_plan()` ใช้ `response_schema=TripPlan` (pydantic) |

ใช้ฟีเจอร์จาก Lab จริง **5 อย่าง** (โจทย์กำหนด ≥ 3) + Structured Output ตามที่โจทย์บังคับ

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
    --interests "food, temples, photography" --budget mid --out trip_plan.json
```

### คำสั่งทั้งหมด

```bash
python app.py plan "Chiang Mai, Thailand" --days 2 --month December   # เช็คอากาศ (function calling) + แผน JSON
python app.py weather "Kyoto, Japan"                                  # function calling อย่างเดียว
python app.py photo temple.jpg "What place is this?"                  # multimodality (รูป/URL)
python app.py chat                                                    # แชทหลายเทิร์น + streaming
python app.py thinking "Plan a rainy 5-day Tokyo trip on a tight budget"  # เทียบ thinking_level
```

## ตัวอย่าง Input / Output

**Input**
```bash
python app.py plan "Kyoto, Japan" --days 2 --month November --interests "temples, food" --budget mid
```

**Output (ตัดมาบางส่วน)**
```
Checking weather for Kyoto, Japan (function calling)...
The current weather in Kyoto, Japan is around 18°C with clear skies.

Making your trip plan...
{
  "destination": "Kyoto, Japan",
  "trip_month": "November",
  "num_days": 2,
  "summary": "A 2-day autumn Kyoto trip mixing famous temples and local food...",
  "days": [
    {
      "day": 1,
      "theme": "East Kyoto temples & autumn leaves",
      "activities": [
        {
          "time_of_day": "morning",
          "title": "Kiyomizu-dera at opening",
          "description": "Arrive by 8am to beat the crowds and catch autumn colors.",
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
| **Weather (function calling)** | `0.2` | เป็นงานอิงข้อเท็จจริง ต้องแม่นยำ ลดการแต่งเรื่องเอง จึงตั้งต่ำ |
| **Trip plan** | `0.7` | ต้องการความหลากหลายและไอเดียใหม่ในการจัดกิจกรรม แต่ยังต้องสมเหตุสมผล จึงใช้ค่ากลางค่อนสูง |
| **Photo (multimodal)** | `0.4` | บรรยายตามภาพจริง ไม่แต่งเกินจริง |
| **Chat** | `0.6` | สมดุลระหว่างการเสนอไอเดียใหม่กับการยึดตามแผนเดิม |

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

Lab GSP1150 ใช้ **Gemini 3.1 Pro** และ **Gemini 3.5 Flash**
แอปนี้ default เป็น `gemini-3.5-flash` — เปลี่ยนได้ผ่าน `GEMINI_MODEL` ใน `.env`
(เช่น `gemini-3.1-pro`) ฟีเจอร์ `thinking_level` ต้องใช้โมเดล Gemini 3
ถ้าไม่มีสิทธิ์เข้าถึง Gemini 3 ตั้ง `GEMINI_MODEL=gemini-2.5-flash` ได้ (คำสั่ง `thinking` จะข้ามให้)

## ส่วนที่ใช้ AI

- ใช้ **Claude Code** ช่วยยกร่างโครงสร้างโปรเจกต์, SPEC, และโค้ด `app.py` ตาม use case ที่ออกแบบเอง
- ให้ Claude อ่านไฟล์ Lab (PDF) เพื่อตรวจว่าฟีเจอร์ที่ใช้ตรงกับ GSP1150 จริง —
  รอบแรกเผลอใช้ Grounding (ซึ่งอยู่ Lab อื่น) จึงแก้มาใช้ Function calling + Multimodality ที่อยู่ใน Lab นี้
- schema ของ `TripPlan` และค่า temperature ต่อแต่ละงาน เป็นการตัดสินใจออกแบบของผู้ทำ
