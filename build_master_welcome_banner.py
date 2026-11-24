import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageOps

print("Generating Master Symmetrical 2x3 Welcome Banner (Version 2)...")

W, H = 1280, 720
canvas = Image.new("RGB", (W, H), color="#080c16")

# 1. Luxury Dark Gradient Background with subtle ambient glow
bg = Image.new("RGB", (W, H), color="#080c16")
d_bg = ImageDraw.Draw(bg)
d_bg.ellipse([(50, -100), (600, 300)], fill="#0f2b48")
d_bg.ellipse([(700, 400), (1280, 800)], fill="#3b0764")
d_bg.ellipse([(400, 200), (900, 600)], fill="#064e3b")
bg = bg.filter(ImageFilter.GaussianBlur(130))
canvas = Image.blend(canvas, bg, alpha=0.95)
draw = ImageDraw.Draw(canvas)

# Fonts (Windows standard Segoe UI - crisp & modern)
f_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 26)
f_sub = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 14)
f_header_badge = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 14)
f_card_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 15)
f_card_desc = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 12)
f_pill = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 10)
f_tiny = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 9)

# 2. Header
draw.text((45, 24), "XOTIRA AI", fill="#00f2fe", font=f_title)
draw.text((195, 26), "|   UNIVERSAL FOTO STUDIO", fill="#ffffff", font=f_title)
draw.text((45, 62), "O'zbekistondagi eng zamonaviy neyrotarmoq foto laboratoriyasi", fill="#94a3b8", font=f_sub)

# Header Right Badge
draw.rounded_rectangle([(1035, 26), (1235, 66)], radius=10, fill="#0f172a", outline="#00f2fe", width=2)
draw.text((1062, 36), "6 TA AI XIZMAT", fill="#00f2fe", font=f_header_badge)

# Divider line below header
draw.line([(45, 90), (1235, 90)], fill="#1e293b", width=2)

# Card Grid Dimensions (2 rows x 3 columns - 100% Equal Size)
CARD_W = 380
CARD_H = 290
IMG_W = 360
IMG_H = 185

COLS_X = [45, 448, 855]
ROWS_Y = [105, 412]

# Helpers
def draw_divider_laser(img_draw, x, h, color_hex):
    img_draw.line([(x, 0), (x, h)], fill=color_hex, width=3)
    cy = h // 2
    img_draw.ellipse([(x-5, cy-5), (x+5, cy+5)], fill=color_hex)
    img_draw.ellipse([(x-2, cy-2), (x+2, cy+2)], fill="#ffffff")

def draw_pill(img_draw, box, text, fill_bg, outline_col, text_col, font=f_tiny):
    img_draw.rounded_rectangle(box, radius=4, fill=fill_bg, outline=outline_col, width=1)
    img_draw.text((box[0]+6, box[1]+2), text, fill=text_col, font=font)


# --- 1. CARD: HD TINIQLASHTIRISH ---
face_src = Image.open("temp_photos/woman_face.jpg").convert("RGB")
w_f, h_f = face_src.size
crop_sz = min(w_f, h_f)
face_sq = face_src.crop(((w_f-crop_sz)//2, int(h_f*0.06), (w_f+crop_sz)//2, int(h_f*0.06)+crop_sz)).resize((IMG_W, IMG_H), Image.Resampling.LANCZOS)

left1 = face_sq.crop((0, 0, IMG_W//2, IMG_H))
left1 = left1.filter(ImageFilter.GaussianBlur(3.2))
left1 = ImageEnhance.Color(left1).enhance(0.7)
left1 = ImageEnhance.Contrast(left1).enhance(0.9)

right1 = face_sq.crop((IMG_W//2, 0, IMG_W, IMG_H))
right1 = right1.filter(ImageFilter.UnsharpMask(radius=2, percent=190, threshold=1))
right1 = ImageEnhance.Color(right1).enhance(1.15)
right1 = ImageEnhance.Brightness(right1).enhance(1.04)

card1_img = Image.new("RGB", (IMG_W, IMG_H))
card1_img.paste(left1, (0, 0))
card1_img.paste(right1, (IMG_W//2, 0))
d1 = ImageDraw.Draw(card1_img)
draw_divider_laser(d1, IMG_W//2, IMG_H, "#00f2fe")
draw_pill(d1, (10, 10, 65, 26), "XIRA", "#000000cc", "#64748b", "#cbd5e1")
draw_pill(d1, (IMG_W-75, 10, IMG_W-10, 26), "HD 4K", "#000000cc", "#00f2fe", "#00f2fe")


# --- 2. CARD: RANGLI QILISH (Family photo) ---
family_path = r"C:\Users\Yutech\.gemini\antigravity\brain\9192671a-8f48-460f-86bf-ff60efb11a71\jonli_xotira_welcome_banner_1795512533289.jpg"
fam_src = Image.open(family_path).convert("RGB")
w_fam, h_fam = fam_src.size
fam_rect = fam_src.crop((0, int(h_fam*0.05), w_fam, int(h_fam*0.95))).resize((IMG_W, IMG_H), Image.Resampling.LANCZOS)

left2 = ImageOps.grayscale(fam_rect.crop((0, 0, IMG_W//2, IMG_H))).convert("RGB")
left2 = ImageEnhance.Contrast(left2).enhance(1.1)
right2 = fam_rect.crop((IMG_W//2, 0, IMG_W, IMG_H))
right2 = ImageEnhance.Color(right2).enhance(1.35)

card2_img = Image.new("RGB", (IMG_W, IMG_H))
card2_img.paste(left2, (0, 0))
card2_img.paste(right2, (IMG_W//2, 0))
d2 = ImageDraw.Draw(card2_img)
draw_divider_laser(d2, IMG_W//2, IMG_H, "#ff3366")
draw_pill(d2, (10, 10, 80, 26), "OQ-QORA", "#000000cc", "#94a3b8", "#cbd5e1")
draw_pill(d2, (IMG_W-75, 10, IMG_W-10, 26), "RANGLI", "#000000cc", "#ff3366", "#ff3366")


# --- 3. CARD: FONNI O'CHIRISH (Flawless Neural Cutout on Checkerboard) ---
# Use the pristine neural cutout with 100% preserved clothes & hair
cutout_raw = Image.open("temp_photos/model_cutout_u2netp.png").convert("RGBA")
mod_rgb = Image.open("temp_photos/model_cutout.jpg").convert("RGB")

w_m, h_m = mod_rgb.size
# Crop to 360 x 185
mod_orig = mod_rgb.crop(((w_m-int(w_m*0.8))//2, int(h_m*0.02), (w_m+int(w_m*0.8))//2, int(h_m*0.86))).resize((IMG_W, IMG_H), Image.Resampling.LANCZOS)
cutout_crop = cutout_raw.crop(((w_m-int(w_m*0.8))//2, int(h_m*0.02), (w_m+int(w_m*0.8))//2, int(h_m*0.86))).resize((IMG_W, IMG_H), Image.Resampling.LANCZOS)

card3_img = Image.new("RGB", (IMG_W, IMG_H), color="#ffffff")
d3 = ImageDraw.Draw(card3_img)

# Left half: original background intact
card3_img.paste(mod_orig.crop((0, 0, IMG_W//2, IMG_H)), (0, 0))

# Right half: transparency checkerboard pattern
cell_sz = 12
for y in range(0, IMG_H, cell_sz):
    for x in range(IMG_W//2, IMG_W, cell_sz):
        if ((x // cell_sz) + (y // cell_sz)) % 2 == 0:
            d3.rectangle([(x, y), (x+cell_sz, y+cell_sz)], fill="#cbd5e1")
        else:
            d3.rectangle([(x, y), (x+cell_sz, y+cell_sz)], fill="#f8fafc")

# Right half cutout: extract alpha channel
right_cutout = cutout_crop.crop((IMG_W//2, 0, IMG_W, IMG_H))
alpha_mask = right_cutout.split()[3]

# Crisp glowing emerald sticker outline
sticker_mask = alpha_mask.filter(ImageFilter.MaxFilter(5))
sticker_img = Image.new("RGB", right_cutout.size, "#10b981")
card3_img.paste(sticker_img, (IMG_W//2, 0), sticker_mask)
# Paste model on top with full clothes and hair
card3_img.paste(right_cutout.convert("RGB"), (IMG_W//2, 0), alpha_mask)

d3_final = ImageDraw.Draw(card3_img)
draw_divider_laser(d3_final, IMG_W//2, IMG_H, "#10b981")
draw_pill(d3_final, (10, 10, 85, 26), "FON BILAN", "#000000cc", "#64748b", "#cbd5e1")
draw_pill(d3_final, (IMG_W-90, 10, IMG_W-10, 26), "PNG STIKER", "#000000cc", "#10b981", "#10b981")


# --- 4. CARD: 3x4 PASPORT FORMAT (Official Studio Sheet with Suit) ---
card4_img = Image.new("RGB", (IMG_W, IMG_H), color="#f1f5f9")
d4 = ImageDraw.Draw(card4_img)

# Passport photo with formal suit & tie
pass_src = Image.open("temp_photos/passport_suit_aligned2.jpg").convert("RGB")
pass_crop = pass_src.resize((76, 100), Image.Resampling.LANCZOS)
pass_crop = ImageOps.expand(pass_crop, border=2, fill="#94a3b8")

# White print card
sheet_w, sheet_h = 320, 155
sx = (IMG_W - sheet_w) // 2
sy = 15
d4.rounded_rectangle([(sx, sy), (sx+sheet_w, sy+sheet_h)], radius=6, fill="#ffffff", outline="#cbd5e1", width=1)

# 3 photos side by side
photo_xs = [sx + 18, sx + 118, sx + 218]
for px in photo_xs:
    py = sy + 14
    card4_img.paste(pass_crop, (px, py))
    # Corner marks
    d4.line([(px-3, py-3), (px+5, py-3)], fill="#f59e0b", width=2)
    d4.line([(px-3, py-3), (px-3, py+5)], fill="#f59e0b", width=2)
    d4.line([(px+79, py-3), (px+71, py-3)], fill="#f59e0b", width=2)
    d4.line([(px+79, py-3), (px+79, py+5)], fill="#f59e0b", width=2)
    d4.text((px+7, py+104), "35 x 45 mm", fill="#64748b", font=f_tiny)

# Seal ribbon
d4.rounded_rectangle([(sx + 15, sy + 128), (sx + sheet_w - 15, sy + 148)], radius=4, fill="#f8fafc", outline="#e2e8f0")
d4.text((sx + 32, sy + 132), "BIOMETRIK PASPORT + KOSTYUMLI FORMAT", fill="#0f172a", font=f_tiny)

d4_final = ImageDraw.Draw(card4_img)
draw_pill(d4_final, (10, 10, 105, 26), "6 TALIK VARAQ", "#0f172acc", "#f59e0b", "#f59e0b")


# --- 5. CARD: ANIME & ART STILI ---
anime_src = Image.open("temp_photos/anime_art.jpg").convert("RGB")
aw, ah = anime_src.size
asz = min(aw, ah)
anime_crop = anime_src.crop(((aw-asz)//2, int(ah*0.08), (aw+asz)//2, int(ah*0.08)+asz)).resize((IMG_W//2, IMG_H), Image.Resampling.LANCZOS)
anime_crop = ImageEnhance.Color(anime_crop).enhance(1.4)

card5_img = Image.new("RGB", (IMG_W, IMG_H))
card5_img.paste(face_sq.crop((0, 0, IMG_W//2, IMG_H)), (0, 0))
card5_img.paste(anime_crop, (IMG_W//2, 0))

d5 = ImageDraw.Draw(card5_img)
draw_divider_laser(d5, IMG_W//2, IMG_H, "#ec4899")
draw_pill(d5, (10, 10, 80, 26), "ASL SURAT", "#000000cc", "#64748b", "#cbd5e1")
draw_pill(d5, (IMG_W-90, 10, IMG_W-10, 26), "ANIME ART", "#000000cc", "#ec4899", "#ec4899")


# --- 6. CARD: JONLI HARAKAT (GIF) ---
mot_src = Image.open("temp_photos/motion_person.jpg").convert("RGB")
mw, mh = mot_src.size
msz = min(mw, mh)
mot_crop = mot_src.crop(((mw-msz)//2, 0, (mw+msz)//2, msz)).resize((IMG_W, IMG_H), Image.Resampling.LANCZOS)

card6_img = mot_crop.copy()
d6 = ImageDraw.Draw(card6_img)

cx, cy = IMG_W // 2, IMG_H // 2
for rad in [48, 70, 95]:
    d6.arc([(cx-rad, cy-rad), (cx+rad, cy+rad)], start=210, end=330, fill="#a855f7", width=3)
    d6.arc([(cx-rad, cy-rad), (cx+rad, cy+rad)], start=30, end=150, fill="#a855f7", width=3)

# Play Button Glassmorphism Circle
d6.ellipse([(cx-28, cy-28), (cx+28, cy+28)], fill="#0f172add", outline="#8b5cf6", width=3)
d6.polygon([(cx-7, cy-12), (cx+13, cy), (cx-7, cy+12)], fill="#ffffff")

# Audio spectrum bars at bottom
bar_x = cx - 60
for h_bar in [8, 16, 26, 12, 22, 30, 18, 25, 14, 20]:
    d6.rounded_rectangle([(bar_x, IMG_H - 10 - h_bar), (bar_x + 6, IMG_H - 10)], radius=2, fill="#c084fc")
    bar_x += 12

draw_pill(d6, (10, 10, 75, 26), "VIDEO GIF", "#000000cc", "#8b5cf6", "#c084fc")
# Clean live motion pill with non-overlapping dot
draw_pill(d6, (IMG_W-95, 10, IMG_W-10, 26), "   LIVE MOTION", "#000000cc", "#ef4444", "#ffffff")
d6.ellipse([(IMG_W-89, 15), (IMG_W-83, 21)], fill="#ef4444")


# --- COMBINE INTO THE 2x3 SYMMETRICAL GRID ---
cards_data = [
    (card1_img, "1. HD TINIQLASHTIRISH", "Xira va eski yuzlarni 4K aniq tiklash", "HD RESTORE", "#00f2fe"),
    (card2_img, "2. RANGLI QILISH", "Oq-qoradan to'liq tabiiy rangga o'tkazish", "COLORIZE", "#ff3366"),
    (card3_img, "3. FONNI O'CHIRISH", "Orqa fonni tozalash va PNG stiker qilish", "REMOVE BG", "#10b981"),
    (card4_img, "4. 3x4 PASPORT FORMAT", "Hujjatlar va viza uchun tayyor 6 talik varaq", "PASSPORT", "#f59e0b"),
    (card5_img, "5. ANIME & ART STILI", "Suratni qahramon va komiksga aylantirish", "ANIME ART", "#ec4899"),
    (card6_img, "6. JONLI HARAKAT", "Qotgan suratlardan animatsion GIF yaratish", "MOTION GIF", "#8b5cf6")
]

idx = 0
for r_idx, y in enumerate(ROWS_Y):
    for c_idx, x in enumerate(COLS_X):
        if idx >= len(cards_data):
            break
        img_thumb, title, desc, badge_txt, col_hex = cards_data[idx]
        
        # 1. Karta tashqi foni va chegarasi (100% teng o'lcham: 380 x 290)
        draw.rounded_rectangle([(x, y), (x + CARD_W, y + CARD_H)], radius=12, fill="#0b1120", outline=col_hex, width=2)
        
        # 2. Ichki rasm (100% teng o'lcham: 360 x 185)
        canvas.paste(img_thumb, (x + 10, y + 10))
        
        # 3. Karta ichidagi rasmga nozik chegara
        draw.rounded_rectangle([(x + 10, y + 10), (x + 10 + IMG_W, y + 10 + IMG_H)], radius=6, outline="#334155", width=1)
        
        # 4. Badge (Stiker-nishon)
        badge_w = 96
        draw.rounded_rectangle([(x + 12, y + IMG_H + 18), (x + 12 + badge_w, y + IMG_H + 42)], radius=6, fill="#030712", outline=col_hex, width=1)
        draw.text((x + 18, y + IMG_H + 22), badge_txt, fill=col_hex, font=f_pill)
        
        # 5. Sarlavha (Katta, qalin, oq rang)
        draw.text((x + 118, y + IMG_H + 21), title, fill="#ffffff", font=f_card_title)
        
        # 6. Qisqa izoh (Och kulrang)
        draw.text((x + 14, y + IMG_H + 52), desc, fill="#94a3b8", font=f_card_desc)
        
        idx += 1

# Saqlash
out_desktop = r"c:\Users\Yutech\Desktop\welcome.jpg"
out_bot = r"c:\Users\Yutech\Desktop\IT\FrontEnd\bot\welcome.jpg"

canvas.save(out_desktop, "JPEG", quality=98)
canvas.save(out_bot, "JPEG", quality=98)
print("SUCCESSFULLY_SAVED_MASTER_WELCOME_BANNER_V2")
