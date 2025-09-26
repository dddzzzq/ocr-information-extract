import os
import requests
import json
import cv2
import numpy as np
from typing import Dict
from paddleocr import PaddleOCR
from fastapi import HTTPException

# --- 初始化 PaddleOCR ---
# 为了提高效率，这个实例在应用启动时创建一次。
# lang='ch' 表示启用中文识别。
try:
    print("--- 正在初始化 PaddleOCR 引擎... ---")
    ocr = PaddleOCR(use_angle_cls=True, lang='ch')
    print("--- PaddleOCR 引擎初始化成功。 ---")
except Exception as e:
    print(f"--- 初始化 PaddleOCR 失败: {e} ---")
    print("--- 请确保已正确安装 PaddlePaddle。 ---")
    print("--- CPU 版本: pip install paddlepaddle ---")
    print("--- GPU 版本: 请参考 PaddleOCR 官方文档进行安装。 ---")
    ocr = None

def ocr_processing(image_bytes: bytes) -> str:
    """
    使用真实的 PaddleOCR 处理图片字节流并提取文字。
    
    :param image_bytes: 图片文件的字节内容。
    :return: 识别出的所有文本拼接成的字符串。
    """
    if ocr is None:
        raise RuntimeError("PaddleOCR 未能成功初始化，请检查安装和服务器日志。")

    print(f"--- [Real OCR] 正在处理 {len(image_bytes)} 字节的图片... ---")
    
    # 将字节流转换为 OpenCV 可以处理的 numpy 数组
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("无法从字节流解码图片，请检查图片格式是否正确。")

    # 执行 OCR 识别
    # 错误修复：移除了 'cls=True' 参数，因为在初始化时已通过 use_angle_cls=True 启用。
    result = ocr.ocr(img)
    
    # 提取并组合所有识别出的文本行
    lines = []
    if result and result[0] is not None:
        for i in range(len(result[0]['rec_texts'])):
            text = result[0]['rec_texts'][i]
            confidence = result[0]['rec_scores'][i]

            if confidence >= 0:
                print(f"识别到文本: '{text}' (置信度: {confidence:.4f})")
            else:
                print(f"识别到文本: '{text}' (无置信度信息)")
            lines.append(text)

    full_text = "\n".join(lines)
    print("--- [Real OCR] 文本识别完成。 ---")
    return full_text


def llm_summarization(text: str) -> Dict[str, str]:
    """
    调用 DeepSeek API，将文本规整为结构化的 JSON 数据。
    
    :param text: OCR 识别出的原始文本。
    :return: 包含海报信息的字典。
    """

    DEEPSEEK_API_KEY="sk-1d7cdcb3826b4008a4be4ee2ae8f9f52"
    api_key = DEEPSEEK_API_KEY
    if not api_key:
        raise ValueError("环境变量 DEEPSEEK_API_KEY 未设置。")

    url = "https://api.deepseek.com/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # 精心设计的提示词 (Prompt)，引导 LLM 输出期望的 JSON 格式
    prompt = f"""
    你是一个信息提取专家。请从以下校园海报OCR识别出的文本中，提取关键信息，并严格按照JSON格式返回。
    需要提取的字段包括：
    - "title": 活动的完整主题
    - "date": 活动日期 (例如: 2025年10月28日)
    - "time": 活动时间 (例如: 下午 14:30)
    - "location": 活动地点
    - "organizer": 主办方或承办单位
    - "summary": 对活动内容的简短总结 (2-3句话)
    如果某个字段在文本中找不到对应信息，请将该字段的值设为 "未能识别"。
    请确保你的回答是一个干净、合法、无任何多余解释的JSON对象。

    待处理的原始文本如下：
    ---
    {text}
    ---
    """

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个只输出JSON格式的高效信息提取助手。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,  # 使用较低的温度以获得更稳定、一致的输出
        "response_format": {"type": "json_object"} # 强制模型输出 JSON 对象
    }
    
    print("--- [Real LLM] 正在向 DeepSeek API 发送请求... ---")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status() # 如果状态码不是 2xx，则抛出异常

        print("--- [Real LLM] 已成功收到 API 的响应。 ---")
        response_data = response.json()
        content_str = response_data['choices'][0]['message']['content']
        
        # 解析 LLM 返回的 JSON 字符串
        structured_info = json.loads(content_str)
        return structured_info

    except requests.exceptions.Timeout:
        print("--- [Real LLM] Error: 请求 DeepSeek API 超时。 ---")
        raise HTTPException(status_code=408, detail="请求大语言模型超时，请稍后重试。")
    except requests.exceptions.RequestException as e:
        print(f"--- [Real LLM] Error: API 请求失败: {e} ---")
        raise HTTPException(status_code=502, detail=f"调用大语言模型服务失败: {e}")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"--- [Real LLM] Error: 解析 LLM 响应失败: {e} ---")
        raise HTTPException(status_code=500, detail="解析大语言模型返回的数据时出错。")

