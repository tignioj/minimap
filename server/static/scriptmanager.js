// 清单管理
// 新建清单

/** @type {Map<string, {enable: boolean; files: Set<string>}>} */
const todoMap = new Map()
const todoSelect = document.getElementById("todoSelect")
const todoRunButton = document.getElementById('runListBtn')

let todoRunning = false
function setTodoRunning(bool) {
    todoRunning = bool
    if (todoRunning) {
        todoRunButton.innerText = "停止执行"
    } else {
        todoRunButton.innerText = "执行清单"
    }
}

document.addEventListener("DOMContentLoaded", function() {
    const socket = io(socketURL);
    socket.on('connect', function() {
        // drawMap(0,0)
        console.log('WebSocket connection established');
    });
    socket.on('disconnect', function() {
        errorMsg('已断开服务器')
        console.log('WebSocket connection closed');
    });
    socket.on('playback_event', function (data) {
        if (data && data.result)  {
            info(data.msg)
            if (data.msg === "结束执行清单了") {
                setTodoRunning(false)
            }
        }
        else errorMsg(data.msg)
    })
});




fetch(todoGetURL).then(res => {
    // 如果是net::ERR_CONNECTION_REFUSED网络异常，则不会走这里
    if(!res.ok) {
        throw new Error("网络异常");
    }
    return res.json()
}).then(data=> {
    if(data.success) {
        /** @type {Map<string, {enable: boolean; files: Set<string>}>} */
        const jsonDict = data.data
        Object.keys(jsonDict).forEach(key => {
            console.log(`Key: ${key}, Value: ${jsonDict[key]}`);
            const set = new Set()
            const todo_item = jsonDict[key]
            const files = todo_item.files
            files.forEach(fileName=> {
                set.add(fileName)
            })
            const item = {
                enable: todo_item.enable,
                files: set
            }
            todoMap.set(key, item)
            renderToDoMap()
        });
        console.log(todoMap)
    } else {
        errorMsg('获取失败:' + data.data)
    }
}).catch(err => errorMsg(err));

const msgElement = document.getElementById('msg')
function info(text) {
    msgElement.classList.remove('error-msg')
    msgElement.innerText = text;
    console.log(text)
}
function errorMsg(text) {
    console.log('异常:', text)
    msgElement.innerText = text;
    msgElement.classList.add('error-msg')

}
function isUndefinedNullOrEmpty(value) {
    return value === undefined || value === null || value === "";
}
function renderToDoMap() {
    const listContainer = document.getElementById('listContainer')

    // 保存当前下拉框状态, 不使用index的原因是防止清单删除时候，index不对应
    const todoSelectValue = todoSelect.value

    // TODO: 保存展开状态
    const itemTodoList = document.querySelectorAll(".item-todo-list")
    const openStatusDict = {}
    itemTodoList.forEach(item => {
        const itemName =  item.parentElement.querySelector('.list-item-checkbox').value
        openStatusDict[itemName] = item.style.display
    })
    console.log(openStatusDict)

    todoSelect.innerHTML = ''
    listContainer.innerHTML = ''


    for (const [key, value] of todoMap) {
        // console.log(`${key}: ${value}`);
        const folderName = key
        const item = value

        const filesName = item.files
        const enable = item.enable

        const listItem = document.createElement('li');
        const checkbox = document.createElement("input")
        checkbox.type = "checkbox"
        checkbox.classList.add("list-item-checkbox")
        checkbox.value = folderName
        checkbox.checked = enable

        checkbox.addEventListener('change', event=> {
            todoMap.get(folderName).enable = checkbox.checked
        })
        const showListButton = document.createElement("button");
        const openStatus = openStatusDict[folderName]
        showListButton.innerText = openStatus !== "block" ? "展示清单" : "收起清单"
        showListButton.classList.add("showListBtn")
        showListButton.addEventListener('click', event=> {
            if (showListButton.innerText === "展示清单") {
                showListButton.innerText = "收起清单"
                ulElement.style.display = "block"
            }else {
                showListButton.innerText = "展示清单"
                ulElement.style.display = "none"
            }
        })
        // 如果这个文件夹的复选框之前是勾选状态，则重新勾选
        listItem.appendChild(checkbox)
        listItem.appendChild(document.createTextNode(folderName))
        listItem.appendChild(showListButton)

        const ulElement = document.createElement('ul')
        ulElement.style.display = openStatus === "block"? "block":"none"
        ulElement.classList.add("item-todo-list")
        if (folderName=== todoSelectValue) {
            todoSelect.innerHTML += `<option value="${folderName}" selected>${folderName}</option>`
        } else {
            todoSelect.innerHTML += `<option value="${folderName}">${folderName}</option>`
        }

        filesName.forEach(fileName => {
            // 左边栏
            const fileItem = document.createElement('li');
            const span = document.createElement('span')
            span.innerText = fileName
            const removeBtn = document.createElement('button');
            removeBtn.innerText = "移除"
            // removeBtn.classList.add("removeFieBtn")
            removeBtn.addEventListener('click', ()=> {
                const item = todoMap.get(folderName)
                item.files.delete(fileName)
                console.log(todoMap)
                ulElement.removeChild(fileItem)
            });

            const editBtn = document.createElement('button')
            editBtn.innerText = '编辑'
            editBtn.addEventListener('click', ()=> {
                editFile(fileName)
            })
            fileItem.appendChild(span);
            fileItem.appendChild(editBtn)
            fileItem.appendChild(removeBtn)
            ulElement.appendChild(fileItem);
        })
        listItem.appendChild(ulElement)
        listContainer.appendChild(listItem);
    }
}

// 新建清单
document.getElementById('createListBtn').addEventListener('click', function() {
    const listName = prompt('请输入清单名称:');
    const item = todoMap.get(listName)
    if (item) {
        errorMsg(`已经存在同名称的清单${listName}`)
        return;
    }
    if (listName) {
        // const listItem = document.createElement('li');
        // listItem.innerHTML =
        //     `<input type="checkbox" class="list-item-checkbox" value="${listName}"> ${listName} <button class="showListBtn">展示清单</button>`;
        // document.getElementById('listContainer').appendChild(listItem);

        todoMap.set(listName, {enable: true, files: new Set()});
        renderToDoMap()
        info(`创建成功${listName}`)
    }
});

// 删除清单
document.getElementById('deleteListBtn').addEventListener('click', function() {
    const checkedLists = document.querySelectorAll('.list-item-checkbox:checked');
    if (checkedLists.length < 1) return;
    const ok = confirm("确认删除？")
    if (!ok) {
        info("取消删除")
        return
    }
    info("确认删除")
    checkedLists.forEach(item => {
        item.parentElement.remove()
        todoMap.delete(item.value)
    });
});

function getSerializableMap() {
    return Object.fromEntries(
        Array.from(todoMap.entries()).map(([key, value]) => [
            key,
            { ...value, files: Array.from(value.files) }
        ])
    )
}

document.getElementById('saveListBtn').addEventListener('click', function() {

// 序列化为 JSON 字符串
    const obj = getSerializableMap()
    const jsonString = JSON.stringify(obj);

    fetch(todoSaveURL, {
        method: 'POST', // 请求方法
        headers: {
            'Content-Type': 'application/json' // 指定发送的数据格式为 JSON
        },
        body: jsonString // 将 JavaScript 对象转换为 JSON 字符串
    })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok ' + response.statusText);
            return response.json(); // 解析响应为 JSON
        })
        .then(data => {
            if (data.success === true) {
                info("保存清单成功")
            } else {
                errorMsg(data.data)
            }
        })
        .catch(error => {
            console.error('Error:', error); // 处理错误
            errorMsg(error)
        });
})

function runTodo() {
    const jsonString = JSON.stringify(getSerializableMap())
    console.log(getSerializableMap())
    setTodoRunning(true)
    fetch(todoRunURL, {
        method: 'POST', // 请求方法
        headers: {
            'Content-Type': 'application/json' // 指定发送的数据格式为 JSON
        },
        body: jsonString // 将 JavaScript 对象转换为 JSON 字符串
    })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok ' + response.statusText);
            return response.json(); // 解析响应为 JSON
        })
        .then(data => {
            if (data.success === true) {
                // info(data.data)
            } else {
                errorMsg(data.data)
            }
        })
        .catch(error => {
            console.error('Error:', error); // 处理错误
            errorMsg(error)
        });
}
function stopTodo() {
    console.log(getSerializableMap())
    setTodoRunning(true)
    fetch(todoStopURL) .then(response => {
            if (!response.ok) throw new Error('Network response was not ok ' + response.statusText);
            return response.json(); // 解析响应为 JSON
    })
    .then(data => {
            if (data.success === true) {
                info(data.data)
                setTodoRunning(false)
            } else {
                errorMsg(data.data)
            }
        })
        .catch(error => {
            console.error('Error:', error); // 处理错误
            errorMsg(error)
    });
    setTodoRunning(false)
}

todoRunButton.addEventListener('click', ()=> {
    if(todoRunning) {
        stopTodo()
    } else {
        runTodo()
    }
})


//======================== 文件管理
// 假设有一个预先定义好的文件结构
// const fileStructure = {
//     "Folder1": ["file1.txt", "file2.txt"],
//     "Folder2": ["file3.txt", "file4.txt"],
//     "Folder3": ["file5.txt", "file6.txt"]
// };
let fileStructure = {}

// 展示文件树
function displayFileTree(structure, container) {
    for (let folderName in structure) {
        const folder = document.createElement('div');
        const toggleBtn = `<button class="toggleFolderBtn">显示列表</button>`
        folder.innerHTML = `<input type="checkbox" class="folder-checkbox" value="${folderName}" > ${folderName} ${toggleBtn}`;
        const fileList = document.createElement('ul');
        structure[folderName].forEach(fileName => {
            const fileItem = document.createElement('li');
            fileItem.innerHTML = `<input type="checkbox" class="file-checkbox" value="${fileName}"/> ${fileName}  <button class="editBtn">编辑</button>`;
            fileList.appendChild(fileItem);
        });
        folder.appendChild(fileList);
        container.appendChild(folder);
    }
}
fetch(pathListListURL).then(res => {
    if(!res.ok) throw new Error("网络异常");
    return res.json()
}).then((data)=> {
    if(data.success) {
        fileStructure = data.data
        displayFileTree(fileStructure, document.getElementById('fileTreeContainer'));
    } else {
        console.log('加载失败')
    }
}).catch(err=> errorMsg(err))



// 文件过滤功能
document.getElementById('fileSearchInput').addEventListener('input', function(e) {
    const searchText = e.target.value.toLowerCase();
    document.querySelectorAll('.file-checkbox').forEach(file => {
        const fileName = file.parentElement.textContent.toLowerCase();
        if (fileName.includes(searchText)) {
            file.parentElement.style.display = 'block';
        } else {
            file.parentElement.style.display = 'none';
        }
    });
});

// 添加到清单-添加到多个清单
// document.getElementById('addToListBtn').addEventListener('click', function() {
//     const selectedFiles = document.querySelectorAll('.file-checkbox:checked');
//     // 查找选中的清单
//     const selectedToDoList = document.querySelectorAll('.list-item-checkbox:checked');
//     selectedToDoList.forEach(toDoCheckBox=> {
//         // 创建一个容器显示列表
//         // const ulElement = document.createElement('ul')
//         // 遍历每一个选中的文件
//         selectedFiles.forEach(selectedFile => {
//             const fileName = selectedFile.value
//             const toDoCheckBoxValue = toDoCheckBox.value
//             let todoSet = todoMap.get(toDoCheckBoxValue)
//             if (todoSet.has(fileName)) {
//                 console.error(`已经存在同名文件${fileName}在清单${toDoCheckBox.value}中`)
//                 return
//             }
//             todoSet.add(fileName)
//         });
//     })
//     renderToDoMap()
// });

document.getElementById('addToListBtn').addEventListener('click', function() {
    const selectedFiles = document.querySelectorAll('.file-checkbox:checked');
    // 查找选中的清单
    // 创建一个容器显示列表
    // const ulElement = document.createElement('ul')
    // 遍历每一个选中的文件
    selectedFiles.forEach(selectedFile => {
        const fileName = selectedFile.value
        const todoValue = todoSelect.value
        let item = todoMap.get(todoValue)
        const todoSet = item['files']
        if (todoSet.has(fileName)) {
            console.error(`已经存在同名文件${fileName}在清单${todoValue}中`)
            return
        }
        todoSet.add(fileName)
        renderToDoMap()

        // document.querySelectorAll('.list-item-checkbox').forEach(itemCheckBox=> {
        //     if(itemCheckBox.value === todoValue) {
        //         const itemTodoList = itemCheckBox.parentElement.querySelector('.item-todo-list')
        //         itemTodoList.appendChild(document.createTextNode(fileName))
        //     }
        // })
    });

})

// ================== 动态按钮
document.addEventListener('click', function(e) {
    // 文件夹勾选框功能
    if (e.target && e.target.classList.contains('folder-checkbox')) {
        const isChecked = e.target.checked;
        const fileItems = e.target.parentElement.querySelectorAll('.file-checkbox');
        fileItems.forEach(fileCheckbox => fileCheckbox.checked = isChecked);
    }

    // 显示/收起子文件夹和文件列表
    if (e.target && e.target.classList.contains('toggleFolderBtn')) {
        const fileList = e.target.parentElement.querySelector('ul');
        if (fileList.style.display === 'none' || fileList.style.display === '') {
            fileList.style.display = 'block';
            e.target.textContent = '收起列表';
        } else {
            fileList.style.display = 'none';
            e.target.textContent = '显示列表';
        }
    }

    // 展示或收起清单
    // if (e.target && e.target.classList.contains('showListBtn')) {
    //     const listItems = e.target.parentElement.querySelectorAll('li');
    //     if (e.target.textContent === '展示清单') {
    //         // 展示清单内容
    //         listItems.forEach(item => item.style.display = 'block');
    //         e.target.textContent = '收起清单';
    //     } else {
    //         // 收起清单内容
    //         listItems.forEach(item => item.style.display = 'none');
    //         e.target.textContent = '展示清单';
    //     }
    // }

    // 删除清单中的文件
    if (e.target && e.target.classList.contains('removeFileBtn')) {
        e.target.parentElement.remove();
        // 获取文件名称
        const todoItem = e.target.parentElement.querySelector('.todo-item-name')
        // 获取文件夹名称
        const folderName = e.target.closest('li').querySelector(".list-item-checkbox").value;
        console.log(folderName,todoItem)
    }

    // 编辑
    if (e.target && e.target.classList.contains('editBtn')) {
        const fileName = e.target.closest('li').querySelector(".file-checkbox").value;
        console.log('编辑', fileName)
        editFile(fileName)
    }
});

function editFile(fileName) {
    const editURL = `${pathListEditURL}/${fileName}`;
    const a= document.createElement('a');
    a.target= '_blank';
    a.href= editURL
    a.click();
}