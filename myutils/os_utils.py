import win32api
import win32security
import win32con


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


if __name__ == '__main__':
    hibernate_sys()