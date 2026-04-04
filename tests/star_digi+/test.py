import pyautogui, pyperclip, time, random

def send_now(name, msg):
    """立即给指定联系人/群发送一条消息"""
    pyautogui.hotkey('ctrl', 'alt', 'w')   # 唤起微信
    time.sleep(0.5)
    pyautogui.click(250, 40)               # 点搜索框（1920×1080 通用坐标）
    time.sleep(0.2)
    pyperclip.copy(name)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(0.5)
    pyperclip.copy(msg)
    pyautogui.hotkey('ctrl', 'v')
    pyautogui.press('enter')
    print(f"✅ 已发送给【{name}】: {msg}")

if __name__ == "__main__":
    target = "黎国润"          # 要轰炸的联系人/群
    for i in range(1, 101):   # 发 100 条
        text = f"第 {i:03d} 条消息（随机码 {random.randint(1000, 9999)}）"
        send_now(target, text)
        time.sleep(random.uniform(1, 2))   # 随机 1~2 秒，防风控