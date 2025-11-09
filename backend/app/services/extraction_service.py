import os
import requests
import json
import cv2 
import numpy as np
from typing import Dict
from paddleocr import PaddleOCR
from fastapi import HTTPException
import base64 
import httpx

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# --- 初始化 PaddleOCR ---
try:
    print("--- 正在初始化 PaddleOCR 引擎... ---")
    ocr = PaddleOCR(use_angle_cls=True, lang='ch')
    print("--- PaddleOCR 引擎初始化成功。 ---")
except Exception as e:
    print(f"--- 初始化 PaddleOCR 失败: {e} ---")
    ocr = None

# OCR处理
def ocr_processing(image_bytes: bytes) -> str:
    """
    (稳定版) 使用您在 extracted.txt 中提供的原始逻辑。
    """
    if ocr is None:
        raise RuntimeError("PaddleOCR 未能成功初始化，请检查安装和服务器日志。")

    print(f"--- [Real OCR] 正在处理 {len(image_bytes)} 字节的图片... ---")
    
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("无法从字节流解码图片，请检查图片格式是否正确。")

    result = ocr.ocr(img)
    lines = []
    
    if result and result[0] is not None:
        try:
            if 'rec_texts' in result[0] and 'rec_scores' in result[0]:
                for i in range(len(result[0]['rec_texts'])):
                    text = result[0]['rec_texts'][i]
                    confidence = result[0]['rec_scores'][i]

                    if confidence >= 0:
                        print(f"识别到文本: '{text}' (置信度: {confidence:.4f})")
                    else:
                        print(f"识别到文本: '{text}' (无置信度信息)")
                    lines.append(text)
            else:
                print("--- [Real OCR] 警告: 未检测到 'rec_texts'。尝试备用列表解析... ---")
                page_data = result[0]
                if isinstance(page_data, list):
                     for line_data in page_data:
                        if isinstance(line_data, (list, tuple)) and len(line_data) == 2:
                            text_info = line_data[1]
                            if isinstance(text_info, tuple) and len(text_info) == 2:
                                text = text_info[0]
                                if text:
                                    print(f"识别到文本 (备用): '{text}'")
                                    lines.append(text)
        except Exception as e:
            print(f"--- [Real OCR] 解析时发生错误 (已捕获): {e} ---")
            print(f"--- 原始 OCR 结果: {str(result)[:500]} ...")
            return ""

    full_text = "\n".join(lines)
    print("--- [Real OCR] 文本识别完成。 ---")
    return full_text


# 增加图片压缩逻辑
def llm_summarization(text: str, image_bytes: bytes) -> Dict[str, str]:
    """
    1. 在 Base64 编码前，对图片进行压缩和缩放
    
    :param text: OCR 识别出的原始文本。
    :param image_bytes: (新增) 原始的图片字节流 (用于LLM视觉分析)。
    :return: 包含海报信息的字典。
    """

    DEEPSEEK_API_KEY=os.environ.get("DEEPSEEK_API_KEY")
    api_key = DEEPSEEK_API_KEY
    if not api_key:
        raise ValueError("环境变量 DEEPSEEK_API_KEY 未设置。")

    try:
        # 图片压缩
        print("--- [Real LLM] (V9) 正在压缩图片以适应 Token 限制... ---")
        
        # 1. 从字节解码
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("无法从字节流解码图片 (用于压缩)")

        # 2. 缩放
        height, width = img.shape[:2]
        max_dim = 1024 # 将最长边限制为 1024 像素
        
        if height > max_dim or width > max_dim:
            if height > width:
                new_height = max_dim
                new_width = int(width * (max_dim / height))
            else:
                new_width = max_dim
                new_height = int(height * (max_dim / width))
            
            img_resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            print(f"--- [Real LLM] (V9) 图片已从 {width}x{height} 缩放至 {new_width}x{new_height}")
        else:
            img_resized = img
            print("--- [Real LLM] (V9) 图片尺寸无需缩放。")

        # 3. 重新编码为 JPG (50% 质量)
        is_success, buffer = cv2.imencode(".jpg", img_resized, [cv2.IMWRITE_JPEG_QUALITY, 50])
        if not is_success:
            raise ValueError("无法将缩放后的图片重新编码为 JPG")
        
        compressed_image_bytes = buffer.tobytes()
        print(f"--- [Real LLM] (V9) 图片已压缩。新大小: {len(compressed_image_bytes)} 字节。")
        
        # 4. 使用压缩后的字节
        base64_image = base64.b64encode(compressed_image_bytes).decode('utf-8')
        image_mime_type = "image/jpeg"
        
    except Exception as e:
        print(f"--- [LLM] Error: 图片压缩或 Base64 编码失败: {e} ---")
        raise HTTPException(status_code=500, detail=f"图片处理失败: {e}")

    # 提示词
    prompt = f"""
    你是一个信息提取专家。请结合以下【OCR识别文本】和【海报原图】来提取关键信息，并严格按照JSON格式返回。
    
    【海报原图】提供了视觉上下文，请在【OCR识别文本】不准确或有遗漏时，优先参考【海报原图】进行补充和修正。

    需要提取的字段包括：
    - "title": 活动的完整主题
    - "date": 活动日期 (例如: 2025年10月28日)
    - "time": 活动时间 (例如: 下午 14:30)
    - "location": 活动地点
    - "organizer": 主办方或承办单位
    - "speaker": 主讲人
    - "event_type": 活动类型 (例如: 讲座, 竞赛, 招聘, 社团活动)
    - "target_audience": 面向对象 (例如: 全体师生, 2023级本科生)
    - "contact_info": 联系方式 (例如: 电话, 邮箱, QQ群)
    - "registration_info": 报名信息 (例如: 扫码报名, 报名链接)
    - "summary": 对活动内容的简短总结 (2-3句话)
    
    如果某个字段在文本中找不到对应信息，请将该字段的值设为 "None"。
    请确保你的回答是一个干净、合法、无任何多余解释的JSON对象。

    【OCR识别文本】：
    ---
    {text}
    ---
    """

    try:
        print("--- [Real LLM] (V9) 正在初始化 LangChain... ---")
        
        # 1. 配置DeepSeek模型
        model = ChatOpenAI(
            model_name="deepseek-chat",
            openai_api_key=api_key,
            openai_api_base="https://api.deepseek.com/v1"
        )

        # 2. 构建 CSDN 格式的 content
        content_list = [
            {"type": "text", "text": prompt},
            {"type": "image", "image": {"data": base64_image, "format": image_mime_type.split('/')[-1]}}
        ]
        
        # 3. 构建多模态消息
        message = HumanMessage(
            content=json.dumps(content_list) # (关键) 将列表转为 JSON 字符串
        )
        
        system_message = "你是一个只输出JSON格式的高效多模态信息提取助手。"
        
        print("--- [Real LLM] (V9) 正在向 DeepSeek (LangChain) API 发送请求... ---")
        
        # 4. 调用API
        response = model.invoke([system_message, message])
        
        print("--- [Real LLM] (V9) 已成功收到 API 的响应。 ---")
        
        content_str = response.content
        
        if content_str.strip().startswith("```json"):
            content_str = content_str.strip()[7:-3].strip() 

        structured_info = json.loads(content_str)
        return structured_info

    except Exception as e:
        print(f"--- [Real LLM] (V9) Error: LangChain/API 请求失败: {e} ---")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"--- [Real LLM] 错误响应体: {e.response.text[:500]} ...")
        raise HTTPException(status_code=502, detail=f"调用大语言模型服务失败: {e}")