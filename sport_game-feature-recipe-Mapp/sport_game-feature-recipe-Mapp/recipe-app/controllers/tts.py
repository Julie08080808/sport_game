import re  # 必須引入正規表達式模組
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from google.cloud import texttospeech
import io
import os
from dotenv import load_dotenv

# 1. 取得路徑設定 (保持原本邏輯)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
JSON_KEY_PATH = os.path.join(BASE_DIR, "google-key.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = JSON_KEY_PATH

load_dotenv()

router = APIRouter()

def convert_large_numbers(text: str) -> str:
    """
    將阿拉伯數字轉換為中文數字（針對千位數）：
    - 1000 → 一千
    - 2000 → 二千
    - 3000 → 三千
    等等...
    """
    if not text:
        return ""
    
    def replace_number(match):
        num_str = match.group(0)
        num = int(num_str)
        
        # 中文數字映射
        chinese_digits = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']
        
        # 處理千位 (1000-9999)
        if 1000 <= num <= 9999:
            thousands = num // 1000
            remainder = num % 1000
            
            if remainder == 0:
                # 例如：1000 → 一千，2000 → 二千
                return chinese_digits[thousands] + '千'
            else:
                # 例如：1500 → 一千五百
                hundreds = remainder // 100
                tens = (remainder % 100) // 10
                ones = remainder % 10
                
                result = chinese_digits[thousands] + '千'
                
                if hundreds > 0:
                    result += chinese_digits[hundreds] + '百'
                elif tens > 0 or ones > 0:
                    result += '零'
                
                if tens > 0:
                    result += chinese_digits[tens] + '十'
                elif ones > 0:
                    result += '零'
                
                if ones > 0:
                    result += chinese_digits[ones]
                
                return result
        
        # 處理百位 (100-999)
        elif 100 <= num <= 999:
            hundreds = num // 100
            remainder = num % 100
            
            result = chinese_digits[hundreds] + '百'
            
            if remainder == 0:
                return result
            elif remainder < 10:
                result += '零' + chinese_digits[remainder]
            else:
                tens = remainder // 10
                ones = remainder % 10
                result += chinese_digits[tens] + '十'
                if ones > 0:
                    result += chinese_digits[ones]
            
            return result
        
        # 其他數字保持原樣
        return num_str
    
    # 匹配三位以上的純數字（百位以上），使用正向前瞻
    # 改為更寬鬆的匹配：數字後面可以接任何字符或結尾
    text = re.sub(r'\d{3,}(?=\D|$)', replace_number, text)
    
    return text

def add_ssml_pauses(text: str) -> str:
    """
    在材料列表中的每一項後面添加 0.5 秒的停頓 (SSML <break> 標籤)
    
    例如：
    蝦仁二兩，豆腐兩塊，鹽三克
    →
    蝦仁二兩<break time="500ms"/>豆腐兩塊<break time="500ms"/>鹽三克
    
    朗讀效果：
    1. 朗讀「蝦仁二兩」
    2. 停頓 0.5 秒
    3. 朗讀「豆腐兩塊」
    4. 停頓 0.5 秒
    5. 朗讀「鹽三克」
    """
    if not text:
        return ""
    
    # 在所有「、」（中文頓號）之後插入 0.5 秒停頓
    text = text.replace("、", "<break time='500ms'/>")
    
    # 在所有「，」（中文逗號）之後插入 0.5 秒停頓
    text = text.replace("，", "<break time='500ms'/>")
    
    return text

def clean_text_for_tts(text: str) -> str:
    """
    優化 TTS 朗讀內容：
    1. 先將 CC/cc 轉換為「毫升」
    2. 將大數字轉換為中文（如 1000 → 一千）
    3. 移除數字後方多餘的 .00
    4. 在材料列表中插入 SSML 停頓標籤（0.5 秒）
    """
    if not text:
        return ""

    # --- 第一步：先處理 CC 問題 ---
    # 將 CC 或 cc 替換成「毫升」，這在食譜中聽起來最自然
    text = text.replace("CC", "毫升").replace("cc", "毫升")

    # --- 第二步：處理數字小數點問題 ---
    # 1. 把 2.00 這種格式變成 2 (移除 .00)
    text = re.sub(r'(\d+)\.00(?!\d)', r'\1', text)
    
    # 2. 把 2.50 這種格式變成 2.5 (移除結尾多餘的 0)
    text = re.sub(r'(\d+\.[1-9])0+(?!\d)', r'\1', text)

    # --- 第三步：轉換大數字為中文 ---
    text = convert_large_numbers(text)

    # --- 第四步：添加 SSML 停頓標籤（0.5 秒） ---
    text = add_ssml_pauses(text)

    return text

@router.post("/tts")
async def text_to_speech(data: dict):
    """
    接收前端文字，清理後回傳 Google TTS 音訊
    
    處理流程：
    1. 清理文字（CC→毫升、數字轉換、插入停頓標籤）
    2. 檢測是否有 SSML 標籤
    3. 用正確的模式發送給 Google TTS
    
    支持兩種模式：
    - is_ssml=False (預設)：純文字，自動清理並插入停頓
    - is_ssml=True：SSML 文字（包含停頓標籤），直接送入合成
    """
    text = data.get("text")
    is_ssml = data.get("is_ssml", False)

    if not text:
        raise HTTPException(status_code=400, detail="請提供文字內容")

    # --- 關鍵步驟：在合成前先清理文字 ---
    processed_text = clean_text_for_tts(text)
    
    # 當有停頓標籤時，強制使用 SSML 模式
    has_ssml_tags = "<break" in processed_text
    use_ssml = is_ssml or has_ssml_tags
    
    # 如果使用 SSML，用 <speak> 標籤包裝文字
    if use_ssml:
        processed_text = f"<speak>{processed_text}</speak>"

    try:
        client = texttospeech.TextToSpeechClient()

        # 使用處理過的 processed_text 送入合成引擎
        input_text = (
            texttospeech.SynthesisInput(ssml=processed_text) 
            if use_ssml 
            else texttospeech.SynthesisInput(text=processed_text)
        )
        
        voice = texttospeech.VoiceSelectionParams(
            language_code="zh-TW", 
            name="cmn-TW-Wavenet-A", 
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            request={"input": input_text, "voice": voice, "audio_config": audio_config}
        )
        
        return StreamingResponse(
            io.BytesIO(response.audio_content), 
            media_type="audio/mpeg"
        )

    except Exception as e:
        print(f"\n--- ❌ TTS 運作錯誤診斷 ---")
        print(f"錯誤訊息: {str(e)}")
        print(f"處理後文字: {processed_text}")
        print(f"使用 SSML 模式: {use_ssml}")
        print(f"---------------------------\n")
        
        raise HTTPException(
            status_code=500, 
            detail="語音服務暫時不可用"
        )