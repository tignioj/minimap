# 监听BGI的事件, 这里的WebHook事件要自己修改BGI的代码
# GameTask->AutoFight->AutoFightTask

# 1. 实现通知接口
# public class WebhookNotificationData : INotificationData
# {
#     public NotificationEvent Event { get; set; }
#     public string Message { get; set; }
#     public string Recipient { get; set; }
# }
# 2. 获取通知服务
# private readonly NotificationService _notificationService;
# _notificationService = NotificationService.Instance();  # 获取通知实例

# 3. 发送通知
# await _notificationService.NotifyAllNotifiersAsync(new WebhookNotificationData
# {
#   Event = NotificationEvent.Fight,
#   Message = "开始战斗"
# });
# 在finally处
# await _notificationService.NotifyAllNotifiersAsync(new WebhookNotificationData
# {
#   Event = NotificationEvent.Fight,
#   Message = "战斗结束"
#  });

import time

from flask import Flask, request, jsonify
import requests as rq
class BGIEventHandler(Flask):
    BGI_EVENT_FIGHT = 3

    is_fighting = False
    @staticmethod
    def start_server():
        app.run(port=5003)


app = BGIEventHandler(__name__)
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        # 获取 JSON 数据
        data = request.get_json()
        # 在这里处理传入的数据
        print('Received data:', data)
        if data.get('event') == BGIEventHandler.BGI_EVENT_FIGHT:
            if data.get('message') == '开始战斗':
                BGIEventHandler.is_fighting = True
            elif data.get('message') == '战斗结束':
                BGIEventHandler.is_fighting = False

        # 你可以在这里进行数据处理、存储等操作

        # 返回一个响应
        return jsonify({'status': 'success', 'data': data}), 200


if __name__ == '__main__':
    import threading
    thread = threading.Thread(target=BGIEventHandler.start_server)
    thread.setDaemon(True)
    thread.start()
    start = time.time()
    while time.time() - start < 5:
        time.sleep(1)
        print(BGIEventHandler.is_fighting)
    # BGIEventHandler.shutdown_server()
