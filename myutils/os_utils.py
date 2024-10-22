import win32api
import win32security
import win32con
import win32gui
import win32process


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