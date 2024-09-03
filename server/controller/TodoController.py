from flask import Blueprint, jsonify, request
from threading import Thread
import os

from server.controller.ServerBaseController import ServerBaseController

# 创建一个蓝图
todo_bp = Blueprint('todo', __name__)
from server.service.TodoService import TodoService, TodoExecuteException

class TodoController(ServerBaseController):
    @staticmethod
    @todo_bp.route('/todo/get')
    def todo_get():
        try:
            data = TodoService.get_all_todos()
            return TodoController.success(data=data)
        except Exception as e:
            return TodoController.error(message=e.args)

    @staticmethod
    @todo_bp.post('/todo/save')
    def todo_save():
        if TodoService.save_todo(request.get_json()):
            return TodoController.success('保存成功')
        else:
            return TodoController.error('保存失败')

    @staticmethod
    @todo_bp.post('/todo/run')
    def todo_run():
        todo_json = request.get_json()
        try:
            TodoService.todo_run(todo_json)
            return TodoController.success(message='成功执行')
        except TodoExecuteException as e:
            return TodoController.error(e.args)

    @staticmethod
    @todo_bp.get('/todo/stop')
    def todo_stop():
        try:
            TodoService.todo_stop()
            return TodoController.success(message='停止执行清单')
        except TodoExecuteException as e:
            return TodoController.error(message=e.args)

