def hello_world():
    """增强版函数 - 支持多语言问候"""
    messages = [
        "Hello, World!", 
        "你好，世界！",
        "Hola, Mundo!",
        "Bonjour, le monde!"
    ]
    print("=== 多语言问候 ===")
    for i, message in enumerate(messages, 1):
        print(f"{i}. {message}")
    return messages