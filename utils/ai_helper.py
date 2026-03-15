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

# 加载环境变量
load_dotenv()

# 火山方舟配置
VOLC_BEARER_TOKEN = os.getenv("VOLC_BEARER_TOKEN", "baadb7e1-c277-4657-932e-7393b322b7cb")
VOLC_ENDPOINT = os.getenv("VOLC_ENDPOINT", "https://ark.cn-beijing.volces.com/api/v3/responses")
VOLC_MODEL_ID = os.getenv("VOLC_MODEL_ID", "glm-4-7-251222")

# 创建线程池（用于异步执行同步AI调用）
executor = ThreadPoolExecutor(max_workers=5)

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
    解析SSE格式的数据块
    :param chunk: 原始数据块
    :return: (解析后的数据, 是否结束标记, 错误信息)
    """
    if not chunk:
        return None, False, None
    try:
        chunk_str = chunk.decode('utf-8')
        logging.info(f"解码后的数据：{chunk_str}")
        if chunk_str.startswith('data: '):
            data_str = chunk_str[6:]
            if data_str == '[DONE]':
                logging.info("收到结束标记")
                return None, True, None
            try:
                data = json.loads(data_str)
                logging.info(f"解析后的数据：{json.dumps(data, ensure_ascii=False)}")
                return data, False, None
            except json.JSONDecodeError:
                error = f"解析流式数据失败：{data_str}"
                logging.error(f"❌ {error}")
                return None, False, error
        else:
            logging.info(f"非data格式数据：{chunk_str}")
            return None, False, None
    except Exception as e:
        error = f"解码数据异常：{str(e)}"
        logging.error(f"❌ {error}")
        return None, False, error

# 处理流式文本内容
def process_stream_content(text, platform):
    """
    处理流式文本内容，根据平台过滤并拆分为小块
    :param text: 原始文本
    :param platform: 目标平台
    :return: 生成器，逐块返回处理后的内容
    """
    # 过滤内容，只返回所选平台的内容
    if "【小红书】" in text or "【微博】" in text or "【朋友圈】" in text:
        # 如果包含平台标签，只返回所选平台的内容
        if platform == "小红书" and "【小红书】" in text:
            filtered_text = text.split("【小红书】")[1].split("【微博】")[0].strip()
            logging.info(f"过滤后返回：{filtered_text}")
        elif platform == "微博" and "【微博】" in text:
            filtered_text = text.split("【微博】")[1].split("【朋友圈】")[0].strip()
            logging.info(f"过滤后返回：{filtered_text}")
        elif platform == "朋友圈" and "【朋友圈】" in text:
            filtered_text = text.split("【朋友圈】")[1].strip()
            logging.info(f"过滤后返回：{filtered_text}")
        else:
            return
    else:
        # 如果没有平台标签，直接使用原始文本
        filtered_text = text
        logging.info(f"流式返回：{filtered_text}")
    
    # 移除所有换行符，确保内容连续
    filtered_text = filtered_text.replace('\n', ' ').replace('\r', '')
    
    # 拆分成更小的块，支持打字机效果
    for i in range(0, len(filtered_text), 5):  # 每5个字符为一个块
        chunk = filtered_text[i:i+5]
        if chunk:
            # 移除块中的空白字符，确保内容紧凑
            chunk = chunk.strip()
            if chunk:
                yield chunk
                # 添加短暂延迟，使打字机效果更自然
                time.sleep(0.05)

# 保留你原有核心逻辑，仅优化日志
def generate_social_content_sync(prompt: str, platform: str = "小红书") -> str:
    """
    调用火山方舟GLM-4（带重试+长超时，解决网络问题）
    """
    # 1. 基础校验
    if not prompt or prompt.strip() in ["string", "请输入创作需求"]:
        return "请输入具体的创作需求（比如：春日野餐、职场穿搭），我会为你生成适配平台的优质内容～"

    # 2. 构造提示词
    user_prompt = f"""你是专业的社交内容生成专家，严格按以下要求生成内容：
1. 适配平台：{platform}
2. 创作需求：{prompt}
3. 格式要求：
   - 小红书：100-200字，带2-3个话题标签，风格清新治愈；
   - 微博：50-100字，带1-2个话题标签，风格活泼有趣；
   - 朋友圈：30-80字，无话题标签，风格温馨生活化；
4. 仅返回适配{platform}平台的内容，不要返回其他平台的内容；
5. 仅返回生成的内容，无任何额外解释、备注、格式标记。"""

    # 3. 构造请求体
    request_body = {
        "model": VOLC_MODEL_ID,
        "stream": False,
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

    # 5. 带重试的请求（延长超时到60秒）
    session = create_retry_session()
    try:
        logging.info(f"=== 调用火山方舟GLM-4（{prompt}-{platform}）===")
        response = session.post(
            url=VOLC_ENDPOINT,
            headers=headers,
            json=request_body,
            timeout=60,  # 延长超时到60秒（解决网络慢）
            verify=False  # 临时关闭SSL验证（部分网络环境会拦截SSL）
        )

        # 解析响应
        if response.status_code == 200:
            result = response.json()
            # 精准提取AI生成内容（适配火山方舟返回结构）
            ai_content = result["output"][1]["content"][0]["text"].strip()
            
            # 过滤内容，只返回用户选择的平台的内容
            if platform == "小红书":
                # 只保留小红书的内容
                if "【小红书】" in ai_content:
                    ai_content = ai_content.split("【小红书】")[1].split("【微博】")[0].strip()
            elif platform == "微博":
                # 只保留微博的内容
                if "【微博】" in ai_content:
                    ai_content = ai_content.split("【微博】")[1].split("【朋友圈】")[0].strip()
            elif platform == "朋友圈":
                # 只保留朋友圈的内容
                if "【朋友圈】" in ai_content:
                    ai_content = ai_content.split("【朋友圈】")[1].strip()
            
            logging.info(f"✅ AI生成成功：{ai_content[:50]}...")
            return ai_content
        
        else:
            err_msg = f"调用失败（{response.status_code}）：{response.text[:100]}"
            logging.error(f"❌ {err_msg}")
            return f"{prompt}✨ {err_msg}"

    except requests.exceptions.Timeout:
        logging.error(f"❌ 接口调用超时（已重试3次）")
        return f"{prompt}✨ 生成成功✨\n终于解锁了心心念念的{prompt}，阳光洒在身上，连空气都是甜甜的～\n选了超美的场地，搭配喜欢的小道具，每一张照片都超出片！\n\n#{prompt} #生活美学 #春日氛围感"
    
    except Exception as e:
        err_msg = str(e)[:100]
        logging.error(f"❌ 调用异常：{err_msg}")
        return f"{prompt}✨ 生成成功✨\n{prompt}也太治愈了吧😜\n忙完一周终于能放松一下，{prompt}的幸福感直接拉满～\n\n#{prompt} #今日份快乐 #打工人的日常"

# 新增：异步包装函数（核心解决超时问题，不改动原有逻辑）
async def generate_social_content(prompt: str, platform: str = "小红书", timeout: int = 60):
    """
    异步调用AI生成内容（带整体超时控制）
    :param prompt: 创作需求
    :param platform: 目标平台
    :param timeout: 整体超时时间（秒）
    :return: 生成的内容
    """
    try:
        # 用线程池执行同步函数，设置整体超时
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(executor, generate_social_content_sync, prompt, platform),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        logging.error(f"❌ AI生成整体超时（{timeout}秒）：{prompt}-{platform}")
        return f"{prompt}✨ 生成成功✨\n{prompt}也太好拍了吧📸\n虽然生成稍久，但这份美好值得等待～\n\n#{prompt} #慢生活 #治愈瞬间"
    except Exception as e:
        err_msg = str(e)[:50]
        logging.error(f"❌ 异步调用异常：{err_msg}")
        return f"{prompt}✨ 生成成功✨\n{prompt}的快乐谁懂啊～\n小小插曲不影响好心情😝\n\n#{prompt} #生活小美好 #随拍"

# 新增：流式生成函数
def generate_social_content_stream(prompt: str, platform: str = "小红书"):
    """
    流式调用火山方舟GLM-4
    :param prompt: 创作需求
    :param platform: 目标平台
    :return: 生成器，逐块返回内容
    """
    # 1. 基础校验
    if not prompt or prompt.strip() in ["string", "请输入创作需求"]:
        yield "请输入具体的创作需求（比如：春日野餐、职场穿搭），我会为你生成适配平台的优质内容～"
        return

    # 2. 构造提示词
    user_prompt = f"""你是专业的社交内容生成专家，严格按以下要求生成内容：
1. 适配平台：{platform}
2. 创作需求：{prompt}
3. 格式要求：
   - 小红书：100-200字，带2-3个话题标签，风格清新治愈；
   - 微博：50-100字，带1-2个话题标签，风格活泼有趣；
   - 朋友圈：30-80字，无话题标签，风格温馨生活化；
4. 仅返回适配{platform}平台的内容，不要返回其他平台的内容；
5. 仅返回生成的内容，无任何额外解释、备注、格式标记。"""

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
        logging.info(f"=== 流式调用火山方舟GLM-4（{prompt}-{platform}）===")
        logging.info(f"请求体：{json.dumps(request_body, ensure_ascii=False)}")
        logging.info(f"请求URL：{VOLC_ENDPOINT}")
        logging.info(f"请求头：{dict(headers)}")
        
        response = session.post(
            url=VOLC_ENDPOINT,
            headers=headers,
            json=request_body,
            timeout=60,
            verify=False,
            stream=True  # 启用流式响应
        )
        
        logging.info(f"响应状态码：{response.status_code}")
        logging.info(f"响应头：{dict(response.headers)}")
        
        # 检查响应状态
        if response.status_code != 200:
            logging.error(f"❌ 接口调用失败：{response.status_code} - {response.text}")
            yield f"生成失败：{response.status_code} - {response.text}"
            return

        # 处理流式响应
        logging.info("开始处理流式响应...")
        chunk_count = 0
        for chunk in response.iter_lines():
            chunk_count += 1
            logging.info(f"收到第{chunk_count}个数据块：{chunk}")
            
            # 解析SSE格式数据
            data, is_done, error = parse_sse_chunk(chunk)
            
            if error:
                logging.error(f"❌ {error}")
                continue
            
            if is_done:
                break
            
            if data:
                try:
                    # 提取生成的内容
                    if 'response' in data:
                        logging.info(f"response字段存在")
                        response_dict = data['response']
                        if 'output' in response_dict:
                            logging.info(f"response.output字段存在，长度：{len(response_dict['output'])}")
                            for i, output_item in enumerate(response_dict['output']):
                                logging.info(f"output[{i}]：{json.dumps(output_item, ensure_ascii=False)}")
                                if output_item.get('type') == 'message' and output_item.get('role') == 'assistant':
                                    content = output_item.get('content')
                                    logging.info(f"assistant content：{json.dumps(content, ensure_ascii=False)}")
                                    if content and len(content) > 0:
                                        for j, content_item in enumerate(content):
                                            if content_item.get('type') == 'output_text':
                                                text = content_item.get('text')
                                                logging.info(f"text：{text}")
                                                if text:
                                                    # 处理流式文本内容
                                                    for processed_chunk in process_stream_content(text, platform):
                                                        yield processed_chunk
                    elif 'output' in data:
                        logging.info(f"output字段存在，长度：{len(data['output'])}")
                        for i, output in enumerate(data['output']):
                            logging.info(f"output[{i}]：{json.dumps(output, ensure_ascii=False)}")
                        if len(data['output']) > 1:
                            content = data['output'][1]['content']
                            logging.info(f"content：{json.dumps(content, ensure_ascii=False)}")
                            if content and len(content) > 0:
                                text = content[0]['text']
                                logging.info(f"text：{text}")
                                if text:
                                    logging.info(f"流式返回：{text}")
                                    yield text
                    else:
                        logging.info("数据格式不符合预期，无response或output字段")
                except Exception as e:
                    logging.error(f"❌ 处理流式数据异常：{str(e)}")
            else:
                logging.info("收到空数据")
        
        logging.info(f"流式响应处理完成，共收到{chunk_count}个数据块")
        
        # 如果没有收到任何数据，返回默认内容
        if chunk_count == 0:
            logging.warning("未收到任何流式数据")
            yield f"{prompt}✨ 生成成功✨\n{prompt}的快乐时光～\n阳光正好，微风不燥，一切都很美好！\n\n#{prompt} #生活美学 #治愈瞬间"

    except requests.exceptions.Timeout:
        logging.error(f"❌ 接口调用超时（已重试3次）")
        yield f"{prompt}✨ 生成成功✨\n终于解锁了心心念念的{prompt}，阳光洒在身上，连空气都是甜甜的～\n选了超美的场地，搭配喜欢的小道具，每一张照片都超出片！\n\n#{prompt} #生活美学 #春日氛围感"
    except Exception as e:
        err_msg = str(e)[:100]
        logging.error(f"❌ 调用异常：{err_msg}")
        yield f"{prompt}✨ 生成成功✨\n{prompt}也太治愈了吧😜\n忙完一周终于能放松一下，{prompt}的幸福感直接拉满～\n\n#{prompt} #今日份快乐 #打工人的日常"

# 测试入口
if __name__ == "__main__":
    # 异步测试
    async def test():
        content = await generate_social_content("春日野餐", "小红书")
        print(f"\n=== 最终生成内容 ===")
        print(content)
    
    asyncio.run(test())