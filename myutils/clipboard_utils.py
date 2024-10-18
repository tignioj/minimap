import time

import win32clipboard
import win32con


def copy_string(text):

    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()


def paste_text():
    import win32clipboard, win32con, win32api
    # 打开剪贴板
    win32clipboard.OpenClipboard()

    try:
        # 获取剪贴板中的数据
        data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
    except:
        # 如果获取失败，返回空字符串
        data = ''
    finally:
        # 关闭剪贴板
        win32clipboard.CloseClipboard()

    # 模拟按下 Ctrl+V
    win32api.keybd_event(0x11, 0, 0, 0)  # Ctrl键按下
    win32api.keybd_event(0x56, 0, 0, 0)  # V键按下
    win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)  # V键释放
    win32api.keybd_event(0x11, 0, win32con.KEYEVENTF_KEYUP, 0)  # Ctrl键释放

    return data

def clean_clipboard():
    # 清空剪贴板
    if clean_clipboard:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()  # 清空剪贴板
        win32clipboard.CloseClipboard()

if __name__ == '__main__':
    copy_string("123")
    paste_text()
    # time.sleep(2)
    clean_clipboard()


