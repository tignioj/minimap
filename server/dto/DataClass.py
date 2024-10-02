from dataclasses import dataclass, field
from typing import List


@dataclass
class Todo:
    name: str = None
    enable: bool = True
    team_enable: bool = True
    fight_duration: int = 20
    from_index: int = 0
    fight_team: str = ""
    files: List[str] = field(default_factory=list)
    frequency:int = 0
    lastExecutionDate: str= "2024-10-2"

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError("无效的数据格式")
        if 'name' not in data:
            raise ValueError("缺少必要的字段name")
        return cls(**data)


@dataclass
class OneDragon:
    name: str = None
    value: str = None
    checked: bool = False

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError("无效的数据格式")
        if 'name' not in data:
            raise ValueError("缺少必要的字段name")
        return cls(**data)

if __name__ == '__main__':
    # 创建一个Todo实例
    todo = Todo(name="完成作业", files=["文件1.txt", "文件2.txt"])

    # 或者使用from_dict方法
    todo_data = {
        "name": "完成作业",
        "enable": False,
        "fight_duration": 30,
        "fight_team": "团队A",
        "files": ["文件1.txt", "文件2.txt"],
        "frequency": 1,
        "lastExecutionDate": "2024-10-3"
    }
    todo = Todo.from_dict(todo_data)

    print(todo)  # 这将打印出Todo实例的所有字段