import asyncio
import logging
import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

logger = logging.getLogger(__name__)

# 1. HD TINIQLASHTIRISH (ENHANCE)
async def enhance_image(input_path: str, output_path: str) -> str:
    def _process_local(inp, out):
        with Image.open(inp) as img:
            img = img.convert("RGB")
            w, h = img.size
            if max(w, h) < 1800:
                scale = min(2.5, 2000 / max(w, h))
                img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
            
            img = img.filter(ImageFilter.SMOOTH_MORE)
            img = img.filter(ImageFilter.UnsharpMask(radius=2.5, percent=190, threshold=3))
            img = img.filter(ImageFilter.DETAIL)
            
            img = ImageEnhance.Contrast(img).enhance(1.25)
            img = ImageEnhance.Sharpness(img).enhance(1.4)
            img = ImageEnhance.Brightness(img).enhance(1.04)
            
            img.save(out, "JPEG", quality=95, optimize=True)
            return out

    try:
        from gradio_client import Client, handle_file
        loop = asyncio.get_running_loop()
        def _call_gradio():
            client = Client("TencentARC/GFPGAN")
            result = client.predict(
                img=handle_file(input_path),
                version="v1.4",
                scale=2,
                api_name="/predict"
            )
            if result and os.path.exists(result):
                with Image.open(result) as res_img:
                    res_img.convert("RGB").save(output_path, "JPEG", quality=95)
                return output_path
            return None

        res = await asyncio.wait_for(loop.run_in_executor(None, _call_gradio), timeout=25)
        if res and os.path.exists(res):
            return res
    except Exception as e:
        logger.warning(f"Onlayn GFPGAN AI: ({e}), lokal algoritm ishlatildi.")

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _process_local, input_path, output_path)


# 2. RANGLI QILISH (COLORIZE)
async def colorize_image(input_path: str, output_path: str) -> str:
    def _process_colorize_local(inp, out):
        with Image.open(inp) as img:
            img = img.convert("RGB")
            w, h = img.size
            if max(w, h) < 1600:
                scale = min(2.0, 1600 / max(w, h))
                img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
                
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=2))
            gray = ImageOps.grayscale(img)
            colorized = ImageOps.colorize(gray, black="#1a110a", mid="#b88358", white="#fff4e6")
            final = Image.blend(img, colorized, alpha=0.65)
            final = ImageEnhance.Color(final).enhance(1.45)
            final = ImageEnhance.Contrast(final).enhance(1.15)
            final.save(out, "JPEG", quality=95, optimize=True)
            return out

    try:
        from gradio_client import Client, handle_file
        loop = asyncio.get_running_loop()
        def _call_colorize():
            client = Client("ariG23498/deoldify")
            result = client.predict(
                image=handle_file(input_path),
                render_factor=35,
                api_name="/predict"
            )
            if result and os.path.exists(result):
                with Image.open(result) as res_img:
                    res_img.convert("RGB").save(output_path, "JPEG", quality=95)
                return output_path
            return None

        res = await asyncio.wait_for(loop.run_in_executor(None, _call_colorize), timeout=25)
        if res and os.path.exists(res):
            return res
    except Exception as e:
        logger.warning(f"Onlayn Colorize AI: ({e}), lokal algoritm ishlatildi.")

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _process_colorize_local, input_path, output_path)


# 3. FONNI O'CHIRISH (REMOVE BACKGROUND / PNG STICKER)
async def remove_bg(input_path: str, output_path: str) -> str:
    def _process_remove_bg(inp, out):
        # 1. Eng zamonaviy neyrotarmoqli AI fon tozalash (rembg u2netp)
        try:
            from rembg import remove, new_session
            session = new_session("u2netp")
            with Image.open(inp) as img:
                res = remove(img, session=session)
                res.save(out, "PNG")
            return out
        except Exception as e:
            logger.warning(f"rembg ishlatishda ogohlantirish: {e}. OpenCV fallback ishlatiladi.")

        # 2. OpenCV GrabCut fallback
        cv_img = cv2.imread(inp)
        if cv_img is None:
            raise ValueError("Rasm o'qilmadi")
            
        h, w = cv_img.shape[:2]
        mask = np.zeros((h, w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        rect = (int(w * 0.05), int(h * 0.05), int(w * 0.9), int(h * 0.9))
        cv2.grabCut(cv_img, mask, rect, bgd_model, fgd_model, 4, cv2.GC_INIT_WITH_RECT)
        
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        mask_blurred = cv2.GaussianBlur(mask2 * 255, (7, 7), 0)
        
        b, g, r = cv2.split(cv_img)
        rgba = [b, g, r, mask_blurred]
        dst = cv2.merge(rgba, 4)
        
        cv2.imwrite(out, dst)
        return out

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _process_remove_bg, input_path, output_path)


# 4. 3x4 HUJJATGA RASM (PASSPORT 3x4 + 6 TALIK QOG'OZ + KOSTYUMLI FORMAT)
async def passport_3x4(input_path: str, output_path: str, wear_suit: bool = True) -> str:
    def _process_passport(inp, out):
        with Image.open(inp) as img:
            img = img.convert("RGB")
            w, h = img.size
            
            # 1. Orqa fonni tozalab oppoq pasport foni qilish
            try:
                from rembg import remove, new_session
                session = new_session("u2netp")
                cutout = remove(img, session=session)
                white_canvas = Image.new("RGB", (w, h), color="#ffffff")
                white_canvas.paste(cutout, (0, 0), cutout)
                img = white_canvas
            except Exception as e:
                logger.warning(f"Passport bg rembg error: {e}")

            # 2. Kostyum / Klassik ko'ylak kiydirish
            suit_path = os.path.join(os.path.dirname(__file__), "assets", "suit_clean_collar.png")
            if wear_suit and os.path.exists(suit_path):
                try:
                    suit = Image.open(suit_path).convert("RGBA")
                    sw, sh = suit.size
                    # Kostyum eni odam yelkasiga moslanadi
                    scale = (w * 1.65) / sw
                    suit_scaled = suit.resize((int(w * 1.65), int(sh * scale)), Image.Resampling.LANCZOS)
                    suit_x = (w - int(w * 1.65)) // 2
                    suit_y = int(h * 0.52)
                    img.paste(suit_scaled, (suit_x, suit_y), suit_scaled)
                except Exception as se:
                    logger.warning(f"Passport suit overlay error: {se}")

            # 3. 3x4 proporsiyasida markaziy qirqish
            target_aspect = 3.0 / 4.0
            current_aspect = w / h
            
            if current_aspect > target_aspect:
                new_w = int(h * target_aspect)
                left = (w - new_w) // 2
                img = img.crop((left, 0, left + new_w, h))
            else:
                new_h = int(w / target_aspect)
                top = int((h - new_h) * 0.15)
                img = img.crop((0, top, w, top + new_h))
            
            # Standart 3x4 piksel o'lchami (600x800)
            single = img.resize((600, 800), Image.Resampling.LANCZOS)
            single = ImageEnhance.Sharpness(single).enhance(1.25)
            single = ImageEnhance.Contrast(single).enhance(1.08)
            
            # 6 talik bosma qog'oz varag'i (10x15 sm foto qog'oz, 1800x1200)
            sheet = Image.new("RGB", (1800, 1200), color="#ffffff")
            thumb = single.resize((480, 640), Image.Resampling.LANCZOS)
            thumb = ImageOps.expand(thumb, border=2, fill="#cbd5e1")
            
            # 6 ta rasmni varaqqa chizish (2 qator, 3 ustun)
            for pos in [(80, 50), (660, 50), (1240, 50), (80, 730), (660, 730), (1240, 730)]:
                sheet.paste(thumb, pos)
            
            sheet.save(out, "JPEG", quality=96)
            return out

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _process_passport, input_path, output_path)


# 7. GOOGLE GEMINI AI (UNIVERSAL INTELLIGENCE & 24/7 SUPPORT WITH MEMORY)
user_ai_history = {}  # user_id -> list of {"role": "user"|"model", "parts": [{"text": ...}]}

async def ask_gemini_ai(prompt: str, user_id: int = 0, reset_history: bool = False) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return "Gemini API kaliti ulanmagan. Iltimos admin bilan bog'laning."
    import aiohttp
    
    # 1. Foydalanuvchi suhbat xotirasi
    if reset_history or user_id not in user_ai_history:
        user_ai_history[user_id] = []
        
    history = user_ai_history[user_id]
    history.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })
    
    # Oxirgi 10 ta xabarni (5 ta savol-javob) xotirada saqlash
    if len(history) > 10:
        history = history[-10:]
        user_ai_history[user_id] = history

    # 2. Universal, erkin va chuqur fikrlovchi haqiqiy AI ko'rsatmasi
    system_instruction = (
        "Siz erkin, nihoyatda bilimdon, har tomonlama chuqur fikrlovchi va samimiy haqiqiy Sun'iy Intellektsiz "
        "(xuddi eng ilg'or Google Gemini / ChatGPT kabi).\n\n"
        "ASOSIY QOIDALAR:\n"
        "1. Foydalanuvchi sizdan nima so'rasa ham — xoh fan, matematika, fizika, tarix, axborot texnologiyalari, "
        "dasturlash (Python, JS va h.k.), biznes, falsafa, psixologiya, hayotiy maslahat, xoh she'r, hikoya, hazil yoki "
        "oddiy samimiy suhbat bo'lsin — barcha mavzularda to'liq, erkin, jonli va insoniy tarzda javob bering.\n"
        "2. HECH QACHON qotib qolgan qolip, shablon yoki cheklangan avtomatik botga o'xshab javob bermang! "
        "Har doim jonli, qiziqarli, mulohazali va yuqori intellektli suhbatdosh bo'ling.\n"
        "3. Siz shuningdek 'Xotira AI' (@xotira_ai_bot) fotostudiyasida yordamchisiz. Agar foydalanuvchi aynan fotosuratlar, "
        "ularni tahrirlash yoki bot xizmatlari haqida so'rasa, quyidagi barcha imkoniyatlar bo'yicha to'liq yordam bering:\n"
        "   • ✨ 1. HD Tiniqlashtirish: Xira, sifatiz va eski suratlarni 4K tiniq holatga keltiradi.\n"
        "   • 🎨 2. Rangli qilish: Tarixiy oq-qora suratlarga tabiiy, jonli ranglar beradi.\n"
        "   • 🖼 3. Fonni o'chirish: Insonning kiyimi va sochlarini aslo kesmasdan, orqa fonni tozalab shaffof PNG stiker qiladi.\n"
        "   • 👔 4. 3x4 Pasport formati: Rasmiy hujjatlar uchun oppoq fon va avtomatik klassik kostyum-galstuk kiydirib, chop etishga tayyor 6 talik varaq qilib beradi.\n"
        "   • 🎭 5. Anime & Art stili: Suratni komiks va anime san'at asariga aylantiradi.\n"
        "   • 👀 6. Jonli harakat (GIF): Qotgan suratlarga harakat berib, jonli animatsiya yaratadi.\n"
        "   • Bot ma'lumotlari: Ro'yxatdan o'tganda 3 ta bepul urinish beriladi. Do'stlarni taklif qilsa har biriga +2 ta urinish. "
        "Tariflar: 10 ta rasm (15 000 so'm), 30 ta rasm (35 000 so'm), 100 ta rasm (75 000 so'm). To'lovlar Click, Payme, Uzum Bank orqali qabul qilinadi.\n"
        "4. Muloqot tili: Asosan o'zbek tili. Agar foydalanuvchi rus, ingliz yoki boshqa tilda yozsa, o'sha tilda ham erkin javob bering.\n"
        "Har doim foydalanuvchiga do'stona, yuqori intellekt bilan va erkin yordam bering!"
    )
    
    models = ["gemini-3.5-flash-lite", "gemini-flash-lite-latest"]
    
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": history
    }
    
    reply_text = ""
    for attempt in range(2):
        for model_name in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                if parts:
                                    reply_text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                                    if reply_text:
                                        break
                        elif resp.status == 503:
                            logger.warning(f"Gemini {model_name} HTTP 503 (vaqtincha band), 1.2 soniya kutilmoqda...")
                            await asyncio.sleep(1.2)
                            continue
                        else:
                            err_text = await resp.text()
                            logger.warning(f"Gemini {model_name} HTTP {resp.status}: {err_text[:120]}")
            except Exception as e:
                logger.warning(f"Model {model_name} xatolik: {e}, keyingi modelga o'tilmoqda...")
                continue
        if reply_text:
            break
            
    if reply_text:
        history.append({
            "role": "model",
            "parts": [{"text": reply_text}]
        })
        return reply_text
    else:
        # Xatolik yuz berganda xotira buzilmasligi uchun oxirgi user xabarini chiqarib tashlash
        if history and history[-1].get("role") == "user":
            history.pop()
        
    return "Hozirda AI modellar band. Iltimos, birozdan so'ng qayta urinib ko'ring yoki /start bosing."


# 5. ANIME / ART / KOMIKS STILI (CARTOONIZE)
async def cartoonize_image(input_path: str, output_path: str) -> str:
    def _process_cartoon(inp, out):
        cv_img = cv2.imread(inp)
        if cv_img is None:
            raise ValueError("Rasm o'qilmadi")
            
        # O'lchamni optimallashtirish
        h, w = cv_img.shape[:2]
        if max(h, w) > 1200:
            scale = 1200 / max(h, w)
            cv_img = cv2.resize(cv_img, (int(w * scale), int(h * scale)))
            
        # 1. Chegaralarni (qora konturlarni) aniqlash
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 5)
        edges = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9
        )
        
        # 2. Ranglarni yumshatish (Bilateral filter orqali akvarel/anime effekti)
        color = cv2.bilateralFilter(cv_img, d=9, sigmaColor=250, sigmaSpace=250)
        
        # 3. Rang va konturni birlashtirish
        cartoon = cv2.bitwise_and(color, color, mask=edges)
        
        # 4. Rang to'yinganligini oshirish
        pil_img = Image.fromarray(cv2.cvtColor(cartoon, cv2.COLOR_BGR2RGB))
        pil_img = ImageEnhance.Color(pil_img).enhance(1.5)
        pil_img = ImageEnhance.Contrast(pil_img).enhance(1.2)
        
        pil_img.save(out, "JPEG", quality=95)
        return out

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _process_cartoon, input_path, output_path)


# 6. JONLI HARAKAT (LIVE MOTION ANIMATED GIF)
async def animate_motion(input_path: str, output_path: str) -> str:
    def _process_animation(inp, out):
        with Image.open(inp) as base_img:
            base_img = base_img.convert("RGB")
            # Kvadrat yoki ixcham o'lchamga keltirish
            w, h = base_img.size
            if max(w, h) > 800:
                scale = 800 / max(w, h)
                base_img = base_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
                
            w, h = base_img.size
            frames = []
            
            # Sekin yaqinlashish (Zoom-in) va nafas olish (breathing) effekti kadrlarini yaratish
            num_frames = 14
            for i in range(num_frames):
                # 0 dan 1 gacha sinusoid tebranish
                t = (1 - np.cos(i / num_frames * 2 * np.pi)) / 2
                zoom_factor = 1.0 + (t * 0.06) # 6% zoom
                
                crop_w = int(w / zoom_factor)
                crop_h = int(h / zoom_factor)
                left = (w - crop_w) // 2
                top = (h - crop_h) // 2
                
                cropped = base_img.crop((left, top, left + crop_w, top + crop_h))
                frame = cropped.resize((w, h), Image.Resampling.BILINEAR)
                
                # Yengil yorug'lik pulsi (hayotiy jilo)
                bright = 1.0 + (t * 0.05)
                frame = ImageEnhance.Brightness(frame).enhance(bright)
                frames.append(frame)
                
            frames[0].save(
                out,
                save_all=True,
                append_images=frames[1:],
                optimize=True,
                duration=100,
                loop=0
            )
            return out

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _process_animation, input_path, output_path)
