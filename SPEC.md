# SPEC.md — TripSmith (AI Travel Trip Planner)

> เขียนสเปกก่อนลงมือ (Spec-Driven Development) ต่อยอดจาก Lab **GSP1150 · Introduction to Gemini 3**
> ใช้ Gemini API ผ่าน Google Gen AI SDK (`google-genai`) · โมเดล **Gemini 3.1 Pro / Gemini 3.5 Flash**

## 1. แอปทำอะไร (Overview)

**TripSmith** เป็นผู้ช่วยวางแผนทริปท่องเที่ยว ผู้ใช้กรอกปลายทาง + จำนวนวัน + เดือนที่ไป + ความสนใจ
แล้วแอปจะ:

1. **เช็คสภาพอากาศ** ด้วย **Function calling** (โมเดลเรียกฟังก์ชัน `get_weather` เอง — แบบเดียวกับใน Lab)
2. **สร้างแผนเที่ยวรายวัน** เป็น **JSON ที่มี schema ชัดเจน** เอาไปทำเป็นหน้าเว็บ / เก็บลง DB ต่อได้ทันที
3. **ดูรูปสถานที่** ด้วย **Multimodality** (ส่งรูป/URL ให้โมเดลช่วยดูว่าน่าไปไหม)
4. เปิดโหมด **แชทหลายเทิร์น (multi-turn) + streaming** ให้ผู้ใช้ปรับแผนแบบโต้ตอบ real-time
5. เทียบ **thinking_level** (low vs high) บนคำถามวางแผนที่ยาก

## 2. Input / Output

### Input
| ฟิลด์ | ชนิด | ตัวอย่าง |
|-------|------|----------|
| destination | str | "Kyoto, Japan" |
| num_days | int | 3 |
| trip_month | str | "November" |
| interests | list[str] | ["food", "temples", "photography"] |
| budget_level | str | "mid" (low/mid/high) |
| image (โหมด photo) | path/URL | "temple.jpg" |

### Output (Structured JSON — ดู schema ในหัวข้อ 4)
- สรุปทริป + แผนรายวัน (ธีม, กิจกรรมเช้า/บ่าย/เย็น, ค่าใช้จ่ายโดยประมาณ)
- ทิปการแพ็คของ + ค่าใช้จ่ายรวมโดยประมาณ

## 3. Prompt + System Instruction Design

### System Instruction (กำหนดบทบาท/พฤติกรรม)
```
You are TripSmith, an experienced local travel guide.
- Give practical, realistic trip plans — leave enough time to travel between places.
- Match the traveler's budget and interests; don't suggest places that are closed or out of season.
- Pick real local spots, not tourist traps.
- Keep it short and clear. When asked for JSON, output ONLY valid JSON that matches the schema.
```

### Function calling tool (แบบเดียวกับ get_weather ใน Lab)
```python
def get_weather(location: str) -> dict:
    """Get the current weather in a specific location.
    Args:
        location: The city and country, e.g. Kyoto, Japan.
    """
    return {"location": location, "temperature": "18", "unit": "celsius", "sky": "clear"}
# config=types.GenerateContentConfig(tools=[get_weather])  → โมเดลเรียกฟังก์ชันเอง
```

### Prompt (trip plan — structured)
```
Make a {num_days}-day trip plan for {destination} in {trip_month}.
Traveler interests: {interests}. Budget: {budget_level}.
Current weather note: {weather}
Return a day-by-day trip plan as JSON that matches the schema.
```

## 4. JSON Schema (Structured Output)

```
TripPlan
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

## 5. ฟีเจอร์จาก Lab GSP1150 ที่ใช้ (≥ 3)

1. ✅ **System Instructions** — กำหนดบทบาทไกด์ท่องเที่ยว *(Lab)*
2. ✅ **Function calling** — โมเดลเรียก `get_weather` เอง (แบบเดียวกับ Lab) *(Lab)*
3. ✅ **Multimodality** — ส่งรูป/URL ให้โมเดลวิเคราะห์ (แบบ meal.png ใน Lab) *(Lab)*
4. ✅ **Multi-turn chat + Streaming** — `chat.send_message_stream` *(Lab)*
5. ✅ **thinking_level** — เทียบผล low vs high (Gemini 3) *(Lab)*
6. ✅ **Structured Output (JSON + schema)** — ตามที่โจทย์กำหนด

> หมายเหตุ: เวอร์ชันแรกเคยใช้ Grounding (Google Search) แต่ฟีเจอร์นั้นอยู่ใน Lab อื่น
> (Modernize Website / Vertex AI Search) ไม่ใช่ GSP1150 จึงเปลี่ยนมาใช้ Function calling ที่อยู่ใน Lab นี้จริง

## 6. Temperature Strategy

| งาน | temperature | เหตุผล |
|-----|-------------|--------|
| Weather (function calling) | 0.2 | ต้องแม่นยำ อิงข้อเท็จจริง |
| Trip plan | 0.7 | ต้องการความหลากหลาย/ไอเดียใหม่ แต่ยังสมเหตุสมผล |
| Photo (multimodal) | 0.4 | บรรยายตามภาพจริง ไม่แต่งเกินจริง |
| Chat | 0.6 | สมดุลระหว่างไอเดียใหม่กับความสอดคล้องกับแผนเดิม |

## 7. ขอบเขต / สิ่งที่แอปนี้ไม่ทำ
- ไม่จองตั๋ว/โรงแรมจริง (แค่วางแผน)
- ราคาเป็นค่าประมาณ ไม่ใช่ราคาจริงตายตัว
- `get_weather` เป็น placeholder (ต่อ API อากาศจริงได้ภายหลัง)
