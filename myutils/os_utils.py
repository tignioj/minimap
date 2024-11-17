import win32api
import win32security
import win32con
import win32gui
import ctypes
import win32process


# 常量定义
WM_INPUTLANGCHANGEREQUEST = 0x0050  # 消息编号
KLF_ACTIVATE = 0x00000001  # 激活输入法
HWND_BROADCAST = 0xFFFF  # 广播给所有窗口
LANG_ENGLISH = "00000409"  # 英文输入法标识符（美国英语）

# 启用 SeShutdownPrivilege 权限
def enable_privilege(privilege_str):
    # 获取当前进程的令牌
    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(),
                                           win32security.TOKEN_ADJUST_PRIVILEGES | win32security.TOKEN_QUERY)

    # 查询指定权限的LUID
    privilege_id = win32security.LookupPrivilegeValue(None, privilege_str)

    # 启用该权限
    privileges = [(privilege_id, win32security.SE_PRIVILEGE_ENABLED)]
    win32security.AdjustTokenPrivileges(token, False, privileges)

def switch_input_language(language_code):
    """
    切换输入法到指定语言。
    :param language_code: 输入法的语言标识符（如 "00000409" 表示美国英语）
    """
    # 加载指定语言的输入法
    hkl = ctypes.windll.user32.LoadKeyboardLayoutW(language_code, KLF_ACTIVATE)
    if not hkl:
        raise RuntimeError(f"Failed to load keyboard layout: {language_code}")

    # 广播消息通知所有窗口切换输入法
    ctypes.windll.user32.SendMessageW(
        HWND_BROADCAST,
        WM_INPUTLANGCHANGEREQUEST,
        0,
        hkl
    )
    print(f"Switched to input language: {language_code}")


def sleep_sys():
    # 启用 SeShutdownPrivilege 权限
    enable_privilege(win32security.SE_SHUTDOWN_NAME)

    # 执行系统休眠
    win32api.SetSystemPowerState(True, False)

def hibernate_sys():
    """
    TODO: 没效果, 似乎和系统策略有关
    :return:
    """
    import ctypes
    # 调用 SetSuspendState 函数
    ctypes.windll.powrprof.SetSuspendState(Hibernate=True, ForceCritical=False, DisableWakeEvent=False)

def shutdown_sys():
    # 启用关机所需的权限
    enable_privilege(win32security.SE_SHUTDOWN_NAME)

    # 调用系统关机
    win32api.ExitWindowsEx(win32con.EWX_SHUTDOWN | win32con.EWX_FORCE, 0)

def find_window_by_name(window_name):
    # 查找窗口句柄
    hwnd = win32gui.FindWindow(None, window_name)
    if hwnd == 0:
        print(f"Window with name '{window_name}' not found.")
        return None
    return hwnd

def kill_process_by_hwnd(hwnd):
    try:
        # 获取窗口所属的进程ID
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        # 打开进程
        handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE, 0, pid)
        # 终止进程
        win32api.TerminateProcess(handle, 0)
        # 关闭进程句柄
        win32api.CloseHandle(handle)
        print(f"Process with window handle {hwnd} has been terminated.")
    except Exception as e:
        print(f"Failed to terminate process with window handle {hwnd}: {e}")

def kill_game():
    from myutils.configutils import WindowsConfig
    window_name = WindowsConfig.get(WindowsConfig.KEY_WINDOW_NAME, '原神')
    hwnd = find_window_by_name(window_name=window_name)
    if hwnd is None:
        raise Exception(f'未找到窗口:{window_name}, 无法关闭游戏')
    kill_process_by_hwnd(hwnd)


if __name__ == '__main__':
    hibernate_sys()