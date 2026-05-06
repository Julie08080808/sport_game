from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from google.cloud import texttospeech
import io
import os
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

@router.post("/tts")
async def text_to_speech(data: dict):
    """
    接收前端文字，回傳 Google TTS 產生的 MP3 音訊串流
    """
    text = data.get("text")
    is_ssml = data.get("is_ssml", False)

    if not text:
        raise HTTPException(status_code=400, detail="請提供文字內容")

    try:
        # 初始化 Google TTS 客戶端
        # 此時它會去讀取我們在上方 os.environ 設定的 JSON_KEY_PATH
        client = texttospeech.TextToSpeechClient()

        # 設定合成請求
        # SSML 用於處理材料清單中的停頓，純文字用於一般描述
        input_text = texttospeech.SynthesisInput(ssml=text) if is_ssml else texttospeech.SynthesisInput(text=text)
        
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
        print(f"---------------------------\n")
        
        raise HTTPException(
            status_code=500, 
            detail=f"語音服務暫時不可用，請檢查後端日誌"
        )