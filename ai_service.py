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
        # OpenCV GrabCut + Threshold yordamida orqa fonni ajratish
        cv_img = cv2.imread(inp)
        if cv_img is None:
            raise ValueError("Rasm o'qilmadi")
            
        h, w = cv_img.shape[:2]
        mask = np.zeros((h, w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        # Asosiy ob'ekt markazda joylashgan degan taxmin bilan chegaralash
        rect = (int(w * 0.05), int(h * 0.05), int(w * 0.9), int(h * 0.9))
        cv2.grabCut(cv_img, mask, rect, bgd_model, fgd_model, 4, cv2.GC_INIT_WITH_RECT)
        
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        # Yumshoq chekkalar (anti-aliasing)
        mask_blurred = cv2.GaussianBlur(mask2 * 255, (7, 7), 0)
        
        # RGBA formatiga o'tkazish
        b, g, r = cv2.split(cv_img)
        rgba = [b, g, r, mask_blurred]
        dst = cv2.merge(rgba, 4)
        
        cv2.imwrite(out, dst)
        return out

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _process_remove_bg, input_path, output_path)


# 4. 3x4 HUJJATGA RASM (PASSPORT 3x4 + 6 TALIK QOG'OZ)
async def passport_3x4(input_path: str, output_path: str) -> str:
    def _process_passport(inp, out):
        with Image.open(inp) as img:
            img = img.convert("RGB")
            w, h = img.size
            
            # 3x4 proporsiyasida markaziy qirqish
            target_aspect = 3.0 / 4.0
            current_aspect = w / h
            
            if current_aspect > target_aspect:
                new_w = int(h * target_aspect)
                left = (w - new_w) // 2
                img = img.crop((left, 0, left + new_w, h))
            else:
                new_h = int(w / target_aspect)
                # Yuz teparoqda bo'lgani uchun yuqoridan ko'proq joy qoldirish
                top = int((h - new_h) * 0.25)
                img = img.crop((0, top, w, top + new_h))
            
            # Standart 3x4 piksel o'lchami (600x800)
            single = img.resize((600, 800), Image.Resampling.LANCZOS)
            # Tiniqlashtirish va yorug'likni rasmiy formatga moslash
            single = ImageEnhance.Sharpness(single).enhance(1.3)
            single = ImageEnhance.Contrast(single).enhance(1.1)
            
            # 6 talik bosma qog'oz varag'i (10x15 sm foto qog'oz)
            sheet = Image.new("RGB", (1800, 1200), color="#ffffff")
            
            # Kichik o'lchamda 6 ta rasmni joylashtirish (3 qator, 2 ustun yoki 2 qator 3 ustun)
            thumb = single.resize((500, 666), Image.Resampling.LANCZOS)
            # Rasmiy oq hoshiya
            thumb = ImageOps.expand(thumb, border=4, fill="#e0e0e0")
            
            positions = [
                (70, 70), (620, 70), (1170, 70),
                (70, 770), (620, 770), (1170, 770)
            ]
            
            # 6 ta rasmni varaqqa chizish
            for pos in [(80, 50), (640, 50), (1200, 50), (80, 730), (640, 730), (1200, 730)]:
                sheet.paste(thumb.resize((480, 640)), pos)
            
            sheet.save(out, "JPEG", quality=95)
            return out

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _process_passport, input_path, output_path)


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
