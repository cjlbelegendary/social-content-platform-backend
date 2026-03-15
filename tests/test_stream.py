import requests
import json

# 测试流式接口
def test_stream():
    url = "http://127.0.0.1:8000/api/content/generate/stream"
    headers = {"Content-Type": "application/json"}
    data = {
        "prompt": "春日野餐",
        "platform": "小红书"
    }
    
    print("开始测试流式接口...")
    print("=" * 50)
    
    # 发送请求并处理流式响应
    response = requests.post(url, headers=headers, json=data, stream=True)
    
    print(f"响应状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    print("\n流式返回内容:")
    print("-" * 50)
    
    try:
        # 逐行读取流式响应
        for line in response.iter_lines():
            if line:
                # 解码并打印
                decoded_line = line.decode('utf-8')
                print(decoded_line)
    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        response.close()

if __name__ == "__main__":
    test_stream()
