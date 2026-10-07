from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from google.cloud import texttospeech
import io
import os
import re
from dotenv import load_dotenv

# 1. 取得當前檔案 (tts.py) 的絕對路徑
# 因為 tts.py 在 controllers/ 資料夾內，所以要往上跳一層回到專案根目錄
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)

# 2. 定義 JSON 憑證的絕對路徑
# 這會組合成類似 C:\Users\YourName\RECIPE-APP\google-key.json
JSON_KEY_PATH = os.path.join(BASE_DIR, "google-key.json")

# 3. 強制將環境變數指向這個絕對路徑 (這比改 .env 更保險)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = JSON_KEY_PATH

# 加載 .env (保留原本其他可能的設定)
load_dotenv()

router = APIRouter()


def convert_large_numbers(text: str) -> str:
    """
    將阿拉伯數字轉換為中文數字（針對百位、千位數），讓 TTS 唸起來更自然：
    - 1000 → 一千 / 1500 → 一千五百
    - 100 → 一百 / 150 → 一百五十
    """
    if not text:
        return ""

    def replace_number(match):
        num_str = match.group(0)
        num = int(num_str)

        chinese_digits = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']

        if 1000 <= num <= 9999:
            thousands = num // 1000
            remainder = num % 1000

            if remainder == 0:
                return chinese_digits[thousands] + '千'

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

        return num_str

    text = re.sub(r'\d{3,}(?=\D|$)', replace_number, text)
    return text


def add_ssml_pauses(text: str) -> str:
    """在中文頓號/逗號之後插入 0.5 秒停頓(SSML <break>)，材料列表唸起來比較不急促。"""
    if not text:
        return ""

    text = text.replace("、", "<break time='500ms'/>")
    text = text.replace("，", "<break time='500ms'/>")
    return text


def clean_text_for_tts(text: str) -> str:
    """
    優化 TTS 朗讀內容：
    1. CC/cc → 毫升
    2. 移除數字結尾多餘的 .00 / 無意義小數尾零
    3. 大數字轉中文(1000 → 一千)
    4. 材料列表插入 SSML 停頓
    """
    if not text:
        return ""

    text = text.replace("CC", "毫升").replace("cc", "毫升")
    text = re.sub(r'(\d+)\.00(?!\d)', r'\1', text)
    text = re.sub(r'(\d+\.[1-9])0+(?!\d)', r'\1', text)
    text = convert_large_numbers(text)
    text = add_ssml_pauses(text)

    return text


@router.post("/tts")
async def text_to_speech(data: dict):
    """
    接收前端文字，清理後回傳 Google TTS 產生的 MP3 音訊串流
    """
    text = data.get("text")
    is_ssml = data.get("is_ssml", False)

    if not text:
        raise HTTPException(status_code=400, detail="請提供文字內容")

    # 合成前先清理文字(數字轉中文、加停頓)；清理後若出現停頓標籤，強制走 SSML 模式。
    processed_text = clean_text_for_tts(text)
    has_ssml_tags = "<break" in processed_text
    use_ssml = is_ssml or has_ssml_tags

    if use_ssml:
        processed_text = f"<speak>{processed_text}</speak>"

    try:
        # 初始化 Google TTS 客戶端
        # 此時它會去讀取我們在上方 os.environ 設定的 JSON_KEY_PATH
        client = texttospeech.TextToSpeechClient()

        # 設定合成請求
        # SSML 用於處理材料清單中的停頓，純文字用於一般描述
        input_text = texttospeech.SynthesisInput(ssml=processed_text) if use_ssml else texttospeech.SynthesisInput(text=processed_text)

        # 設定語音參數 (台灣女聲)
        voice = texttospeech.VoiceSelectionParams(
            language_code="zh-TW", 
            name="cmn-TW-Wavenet-A", 
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
        )

        # 設定音訊格式
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        # 向 Google 伺服器請求語音合成
        response = client.synthesize_speech(
            request={"input": input_text, "voice": voice, "audio_config": audio_config}
        )
        
        # 回傳音訊串流
        return StreamingResponse(
            io.BytesIO(response.audio_content), 
            media_type="audio/mpeg"
        )

    except Exception as e:
        # 發生錯誤時，在終端機印出詳細診斷資訊
        print(f"\n--- ❌ TTS 運作錯誤診斷 ---")
        print(f"錯誤訊息: {str(e)}")
        print(f"嘗試讀取的路徑: {JSON_KEY_PATH}")
        print(f"檔案是否存在: {os.path.exists(JSON_KEY_PATH)}")
        print(f"處理後文字: {processed_text}")
        print(f"使用 SSML 模式: {use_ssml}")
        print(f"---------------------------\n")
        
        raise HTTPException(
            status_code=500, 
            detail=f"語音服務暫時不可用，請檢查後端日誌"
        )