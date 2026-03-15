import requests
import json

# 基础URL
BASE_URL = "http://127.0.0.1:8000/api"

# 注册用户
def register_user():
    url = f"{BASE_URL}/user/register"
    headers = {"Content-Type": "application/json"}
    data = {
        "username": "testuser",
        "password": "123456"
    }
    
    response = requests.post(url, headers=headers, json=data)
    print("注册用户:")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()

# 登录获取token
def login_user():
    url = f"{BASE_URL}/user/login"
    headers = {"Content-Type": "application/json"}
    data = {
        "username": "testuser",
        "password": "123456"
    }
    
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    print("登录用户:")
    print(f"状态码: {response.status_code}")
    print(f"响应: {result}")
    print()
    
    if result.get("code") == 200:
        return result.get("access_token")
    return None

# 测试流式接口
def test_stream(token):
    url = f"{BASE_URL}/content/generate/stream"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = {
        "prompt": "春日野餐",
        "platform": "小红书"
    }
    
    print("测试流式接口...")
    print("=" * 50)
    
    # 发送请求并处理流式响应
    response = requests.post(url, headers=headers, json=data, stream=True)
    
    print(f"响应状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    print("\n流式返回内容:")
    print("-" * 50)
    
    try:
        # 逐行读取流式响应
        print("开始读取流式响应...")
        for i, line in enumerate(response.iter_lines()):
            print(f"第{i+1}行: {line}")
            if line:
                # 解码并打印
                decoded_line = line.decode('utf-8')
                print(f"解码后: {decoded_line}")
        print("流式响应结束")
    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        response.close()

if __name__ == "__main__":
    # 注册用户（如果不存在）
    register_user()
    
    # 登录获取token
    token = login_user()
    
    if token:
        # 测试流式接口
        test_stream(token)
    else:
        print("登录失败，无法测试流式接口")
