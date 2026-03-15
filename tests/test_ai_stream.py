import logging
from utils.ai_helper import generate_social_content_stream

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 直接测试流式生成函数
def test_ai_stream():
    print("开始测试generate_social_content_stream函数...")
    print("=" * 50)
    
    # 调用流式生成函数
    print("创建生成器...")
    generator = generate_social_content_stream("春日野餐", "小红书")
    print(f"生成器类型：{type(generator)}")
    
    print("调用成功，开始获取内容...")
    print("-" * 50)
    
    try:
        # 逐块获取内容
        print("开始迭代生成器...")
        chunk_count = 0
        for i, chunk in enumerate(generator):
            chunk_count += 1
            print(f"第{i+1}块内容：{chunk}")
        print(f"-" * 50)
        print(f"测试完成，共获取{chunk_count}块内容")
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ai_stream()
