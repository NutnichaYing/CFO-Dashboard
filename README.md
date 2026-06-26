# CFO FX Intelligence Dashboard

ระบบ Monitor USD/THB และสร้าง Prompt วิเคราะห์ Forward Contract อัตโนมัติ
**ฟรี 100%** — GitHub Pages + GitHub Actions + Claude Pro

## วิธี Setup (15 นาที)

### 1. Fork Repository นี้
- คลิก Fork มุมบนขวาของ GitHub

### 2. เปิด GitHub Pages
- ไปที่ Settings → Pages
- Source: Deploy from branch → main → / (root)
- กด Save
- รอ 2 นาที → ได้ URL: `https://[username].github.io/fx-intelligence`

### 3. เปิด GitHub Actions
- ไปที่ Actions tab
- คลิก "I understand my workflows, go ahead and enable them"
- ระบบจะ update ข้อมูลอัตโนมัติ 3 ครั้ง/วัน (07:00, 11:00, 18:00 BKK)

### 4. ตั้งค่า Budget Rate
- เปิด Dashboard → ใส่ Budget Rate ของบริษัท
- ใส่ USD Exposure/เดือน
- ใส่ % ที่ Hedge แล้ว
- คลิก "คำนวณใหม่"

### 5. วิเคราะห์ด้วย Claude Pro
- คลิกปุ่ม "Copy Prompt"
- เปิด claude.ai
- วาง Prompt → รับการวิเคราะห์ทันที

## ค่าใช้จ่าย

| รายการ | ค่าใช้จ่าย |
|--------|-----------|
| GitHub Pages | ฟรี |
| GitHub Actions | ฟรี (2,000 นาที/เดือน) |
| BOT API | ฟรี |
| Claude Pro | มีอยู่แล้ว |
| **รวม** | **THB 0** |

## แหล่งข้อมูล

- **FX Rate**: ธนาคารแห่งประเทศไทย (BOT) Public API
- **ข่าว**: Reuters Business RSS, Bangkok Post RSS
- **AI Analysis**: Claude Pro (claude.ai)

## ข้อจำกัด

- BOT อัพเดทอัตราวันละครั้ง (วันทำการ)
- ข่าวจาก RSS อาจมี delay 15-30 นาที
- ระบบนี้เพื่อประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำทางการเงิน
