import requests
import json

# 测试流式接口
def test_stream_api():
    url = "http://127.0.0.1:8000/api/content/generate/stream"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1IiwiZXhwIjoxNzcyNjAzOTAwfQ._GzQ-WUrYxIvIbtDT_Hd9WBNcooOSEG_4yrEQaEqq_0",
        "Origin": "http://localhost:8080",
        "Referer": "http://localhost:8080/"
    }
    data = {
        "prompt": "春日野餐文案",
        "platform": "小红书",
        "title": "春日野餐文案"
    }
    
    print("开始测试流式接口...")
    print("=" * 50)
    
    try:
        # 发送请求
        response = requests.post(url, headers=headers, json=data, stream=True)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 500:
            print("\n500错误响应内容:")
            print(response.text)
        else:
            print("\n流式返回内容:")
            print("-" * 50)
            # 逐行读取流式响应
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    print(decoded_line)
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    test_stream_api()
