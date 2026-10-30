=== วิธีติดตั้งและใช้งาน Noita ภาษาไทย ===

การติดตั้ง:
1. โฟลเดอร์ "thai" นี้ควรอยู่ใน Steam\steamapps\common\Noita\mods\
2. เปิดเกม Noita → ไปที่ Options → Language → เลือก "ภาษาไทย"
3. กด New Game


=== ฟอนต์ภาษาไทย ===

ฟอนต์อยู่ใน fonts/ (font_pixel, font_pixel_big, font_pixel_huge)
สร้างด้วย tools/build_thai_font.py: ตัวอังกฤษ/ตัวเลขคัดลอกมาจากฟอนต์ของเกม
ตัวไทยมาจากภาพตัวอักษรที่วาดมือใน fonts_src/ (ช่องไหนว่าง ใช้จาก TTF แทน)
สระบน/ล่างและวรรณยุกต์ถูกวาดรวมกับพยัญชนะเป็นตัวเดียว (Private Use Area U+E000+)
เพราะเกมวางสระ/วรรณยุกต์ซ้อนกันเองไม่ได้

สร้างใหม่ทุกครั้งที่แก้คำแปลหรือแก้ภาพตัวอักษร (ต้องมี Python + Pillow, รันในโฟลเดอร์ mods/thai):
  python -I tools/build_thai_font.py --game "C:/Program Files (x86)/Steam/steamapps/common/Noita" --mod .

ดูตัวอย่างก่อนเข้าเกม:
  python -I tools/preview.py . preview.png <key1> <key2> ...


=== การเกลาตัวอักษรด้วยมือ ===

fonts_src/thai_11px.png = ตัวเล็ก (ข้อความทั่วไป)   fonts_src/thai_15px.png = ตัวใหญ่ (หัวข้อ)
- เปิดด้วยโปรแกรมวาด pixel (Aseprite, Piskel, Paint.NET, GIMP) ซูมใหญ่ๆ
- ช่องละ 14 px กว้าง, 16 ช่องต่อแถว ลำดับตัวอักษรดูใน thai_11px.txt / thai_15px.txt
- สีขาว = เส้นตัวอักษร  สีพื้นเข้มอื่นๆ = พื้นหลัง (ใช้สีอะไรก็ได้ที่ไม่สว่าง)
- แถบสีอ่อนในแต่ละช่อง = แถวตัวพยัญชนะ (ตัวเล็ก 5 แถว, ตัวใหญ่ 7 แถว)
  พยัญชนะต้องอยู่ในแถบนี้ ห้ามขยับขึ้นลง ส่วนหางขึ้น/ลง (ป ฝ ฟ ฎ ฏ ญ ฐ) ยื่นออกนอกแถบได้
- เส้นตัวอักษรเริ่มชิดซ้ายของช่อง ความกว้างตัวอักษร = ความกว้างเส้น + ช่องไฟ 1 px อัตโนมัติ
- สระบน/ล่างและวรรณยุกต์: วาดแค่รูปร่าง ตำแหน่งสคริปต์คำนวณให้เอง
- ลบช่องให้ว่าง = กลับไปใช้ตัวจาก TTF  ลบทั้งไฟล์ = ใช้ TTF ทั้งขนาดนั้น
- เริ่มใหม่จาก TTF: ลบไฟล์ใน fonts_src แล้วรันคำสั่ง build พร้อม --export-sheets (ไม่ทับไฟล์ที่มีอยู่)


=== ฟอนต์ต้นฉบับ / License ===

ตัวอักษรไทยดัดแปลงจาก IBM Plex Sans Thai Looped (Copyright © 2017 IBM Corp.)
ใช้ภายใต้ SIL Open Font License 1.1 ดู fonts_src/OFL.txt
ห้ามตั้งชื่อฟอนต์ที่ดัดแปลงว่า "Plex" (Reserved Font Name) และต้องแนบ OFL.txt ไปด้วยเสมอ

=== ไฟล์ใน mod ===
- mod.xml             = ข้อมูล mod
- translation.xml     = ตั้งค่าภาษา (ฟอนต์, ชื่อภาษา)
- translation_src.csv = ไฟล์แปลที่แก้ได้
- translation.csv     = ไฟล์ที่เกมอ่าน (สร้างจากสคริปต์)
- fonts/              = ฟอนต์พิกเซลไทย (สร้างจากสคริปต์)
- fonts_src/          = ภาพตัวอักษรวาดมือ + TTF ต้นฉบับ + OFL.txt
- tools/              = สคริปต์ build / preview / test
- README_THAI.txt     = ไฟล์นี้

=== การแก้ไขคำแปล ===
แก้ที่ translation_src.csv เท่านั้น (เปิดด้วย Notepad++ หรือ Excel, เซฟเป็น UTF-8)
translation.csv ถูกสร้างใหม่โดยสคริปต์ทุกครั้ง อย่าแก้ไฟล์นี้ตรงๆ
รูปแบบ: key,ข้อความที่แปล
ขึ้นบรรทัดใหม่ใช้ \n (สคริปต์แปลงการขึ้นบรรทัดจริงให้อัตโนมัติ)

=== ติดต่อ ===
Discord: Noita Official Server → #modding-general
