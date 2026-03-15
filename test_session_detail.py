import requests
import json

# 测试基础URL
BASE_URL = "http://localhost:8000"

# 测试用户登录
def test_login():
    """测试用户登录"""
    login_url = f"{BASE_URL}/user/login"
    login_data = {
        "username": "test",
        "password": "123456"
    }
    response = requests.post(login_url, json=login_data)
    print("登录响应:", response.json())
    return response.json().get("access_token")

# 测试生成内容（创建新会话）
def test_generate_content(token):
    """测试生成内容，创建新会话"""
    generate_url = f"{BASE_URL}/content/generate"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    generate_data = {
        "prompt": "春日野餐",
        "platform": "小红书",
        "title": "春日野餐计划"
    }
    response = requests.post(generate_url, json=generate_data, headers=headers)
    print("生成内容响应:", response.json())
    return response.json().get("content", {}).get("session_id")

# 测试向已有会话添加内容
def test_add_to_session(token, session_id):
    """测试向已有会话添加内容"""
    generate_url = f"{BASE_URL}/content/generate"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    generate_data = {
        "prompt": "野餐必备物品",
        "platform": "小红书",
        "title": "野餐物品清单",
        "session_id": session_id
    }
    response = requests.post(generate_url, json=generate_data, headers=headers)
    print("向会话添加内容响应:", response.json())

# 测试获取会话列表（只返回基本信息）
def test_get_session_list(token):
    """测试获取会话列表"""
    list_url = f"{BASE_URL}/content/list"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(list_url, headers=headers)
    print("会话列表响应:", json.dumps(response.json(), ensure_ascii=False, indent=2))
    return response.json().get("session_list", [])

# 测试获取会话详情
def test_get_session_detail(token, session_id):
    """测试获取会话详情"""
    detail_url = f"{BASE_URL}/content/session/{session_id}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(detail_url, headers=headers)
    print("会话详情响应:", json.dumps(response.json(), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    print("=== 测试会话管理功能 ===")
    # 登录获取token
    token = test_login()
    if token:
        # 生成内容，创建新会话
        session_id = test_generate_content(token)
        if session_id:
            # 向已有会话添加内容
            test_add_to_session(token, session_id)
            # 获取会话列表
            sessions = test_get_session_list(token)
            # 获取会话详情
            test_get_session_detail(token, session_id)
    print("=== 测试完成 ===")
