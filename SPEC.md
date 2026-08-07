# SPEC.md — TripSmith (AI Travel Itinerary Planner)

> เขียนสเปกก่อนลงมือ (Spec-Driven Development) ต่อยอดจาก Lab **GSP1150 · Introduction to Gemini 3**
> ใช้ Gemini API ผ่าน Google Gen AI SDK (`google-genai`)

## 1. แอปทำอะไร (Overview)

**TripSmith** เป็นผู้ช่วยวางแผนทริปท่องเที่ยว ผู้ใช้กรอกปลายทาง + จำนวนวัน + เดือนที่ไป + ความสนใจ
แล้วแอปจะ:

1. **ค้นข้อมูลสด** ด้วย Google Search Grounding (เทศกาล/อีเวนต์/ทิปตามฤดูกาลของช่วงเวลานั้น)
2. **สร้างแผนเที่ยวรายวัน** เป็น **JSON ที่มี schema ชัดเจน** เอาไปเรนเดอร์เป็น UI / เก็บลง DB ต่อได้ทันที
3. เปิดโหมด **แชทหลายเทิร์น (multi-turn) + streaming** ให้ผู้ใช้ปรับแผนแบบโต้ตอบ real-time
4. โหมดเสริม: เปรียบเทียบ **thinking_level** (low vs high) บนคำถามวางแผนที่ซับซ้อน

## 2. Input / Output

### Input
| ฟิลด์ | ชนิด | ตัวอย่าง |
|-------|------|----------|
| destination | str | "Kyoto, Japan" |
| num_days | int | 3 |
| trip_month | str | "November" |
| interests | list[str] | ["food", "temples", "photography"] |
| budget_level | str | "mid" (low/mid/high) |

### Output (Structured JSON — ดู schema ในหัวข้อ 4)
- สรุปทริป + แผนรายวัน (ธีม, กิจกรรมเช้า/บ่าย/เย็น, ค่าใช้จ่ายโดยประมาณ)
- ทิปการแพ็คของ + ประมาณค่าใช้จ่ายรวม
- แหล่งอ้างอิง (citations) จาก Grounding

## 3. Prompt + System Instruction Design

### System Instruction (กำหนดบทบาท/พฤติกรรม)
```
You are TripSmith, a seasoned local travel guide with 15 years of experience.
- Give practical, realistic itineraries — account for travel time between spots.
- Respect the traveler's budget level and interests; never suggest closed/seasonal spots.
- Prefer authentic local experiences over tourist traps.
- Be concise. When asked for JSON, output ONLY valid JSON matching the schema.
```

### Prompt (insights — grounded)
```
Search for current, {trip_month}-specific travel information about {destination}:
seasonal festivals/events, weather to expect, and 3 timely local tips.
Return a tight bullet summary with concrete names and dates.
```

### Prompt (itinerary — structured)
```
Plan a {num_days}-day trip to {destination} in {trip_month}.
Traveler interests: {interests}. Budget: {budget_level}.
Use these fresh insights when relevant:
<<< {grounded_insights} >>>
Produce a day-by-day itinerary as JSON per the provided schema.
```

## 4. JSON Schema (Structured Output)

```
Itinerary
├─ destination: str
├─ trip_month: str
├─ num_days: int
├─ summary: str
├─ days: list[DayPlan]
│   ├─ day: int
│   ├─ theme: str
│   └─ activities: list[Activity]
│       ├─ time_of_day: "morning" | "afternoon" | "evening"
│       ├─ title: str
│       ├─ description: str
│       ├─ approx_cost_usd: float
│       └─ duration_hours: float
├─ packing_tips: list[str]
└─ estimated_total_cost_usd: float
```

## 5. ฟีเจอร์จาก Lab ที่ใช้ (≥ 3)

1. ✅ **System Instructions** — กำหนดบทบาทไกด์ท่องเที่ยว
2. ✅ **Structured Output (JSON + schema)** — ผลลัพธ์แผนเที่ยวแบบ machine-readable
3. ✅ **Grounding (Google Search)** — ดึงข้อมูลเทศกาล/สภาพอากาศล่าสุด
4. ✅ (เสริม) **Multi-turn chat + Streaming** — ปรับแผนแบบโต้ตอบ real-time
5. ✅ (เสริม) **thinking_level** — เทียบผล low vs high (Gemini 3)

## 6. Temperature Strategy

| งาน | temperature | เหตุผล |
|-----|-------------|--------|
| Insights (grounded) | 0.2 | ต้องแม่นยำ อิงข้อเท็จจริง ลด hallucination |
| Itinerary generation | 0.7 | ต้องการความหลากหลาย/สร้างสรรค์ แต่ยังสมเหตุสมผล |
| Chat refinement | 0.6 | สมดุลระหว่างความคิดสร้างสรรค์กับความสอดคล้อง |

## 7. ขอบเขต / Non-goals
- ไม่จองตั๋ว/โรงแรมจริง (แค่วางแผน)
- ไม่รับประกันราคาตายตัว (เป็นค่าประมาณ)
