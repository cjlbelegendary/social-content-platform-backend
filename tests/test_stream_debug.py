import requests
import json
import time

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
    print("=" * 70)
    print(f"请求URL: {url}")
    print(f"请求头: {json.dumps(headers, indent=2, ensure_ascii=False)}")
    print(f"请求数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
    print("=" * 70)
    
    try:
        # 发送请求
        print("发送请求...")
        start_time = time.time()
        response = requests.post(url, headers=headers, json=data, stream=True)
        end_time = time.time()
        print(f"请求耗时: {end_time - start_time:.2f}秒")
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {json.dumps(dict(response.headers), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 500:
            print("\n500错误响应内容:")
            print(response.text)
        else:
            print("\n流式返回内容:")
            print("-" * 70)
            # 逐行读取流式响应
            line_count = 0
            for line in response.iter_lines():
                line_count += 1
                if line:
                    decoded_line = line.decode('utf-8')
                    print(f"第{line_count}行: {decoded_line}")
                else:
                    print(f"第{line_count}行: (空行)")
            print("-" * 70)
            print(f"共收到{line_count}行数据")
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_stream_api()
