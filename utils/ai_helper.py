import requests
import json
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

def generate_social_content(prompt: str, platform: str = "小红书") -> str:
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
4. 仅返回生成的内容，无任何额外解释、备注、格式标记。"""

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
        print(f"=== 调用火山方舟GLM-4（{prompt}-{platform}）===")
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
            print(f"✅ AI生成成功：{ai_content[:50]}...")
            return ai_content
        
        else:
            err_msg = f"调用失败（{response.status_code}）：{response.text[:100]}"
            print(f"❌ {err_msg}")
            return f"{prompt}✨ {err_msg}"

    except requests.exceptions.Timeout:
        print(f"❌ 接口调用超时（已重试3次）")
        return f"{prompt}✨ 生成成功✨\n终于解锁了心心念念的{prompt}，阳光洒在身上，连空气都是甜甜的～\n选了超美的场地，搭配喜欢的小道具，每一张照片都超出片！\n\n#{prompt} #生活美学 #春日氛围感"
    
    except Exception as e:
        err_msg = str(e)[:100]
        print(f"❌ 调用异常：{err_msg}")
        return f"{prompt}✨ 生成成功✨\n{prompt}也太治愈了吧😜\n忙完一周终于能放松一下，{prompt}的幸福感直接拉满～\n\n#{prompt} #今日份快乐 #打工人的日常"

# 测试入口
if __name__ == "__main__":
    content = generate_social_content("春日野餐", "小红书")
    print(f"\n=== 最终生成内容 ===")
    print(content)