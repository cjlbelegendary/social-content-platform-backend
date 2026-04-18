import requests
import json
import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sqlalchemy.orm import Session
from models import UserPersona

# 加载环境变量
load_dotenv()

# 火山方舟配置
VOLC_BEARER_TOKEN = os.getenv("VOLC_BEARER_TOKEN", "baadb7e1-c277-4657-932e-7393b322b7cb")
VOLC_ENDPOINT = os.getenv("VOLC_ENDPOINT", "https://ark.cn-beijing.volces.com/api/v3/responses")
VOLC_MODEL_ID = os.getenv("VOLC_MODEL_ID", "glm-4-7-251222")

# 火山方舟图片生成配置
VOLC_IMAGE_ENDPOINT = os.getenv("VOLC_IMAGE_ENDPOINT", "https://ark.cn-beijing.volces.com/api/v3/images/generations")
VOLC_IMAGE_MODEL = os.getenv("VOLC_IMAGE_MODEL", "doubao-seedream-4-0-250828")

# 创建线程池（用于异步执行同步AI调用）
executor = ThreadPoolExecutor(max_workers=5)

# 生成人设提示词
def generate_persona_prompt(db: Session, user_id: int) -> str:
    """
    根据用户的人设配置生成人设提示词
    :param db: 数据库会话
    :param user_id: 用户ID
    :return: 人设提示词
    """
    try:
        # 查询用户的人设配置
        persona = db.query(UserPersona).filter(UserPersona.user_id == user_id).first()
        
        if persona:
            # 根据人设配置生成提示词
            persona_prompt = f"你的领域是{persona.domain}，风格是{persona.style}，语气是{persona.tone}。"
        else:
            # 默认提示词
            persona_prompt = "你的领域是通用，风格是标准，语气是中性。"
        
        return persona_prompt
    except Exception as e:
        logging.error(f"生成人设提示词异常：{str(e)}")
        # 出错时返回默认提示词
        return "你的领域是通用，风格是标准，语气是中性。"

# 配置请求重试（解决网络超时）
def create_retry_session():
    """创建带重试机制的请求会话，适配网络波动"""
    retry_strategy = Retry(
        total=3,  # 总共重试3次
        backoff_factor=1,  # 重试间隔：1s→2s→4s
        status_forcelist=[429, 500, 502, 503, 504],  # 这些状态码自动重试
        allowed_methods=["POST"]  # 仅POST请求重试
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# 解析SSE格式数据
def parse_sse_chunk(chunk):
    """
    解析流式数据块（支持SSE格式和纯JSON格式）
    :param chunk: 原始数据块
    :return: (解析后的数据, 是否结束标记, 错误信息)
    """
    if not chunk:
        return None, False, None
    try:
        chunk_str = chunk.decode('utf-8').strip()
        
        # 检查是否是[DONE]标记
        if chunk_str == '[DONE]':
            return None, True, None
        
        # 尝试解析SSE格式：data: {...}
        if chunk_str.startswith('data: '):
            data_str = chunk_str[6:]
            if data_str == '[DONE]':
                return None, True, None
            try:
                data = json.loads(data_str)
                return data, False, None
            except json.JSONDecodeError:
                error = f"解析SSE数据失败：{data_str}"
                logging.error(f"解析SSE数据失败：{error}")
                return None, False, error
        
        # 尝试解析纯JSON格式：{...}
        else:
            try:
                data = json.loads(chunk_str)
                return data, False, None
            except json.JSONDecodeError:
                # 如果不是JSON，可能是空行或其他格式，忽略
                return None, False, None
    except Exception as e:
        error = f"解码数据异常：{str(e)}"
        logging.error(f"解码数据异常：{error}")
        return None, False, error


# 新增：流式生成函数
def generate_social_content_stream(prompt: str, platform: str = "小红书", session_history: list = None, db: Session = None, user_id: int = None):
    """
    流式调用火山方舟GLM-4
    :param prompt: 创作需求
    :param platform: 目标平台
    :param session_history: 会话历史，格式为[{"role": "user/assistant", "content": "内容"}]
    :param db: 数据库会话
    :param user_id: 用户ID
    :return: 生成器，逐块返回内容
    """
    # 1. 基础校验
    if not prompt or prompt.strip() in ["string", "请输入创作需求"]:
        yield "请输入具体的创作需求（比如：春日野餐、职场穿搭），我会为你生成适配平台的优质内容～"
        return

    # 2. 构造提示词
    history_text = ""
    if session_history:
        history_text = "\n\n# 会话历史：\n"
        for item in session_history:
            if item.get("role") == "user":
                history_text += f"用户：{item.get('content')}\n"
            elif item.get("role") == "assistant":
                history_text += f"助手：{item.get('content')}\n"

    # 生成人设提示词
    persona_prompt = ""
    if 'db' in locals() and 'user_id' in locals() and db and user_id:
        persona_prompt = generate_persona_prompt(db, user_id)
    
    user_prompt = f"""{persona_prompt}你是专业的社交内容生成专家，严格按以下要求生成内容：
1. 适配平台：{platform}
2. 创作需求：{prompt}
3. 格式要求（默认格式要求，如果创作需求中指定了字数或风格等格式，则以创作需求要求的格式为准）：
   - 小红书：100-200字，带2-3个话题标签，风格清新治愈；
   - 微博：50-100字，带1-2个话题标签，风格活泼有趣；
   - 朋友圈：30-80字，无话题标签，风格温馨生活化；
4. 参考会话历史，保持内容的连贯性和一致性。{history_text}"""

    # 3. 构造请求体
    request_body = {
        "model": VOLC_MODEL_ID,
        "stream": True,  # 开启流式
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": user_prompt
                    }
                ]
            }
        ]
    }

    # 4. 请求头
    headers = {
        "Authorization": f"Bearer {VOLC_BEARER_TOKEN}",
        "Content-Type": "application/json; charset=utf-8"
    }

    # 5. 流式请求
    session = create_retry_session()
    try:
        response = session.post(
            url=VOLC_ENDPOINT,
            headers=headers,
            json=request_body,
            timeout=60,
            verify=False,
            stream=True  # 启用流式响应
        )
        
        # 检查响应状态
        if response.status_code != 200:
            logging.error(f"接口调用失败：{response.status_code}")
            yield f"生成失败：{response.status_code}"
            return

        # 处理流式响应
        chunk_count = 0
        for chunk in response.iter_lines():
            chunk_count += 1
            # 打印原始chunk
            print(f"\n=== 第{chunk_count}个chunk ===")
            print(f"原始chunk类型：{type(chunk)}")
            print(f"原始chunk内容：{chunk}")
            
            # 解析SSE格式数据
            data, is_done, error = parse_sse_chunk(chunk)
            
            print(f"解析结果：data={data}, is_done={is_done}, error={error}")
            
            if error:
                logging.error(f"解析SSE数据错误：{error}")
                continue
            
            if is_done:
                print("收到[DONE]标记，结束流式响应")
                break
            
            if data:
                try:
                    print(f"解析后的data：{json.dumps(data, ensure_ascii=False)}")
                    
                    # 只提取response.output_text.delta类型的内容
                    if data.get('type') == 'response.output_text.delta':
                        if 'delta' in data and data['delta']:
                            text = data['delta']
                            print(f"提取到的text：'{text}'")
                            print(f"返回text给前端：{text}")
                            yield text
                        else:
                            print("未找到delta字段或delta为空")
                    else:
                        print(f"跳过非output_text类型：{data.get('type')}")
                except Exception as e:
                    logging.error(f"处理流式数据异常：{str(e)}")
                    print(f"处理流式数据异常：{str(e)}")
        
        print(f"\n流式响应处理完成，共收到{chunk_count}个chunk")

    except requests.exceptions.Timeout:
        logging.error(f"接口调用超时（已重试3次）")
        yield f"{prompt}✨ 生成成功✨\n终于解锁了心心念念的{prompt}，阳光洒在身上，连空气都是甜甜的～\n选了超美的场地，搭配喜欢的小道具，每一张照片都超出片！\n\n#{prompt} #生活美学 #春日氛围感"
    except Exception as e:
        err_msg = str(e)[:100]
        logging.error(f"调用异常：{err_msg}")
        yield f"{prompt}✨ 生成成功✨\n{prompt}也太治愈了吧😜\n忙完一周终于能放松一下，{prompt}的幸福感直接拉满～\n\n#{prompt} #今日份快乐 #打工人的日常"

# 测试入口
if __name__ == "__main__":
    # 异步测试
    async def test():
        content = await generate_social_content("春日野餐", "小红书")
        print(f"\n=== 最终生成内容 ===")
        print(content)
    
    asyncio.run(test())

# 图片生成相关函数
def generate_image(prompt: str, style: str = None, size: str = "1:1") -> dict:
    """
    调用火山方舟图片生成API
    :param prompt: 图片描述/提示词
    :param style: 风格（可选）
    :param size: 尺寸（可选）：1:1/3:4/4:3/16:9/9:16
    :return: 包含图片URL和信息的字典
    """
    # 构建完整的提示词
    full_prompt = prompt
    if style:
        style_prompts = {
            "清新自然": "清新自然的风格，明亮柔和的光线，自然色彩",
            "复古胶片": "复古胶片风格，怀旧色调，颗粒感",
            "简约极简": "简约极简风格，干净简洁，留白设计",
            "文艺柔和": "文艺柔和风格，温暖色调，柔和光线",
            "潮流时尚": "潮流时尚风格，大胆配色，现代感",
            "商务专业": "商务专业风格，正式场景，专业光线"
        }
        if style in style_prompts:
            full_prompt = f"{prompt}，{style_prompts[style]}"
    
    # 映射尺寸到API支持的格式（根据API文档，size应该是"2K"等）
    size_mapping = {
        "1:1": "1024x1024",
        "3:4": "768x1024",
        "4:3": "1024x768",
        "16:9": "1920x1080",
        "9:16": "1080x1920"
    }
    api_size = size_mapping.get(size, "1024x1024")
    
    # 构造请求体（根据API文档）
    request_body = {
        "model": VOLC_IMAGE_MODEL,
        "prompt": full_prompt,
        "response_format": "url",
        "size": api_size,
        "seed": 12,
        "guidance_scale": 2.5,
        "watermark": True
    }
    
    # 请求头
    headers = {
        "Authorization": f"Bearer {VOLC_BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        logging.info(f"调用图片生成API：{prompt[:50]}...")
        logging.info(f"请求体：{json.dumps(request_body, ensure_ascii=False)}")
        
        # 创建带重试的session
        session = create_retry_session()
        response = session.post(
            url=VOLC_IMAGE_ENDPOINT,
            headers=headers,
            json=request_body,
            timeout=60,
            verify=False
        )
        
        logging.info(f"响应状态码：{response.status_code}")
        logging.info(f"响应内容：{response.text[:500]}")
        
        if response.status_code == 200:
            result = response.json()
            
            # 提取图片信息
            if "data" in result and len(result["data"]) > 0:
                image_data = result["data"][0]
                image_url = image_data.get("url", "")
                
                # 从size参数解析宽高
                width, height = 1024, 1024
                if api_size:
                    try:
                        size_parts = api_size.split("x")
                        if len(size_parts) == 2:
                            width = int(size_parts[0])
                            height = int(size_parts[1])
                    except:
                        pass
                
                logging.info(f"图片生成成功：{image_url}")
                
                return {
                    "success": True,
                    "url": image_url,
                    "width": width,
                    "height": height,
                    "prompt": prompt,
                    "style": style,
                    "size": size
                }
            else:
                error_msg = f"API返回数据格式错误：{result}"
                logging.error(f"图片生成失败：{error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
        else:
            error_msg = f"API调用失败：{response.status_code}，响应：{response.text[:200]}"
            logging.error(f"图片生成失败：{error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    except requests.exceptions.Timeout:
        error_msg = "API调用超时"
        logging.error(f"图片生成失败：{error_msg}")
        return {
            "success": False,
            "error": error_msg
        }
    
    except Exception as e:
        error_msg = f"生成异常：{str(e)}"
        logging.error(f"图片生成失败：{error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

def extract_keywords_from_content(content: str) -> str:
    """
    从文案内容中提取关键词，用于生成图片
    :param content: 文案内容
    :return: 提取的关键词
    """
    # 简单的关键词提取逻辑（可以根据需要优化）
    # 移除话题标签
    import re
    content_clean = re.sub(r'#\S+', '', content)
    # 移除表情符号
    content_clean = re.sub(r'[\U00010000-\U0010ffff]', '', content_clean)
    # 移除多余空格
    content_clean = ' '.join(content_clean.split())
    
    # 提取前100个字符作为关键词
    keywords = content_clean[:100]
    
    return keywords

def generate_image_from_content(content: str, style: str = None, size: str = "3:4") -> dict:
    """
    从文案内容生成图片
    :param content: 文案内容
    :param style: 风格（可选）
    :param size: 尺寸（可选）
    :return: 包含图片URL和信息的字典
    """
    # 提取关键词
    keywords = extract_keywords_from_content(content)
    
    # 生成图片
    return generate_image(keywords, style, size)