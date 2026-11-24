import asyncio
import logging
import os
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

logger = logging.getLogger(__name__)

async def enhance_image(input_path: str, output_path: str) -> str:
    """
    Eski va xira rasmni HD sifatga keltiradi.
    1-navbatda HuggingFace GFPGAN / neyrotarmog'iga ulanadi.
    Agar ulanish sekin yoki band bo'lsa, avtomatik yuqori sifatli algoritmik filtrlar bilan ishlaydi.
    """
    def _process_local(inp, out):
        with Image.open(inp) as img:
            img = img.convert("RGB")
            
            # Kichik rasmlarni kattalashtirish (Super-Resolution simulyatsiyasi)
            w, h = img.size
            if max(w, h) < 1600:
                scale = min(2.5, 1800 / max(w, h))
                new_w, new_h = int(w * scale), int(h * scale)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # 1. Shovqinni kamaytirish va chetlarni tekislash
            img = img.filter(ImageFilter.SMOOTH_MORE)
            
            # 2. Unsharp Mask orqali yuz va chiziqlarni kuchli tiniqlashtirish
            img = img.filter(ImageFilter.UnsharpMask(radius=2.5, percent=180, threshold=3))
            img = img.filter(ImageFilter.DETAIL)
            
            # 3. Kontrast va aniqlikni ko'tarish
            contrast = ImageEnhance.Contrast(img)
            img = contrast.enhance(1.25)
            
            sharpness = ImageEnhance.Sharpness(img)
            img = sharpness.enhance(1.4)
            
            brightness = ImageEnhance.Brightness(img)
            img = brightness.enhance(1.05)
            
            img.save(out, "JPEG", quality=95, optimize=True)
            return out

    # Onlayn AI sinab ko'rish (Hugging Face / Gradio)
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
        logger.warning(f"Onlayn GFPGAN AI ulanishida kutish/xatolik ({e}), lokal yuqori sifatli ishlov berish ishlatildi.")

    # Lokal filtr bilan yakunlash
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _process_local, input_path, output_path)


async def colorize_image(input_path: str, output_path: str) -> str:
    """
    Oq-qora rasmni rangli holatga keltiradi.
    """
    def _process_colorize_local(inp, out):
        with Image.open(inp) as img:
            img = img.convert("RGB")
            
            # Kattalashtirish va tiniqlashtirish
            w, h = img.size
            if max(w, h) < 1600:
                scale = min(2.0, 1600 / max(w, h))
                img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
                
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=2))
            
            # Tabiiy issiq rangli ohang berish (Warm sepia/vintage skin toning)
            gray = ImageOps.grayscale(img)
            # Issiq rangli palitrani hosil qilish
            colorized = ImageOps.colorize(gray, black="#1b120c", mid="#b88358", white="#fff4e6")
            
            # Asl tasvir bilan tabiiy uyg'unlashtirish
            final = Image.blend(img, colorized, alpha=0.65)
            
            color_enhancer = ImageEnhance.Color(final)
            final = color_enhancer.enhance(1.4)
            
            contrast = ImageEnhance.Contrast(final)
            final = contrast.enhance(1.15)
            
            final.save(out, "JPEG", quality=95, optimize=True)
            return out

    # Onlayn AI sinab ko'rish
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
        logger.warning(f"Onlayn Colorize AI ulanishida kutish/xatolik ({e}), lokal algoritmik rang berish ishlatildi.")

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _process_colorize_local, input_path, output_path)
