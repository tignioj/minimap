import time

from myutils.configutils import DomainConfig
from datetime import datetime

SOCKET_EVENT_DOMAIN_START = 'socket_event_domain_start'
SOCKET_EVENT_DOMAIN_UPDATE = 'socket_event_domain_update'
SOCKET_EVENT_DOMAIN_END = 'socket_event_domain_end'
SOCKET_EVENT_DOMAIN_EXCEPTION = 'socket_event_domain_exception'
from controller.DomainController import DomainController
from mylogger.MyLogger3 import MyLogger
import threading

logger = MyLogger('domain_service')


class DomainService:
    domain_runner_thread = None
    __lock = threading.Lock()

    @staticmethod
    def get_domain_list():
        return DomainController.get_domain_list()

    @staticmethod
    def run_domain_week_plan(emit=lambda val1, val2: logger.debug(f'{val1}:{val2}')):
        #  从配置中查找今日要运行的秘境
        plan = DomainConfig.get(DomainConfig.KEY_DOMAIN_WEEK_PLAN)
        # 计算几天是星期几
        # 获取今天的日期
        today = datetime.today()
        # 获取星期几，0表示星期一，6表示星期日
        weekday_index = today.weekday()
        weekday_text = ['一', '二', '三', '四', '五', '六', '日']
        emit(SOCKET_EVENT_DOMAIN_UPDATE, f'今天是星期{weekday_text[weekday_index]}')
        today_domain = plan[weekday_index]
        if today_domain is None or len(today_domain) == 0:
            logger.debug("今天没有秘境计划")
            emit(SOCKET_EVENT_DOMAIN_UPDATE, f'今天没有秘境计划')
            return
        emit(SOCKET_EVENT_DOMAIN_UPDATE, f'今天的计划是{today_domain}')

        # 查询队伍
        domain_team_mapper = DomainConfig.get(DomainConfig.KEY_DOMAIN_TEAM_MAPPER)
        fight_team = domain_team_mapper.get(today_domain)
        if fight_team is None or len(fight_team) == 0:
            emit(SOCKET_EVENT_DOMAIN_UPDATE, f'秘境{today_domain}, 没有指定队伍，使用默认队伍')
        emit(SOCKET_EVENT_DOMAIN_UPDATE, f'秘境{today_domain}, 指定队伍为{fight_team}')

        # 查找最长执行时间
        timeout = DomainConfig.get(DomainConfig.KEY_DOMAIN_LOOP_TIMEOUT, 20, min_val=1, max_val=600)
        emit(SOCKET_EVENT_DOMAIN_UPDATE, f'秘境限制之执行最长时间为{timeout}分钟')

        emit(SOCKET_EVENT_DOMAIN_UPDATE, f'准备执行秘境')
        try:
            DomainService.run_domain(domain_name=today_domain, fight_team=fight_team, timeout=timeout, emit=emit)
        except Exception as e:
            emit(SOCKET_EVENT_DOMAIN_EXCEPTION, str(e.args))

    @staticmethod
    def run_domain(domain_name=None, fight_team=None, timeout=None,
                   emit=lambda val1, val2: logger.debug(f'{val1}:{val2}')):
        # socket的emit方法需要在flask运行时赋值，否则就是普通的log方法

        with DomainService.__lock:
            if DomainService.domain_runner_thread is not None:
                if DomainService.domain_runner_thread.is_alive():
                    raise Exception("已经有秘境正在执行中，不要重复执行")

            # 让控制器可以执行
            from controller.BaseController import BaseController
            BaseController.stop_listen = False

            emit(SOCKET_EVENT_DOMAIN_START, f'开始执行{domain_name},队伍为{fight_team}, 时长:{timeout}')

            def hook_exception(domain_name, fight_team, timeout):
                try: DomainController.one_key_run_domain(domain_name, fight_team, timeout)
                except Exception as e: emit(SOCKET_EVENT_DOMAIN_EXCEPTION, str(e.args))

            DomainService.domain_runner_thread = threading.Thread(
                target=hook_exception, args=(domain_name, fight_team, timeout,))
            DomainService.domain_runner_thread.start()

    @staticmethod
    def stop_domain(emit=lambda val1, val2: logger.debug(f'{val1}:{val2}')):
        from controller.BaseController import BaseController
        BaseController.stop_listen = True
        if DomainService.domain_runner_thread is not None and DomainService.domain_runner_thread.is_alive():
            emit(SOCKET_EVENT_DOMAIN_UPDATE, "等待秘境线程结束")
            DomainService.domain_runner_thread.join()
            emit(SOCKET_EVENT_DOMAIN_END, "秘境线程已结束")
            DomainService.domain_runner_thread = None
        else:
            emit(SOCKET_EVENT_DOMAIN_END, "没有秘境执行，无需停止")

    @staticmethod
    def get_domain_config():
        domain_week_plain = DomainConfig.get(DomainConfig.KEY_DOMAIN_WEEK_PLAN, default=['', '', '', '', '', '', ''])
        domain_loop_timeout = DomainConfig.get(DomainConfig.KEY_DOMAIN_LOOP_TIMEOUT, default=20, min_val=1, max_val=600)
        domain_team_mapper = DomainConfig.get(DomainConfig.KEY_DOMAIN_TEAM_MAPPER, default=dict())
        data = {
            'domain_week_plain': domain_week_plain,
            'domain_loop_timeout': domain_loop_timeout,
            'domain_team_mapper': domain_team_mapper
        }
        return data

    @staticmethod
    def set_domain_config(data):
        wp = data.get('domain_week_plain', [])
        timeout = data.get('domain_loop_timeout', 20)
        domain_team_mapper = data.get('domain_team_mapper', dict())
        if wp is None or timeout is None: raise Exception("秘境配置中存在空值")
        if len(wp) != 7: raise Exception("秘境周计划数组长度必须为7")

        if domain_team_mapper is None: domain_team_mapper = {}

        timeout = int(timeout)
        if timeout < 1: timeout = 1
        if timeout > 600: timeout = 600

        DomainConfig.set(DomainConfig.KEY_DOMAIN_WEEK_PLAN, wp)
        DomainConfig.set(DomainConfig.KEY_DOMAIN_LOOP_TIMEOUT, timeout)
        DomainConfig.set(DomainConfig.KEY_DOMAIN_TEAM_MAPPER, domain_team_mapper)
        DomainConfig.save_config()


if __name__ == '__main__':
    # name = '虹灵的净土'
    name = '罪祸的终末'
    # fight_team = '纳西妲_芙宁娜_钟离_那维莱特_(草龙芙中).txt'
    # fight_team = '那维莱特_莱依拉_迪希雅_行秋_(龙莱迪行).txt'
    fight_team = '芙宁娜_行秋_莱依拉_流浪者_(芙行莱流).txt'
    # DomainService.run_domain(name, fight_team)
    # time.sleep(10)
    # DomainService.stop_domain()
    DomainService.run_domain_week_plan()
