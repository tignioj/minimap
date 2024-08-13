const canvas = document.getElementById('myCanvas');
const ctx = canvas.getContext('2d');
const editPanel = document.getElementById('editPanel');
const xInput = document.getElementById('x');
const yInput = document.getElementById('y');
// const moveModeInput = document.getElementById('moveMode');
const userXInput = document.getElementById('userX');
const userYInput = document.getElementById('userY');
const nameInput = document.getElementById('nameInput');
const countrySelect = document.getElementById('countrySelect')

const msgElement = document.getElementById("msg")

const saveButton = document.getElementById('saveButton');
const deleteButton = document.getElementById('deleteButton');
const cancelButton = document.getElementById('cancelButton');
const newButton = document.getElementById('newButton');
const insertNodeButton = document.getElementById('insertNodeButton');
const startRecordButton = document.getElementById('startRecordButton');
const stopRecordButton = document.getElementById('stopRecordButton');
const saveRecordButton = document.getElementById('saveRecordButton');
const loadRecordButton = document.getElementById('loadRecordButton')
const playBackButton = document.getElementById('playBackButton');
const pointRadius = 4;
const serverURL = 'http://127.0.0.1:5000'

let selectedPointIndex = null;
let draggingPointIndex = null;
let dragOffsetX = 0;
let dragOffsetY = 0;
let isCtrlPressed = false;
let isAltPressed = false;
let isStartRecord = false;
let isPlayingRecord = false;

// 加载数据
pos = { x: 0, y: 0, type: 'start' }
points = []
isDraggingMap = false

function info(text) {
    msgElement.classList.remove('error-msg')
    console.log(text)
    msgElement.innerText = text
}
function errorMsg(text) {
    msgElement.classList.add('error-msg')
    console.error(text)
    msgElement.innerText = text
}

// 更新画布中心
function updateCanvasCenter(newPoint) {
    pos  = newPoint;
    // 设置缩放比例和偏移量
    scale = 1; // 可以根据需要调整缩放比例
    offsetX = canvas.width / 2 - newPoint.x;
    offsetY = canvas.height / 2 - newPoint.y;
    drawMap(newPoint.x, newPoint.y)
    // drawPoints()
    // drawUserPoint(newPoint.x, newPoint.y);
    // console.log(pos)
}
function drawMap(x,y) {
    // if (!isStartRecord) return
    width = 500
    imageUrl = `${serverURL}/minimap/get_region_map?x=${x}&y=${y}&width=${width}`
    // 创建一个 Image 对象
    const img = new Image();

    // 设置跨域属性（如果图片服务器允许跨域）
    img.crossOrigin = 'Anonymous';

    // 设定 image 对象的 src 属性为 HTTP 请求的 URL
    img.src = imageUrl;

    // 等待图片加载完成
    img.onload = function() {
        // 绘制图片到 canvas 上
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        drawPoints()
        drawUserPoint(x,y)
    };
}

// 请求服务器获取新位置
function fetchNewPosition() {
    if(!isStartRecord) return
    fetch(`${serverURL}/minimap/get_position`) // 替换为实际的服务器地址
        .then(response => response.json())
        .then(data => {
            const newPosition = {
                x: data[0],
                y: data[1]
            };
            updateCanvasCenter(newPosition);
            userXInput.value = newPosition.x
            userYInput.value = newPosition.y
        })
        .catch(error => console.error('Error fetching position:', error));
}

setInterval(fetchNewPosition, 100); // 每5秒请求一次
startRecordButton.addEventListener('click', ()=> {
    info("正在记录中,请不要刷新网页，否则数据丢失")
    isStartRecord = true
})
stopRecordButton.addEventListener('click', ()=> {
    info("已停止记录")
    isStartRecord = false
})
function isUndefinedNullOrEmpty(value) {
    return value === undefined || value === null || value === "";
}
function getPathObject() {
    name = nameInput.value
    country = countrySelect.value
    return {
        name: isUndefinedNullOrEmpty(name) ? 'undefined' : name,
        country: isUndefinedNullOrEmpty(countrySelect) ? '蒙德': country,
        positions: points
    };
}
function setPlayingRecord(playing) {
    if (playing) {
        isPlayingRecord = true
        playBackButton.disabled =  true
    } else {
        isPlayingRecord = false
        playBackButton.disabled = false
    }
}

playBackButton.addEventListener('click', () => {
    if(isPlayingRecord) { return; }

    if (points.length < 1)  {
        errorMsg('空路径，无法回放！')
        return
    }
    info('回放中, 已停止记录，按下ESC停止回放')
    isStartRecord = false  // 停止记录

    setPlayingRecord(true)
    const url = `${serverURL}/playback`; // 替换为实际的 API 端点
    data = getPathObject()
    fetch(url, {
        method: 'POST', // 请求方法
        headers: {
            'Content-Type': 'application/json' // 指定发送的数据格式为 JSON
        },
        body: JSON.stringify(data) // 将 JavaScript 对象转换为 JSON 字符串
    })
    .then(response => {
        if (!response.ok) {
            setPlayingRecord(false)
            throw new Error('Network response was not ok ' + response.statusText);
        }
        return response.json(); // 解析响应为 JSON
    })
    .then(data => {
        console.log('Success:', data); // 处理成功的响应
        if (data.result === true) {
            info(data.msg)
            setPlayingRecord(true)
        } else {
            errorMsg(data.msg)
            setPlayingRecord(false)
        }
    })
    .catch(error => {
        console.error('Error:', error); // 处理错误
        errorMsg(error)
        setPlayingRecord(false)
    });

})
function saveDictAsJsonFile(dict, fileName) {
    // 将对象转换为 JSON 字符串
    const jsonString = JSON.stringify(dict, null, 2); // 格式化 JSON 字符串

    // 创建 Blob 对象
    const blob = new Blob([jsonString], { type: 'application/json' });

    // 创建一个临时的链接
    const url = URL.createObjectURL(blob);

    // 创建一个隐藏的 <a> 元素
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;

    // 触发下载
    a.click();

    // 清理
    URL.revokeObjectURL(url);
}
saveRecordButton.addEventListener('click', () => {
    obj = getPathObject()
    const count = obj.positions.filter(item => item.type === "target").length;
    saveDictAsJsonFile(obj, `${obj.name}_${obj.country}_${count}个.json`)
})
loadRecordButton.addEventListener('click', () => {
})

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) {
        return;
    }

    // 读取文件内容
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const json = e.target.result;
            const obj = JSON.parse(json);
             // JSON.stringify(obj, null, 2);
            console.log(obj); // 打印到控制台
            nameInput.value = obj['name']
            points = obj['positions']
            pos = points[0]
            countrySelect.value = obj['country']
            updateCanvasCenter(pos)
            info('加载成功')
        } catch (error) {
            errorMsg('json解析错误:', error);
        }
    };

    reader.readAsText(file);
}
document.getElementById('fileInput').addEventListener('change', handleFileSelect);


document.addEventListener("DOMContentLoaded", function() {
    const socket = io();
    socket.on('connect', function() {
        drawMap(0,0)
        console.log('WebSocket connection established');
    });

    socket.on('disconnect', function() {
        errorMsg('已断开服务器')
        console.log('WebSocket connection closed');
    });

    socket.on('key_event', function(data) {
        // 处理从服务器接收到的键盘事件数据
        console.log(data)
        if (data.key === 'esc') {
            if (isPlayingRecord) {
                info('执行中断')
                setPlayingRecord(false)
            }
        } else if (data.key === 'insert') {
            insertPosition()
        } else if (data.key === 'backspace')
            if (isStartRecord) {
                info('你按下了backspace,删除上一个点位')
                points.pop()
            }
        else if (data.key === 'delete') {
            // points = []
        }
    });
    socket.on('playback_event', function (data) {
        if(data.result) {
            info('执行结束')
            setPlayingRecord(false)
        }else {
            info('执行过程出现异常')
            setPlayingRecord(false)
        }
    })
});

//################################## 快捷键
document.addEventListener('keydown', (event) => {
    if (event.ctrlKey) {
        isCtrlPressed = true;
        hideEditPanel()
    }
    if (event.altKey) {isAltPressed = true;}
    // console.log(event)
});
document.addEventListener('keyup', (event) => {
    console.log(event)
    if (!event.ctrlKey) { isCtrlPressed = false; }
    if (event.code) {isAltPressed = false;}
});
canvas.addEventListener('mousemove', (event) => {
    const canvasRect = canvas.getBoundingClientRect();
    const mouseX = event.clientX - canvasRect.left;
    const mouseY = event.clientY - canvasRect.top;

    if (draggingPointIndex !== null) {
        const { x: newX, y: newY } = getWorldCoords(mouseX, mouseY);
        updatePointPosition(newX, newY);
        drawMap(pos.x,pos.y)
        return;
    } else if (isDraggingMap ) {
        const currentX = event.clientX - canvas.getBoundingClientRect().left;
        const currentY = event.clientY - canvas.getBoundingClientRect().top;

        const dx = currentX - startX;
        const dy = currentY - startY;

        offsetX += dx;
        offsetY += dy;

        startX = currentX;
        startY = currentY;
        drawPoints()
        // offsetX = canvasWidth / 2 - x
        // offsetY = canvasHeight / 2 -y;
        nx = canvasWidth /2 - offsetX
        ny = canvasHeight/2 - offsetY
        pos = {x:nx, y:ny}
        drawMap(nx,ny)
    }

    let isHovered = false;
    points.forEach((point, index) => {
        const { x: canvasX, y: canvasY } = getCanvasCoords(point.x, point.y);
        if (isPointWithin(mouseX, mouseY, canvasX, canvasY)) {
            canvas.style.cursor = 'pointer';
            isHovered = true;
            selectedPointIndex = index;
            if(!isCtrlPressed) {
                showEditPanel(point.x, point.y, point.type, point.move_mode, point.action);
            }
            return;
        }
    });
    if (!isHovered) {
        canvas.style.cursor = 'default';
        selectedPointIndex = null;
        hideEditPanel();
    }
});
canvas.addEventListener('mousedown', (event) => {
    isDraggingMap = true
    startX = event.clientX - canvas.getBoundingClientRect().left;
    startY = event.clientY - canvas.getBoundingClientRect().top;

    if (selectedPointIndex !== null) {
        draggingPointIndex = selectedPointIndex;
        const canvasRect = canvas.getBoundingClientRect();
        const mouseX = event.clientX - canvasRect.left;
        const mouseY = event.clientY - canvasRect.top;
        selectedPoint = points[selectedPointIndex]
        const { x: pointX, y: pointY } = getCanvasCoords(selectedPoint.x, selectedPoint.y);
        dragOffsetX = points[selectedPointIndex].x - getWorldCoords(mouseX, mouseY).x;
        dragOffsetY = points[selectedPointIndex].y - getWorldCoords(mouseX, mouseY).y;
        event.preventDefault(); // Prevent default behavior
    }
});

canvas.addEventListener('mouseup', () => {
    draggingPointIndex = null;
    isDraggingMap = false;
});
canvas.addEventListener('click', (event) => {
    if (draggingPointIndex === null) {
        const canvasRect = canvas.getBoundingClientRect();
        const mouseX = event.clientX - canvasRect.left;
        const mouseY = event.clientY - canvasRect.top;

        points.forEach((point, index) => {
            const { x: canvasX, y: canvasY } = getCanvasCoords(point.x, point.y);
            if (isPointWithin(mouseX, mouseY, canvasX, canvasY)) {
                selectedPointIndex = index;
                showEditPanel(point.x, point.y, point.type, point.move_mode, point.action);
                return;
            }
        });
    }
});

saveButton.addEventListener('click', () => {
    if (selectedPointIndex !== null) {
        points[selectedPointIndex].x = parseFloat(xInput.value);
        points[selectedPointIndex].y = parseFloat(yInput.value);
        points[selectedPointIndex].type = getSelectedValue('type');
        points[selectedPointIndex].action = getSelectedValue('action')
        points[selectedPointIndex].move_mode = getSelectedValue('moveMode');
        hideEditPanel();
        drawPoints();
    }
});

deleteButton.addEventListener('click', () => {
    if (selectedPointIndex !== null) {
        points.splice(selectedPointIndex, 1);
        selectedPointIndex = null;
        hideEditPanel();
        drawMap(pos.x, pos.y)
        // drawPoints();
    }
});

cancelButton.addEventListener('click', () => {
    hideEditPanel();
});

newButton.addEventListener('click', (event) => {
    if (selectedPointIndex !== null) {
        newX = parseFloat(xInput.value);
        newY  = parseFloat(yInput.value);
        newType = getSelectedValue('type')
        newAction = getSelectedValue('action')
        newMoveMode = getSelectedValue('moveMode')
        point = { x: newX - 10, y: newY , type: newType, action: newAction, move_mode: newMoveMode }
        points.splice(selectedPointIndex+1, 0, point);
        hideEditPanel();
        drawPoints();
    }
})

function getUserCustomNode() {
    node = {
        x: Number(userXInput.value),
        y: Number(userYInput.value),
        type: getSelectedValue('userType'),
        move_mode: getSelectedValue('userMoveMode'),
        action: getSelectedValue('userAction')
    }
    return node
}

function insertPosition() {
    if (!isStartRecord) {
        errorMsg('请先开始记录再插入用户点位')
        return
    }
    node = getUserCustomNode()
    info(`插入点位(${node.x},${node.y})`)
    points.push(node)
}
insertNodeButton.addEventListener('click', insertPosition)

function getSelectedValue(name) {
    // Get the selected radio button
    const selectedRadio = document.querySelector(`input[name="${name}"]:checked`);

    // Check if a radio button is selected
    if (selectedRadio) {
        const selectedValue = selectedRadio.value;
        console.log('Selected mode:', selectedValue);
        // Optionally, do something with the selected value
        return selectedValue
    } else {
        console.log('No radio button selected');
        return ""
    }
}


function selectRadio(name,value) {
    // Deselect all radio buttons first
    document.querySelectorAll(`input[name="${name}"]`).forEach(radio => {
        radio.checked = false;
    });

    // Select the radio button with the specified value
    const radioToSelect = document.querySelector(`input[name="${name}"][value="${value}"]`);
    if (radioToSelect) {
        radioToSelect.checked = true;
    }
}


// =================== 绘画
// Initialize drawing
// 获取画布的宽度和高度
const canvasWidth = canvas.width;
const canvasHeight = canvas.height;

let scale = 1;
let offsetX = 0;
let offsetY = 0;

const { x, y } = pos;
offsetX = canvasWidth / 2 - x
offsetY = canvasHeight / 2 -y;
scale = 1;

function drawPoints() {
    // Draw lines
    for (let i = 0; i < points.length - 1; i++) {
        drawLine(points[i], points[i + 1]);
    }

    // Draw points
    points.forEach(point => {
        if (point.type === 'start') {
            color = 'red'
        } else if (point.type === 'path') {
            color = 'blue'
        } else {
            color = 'green'
        }
        drawPoint(point.x, point.y, color);
    });
}

function drawPoint(x, y, color) {
    const canvasX = x * scale + offsetX;
    const canvasY = y * scale + offsetY;

    ctx.beginPath();
    ctx.arc(canvasX, canvasY, pointRadius, 0, 2 * Math.PI);
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.fillStyle = color;
    ctx.fill();
}

function drawUserPoint(x,y) {
    if (!isStartRecord) return
    const canvasX = x * scale + offsetX;
    const canvasY = y * scale + offsetY;

    ctx.beginPath();
    ctx.arc(canvasX, canvasY, pointRadius, 0, 2 * Math.PI);
    ctx.strokeStyle = 'orange';
    ctx.lineWidth = 2;
    ctx.stroke(); // 绘制圆圈
}

// 绘制点
// function drawPoint(x, y) {
//     const canvasX = x * scale + offsetX;
//     const canvasY = y * scale + offsetY;
//
//     ctx.clearRect(0, 0, canvas.width, canvas.height); // 清空画布
//
//     ctx.beginPath();
//     ctx.arc(canvasX, canvasY, 5, 0, 2 * Math.PI);
//     ctx.fillStyle = 'red'; // 设置点的颜色
//     ctx.fill();
// }

function drawLine(from, to) {
    const fromX = from.x * scale + offsetX;
    const fromY = from.y * scale + offsetY;
    const toX = to.x * scale + offsetX;
    const toY = to.y * scale + offsetY;

    ctx.beginPath();
    ctx.moveTo(fromX, fromY);
    ctx.lineTo(toX, toY);
    ctx.strokeStyle = 'black';
    ctx.stroke();
}

function getCanvasCoords(x, y) {
    return {
        x: x * scale + offsetX,
        y: y * scale + offsetY
    };
}

function getWorldCoords(canvasX, canvasY) {
    return {
        x: (canvasX - offsetX) / scale,
        y: (canvasY - offsetY) / scale
    };
}

function isPointWithin(px, py, x, y, radius = pointRadius) {
    return Math.sqrt((px - x) ** 2 + (py - y) ** 2) < radius;
}

function showEditPanel(x, y, type, moveMode, action) {
    xInput.value = x;
    yInput.value = y;
    selectRadio('type',type)
    // moveModeInput.value = moveMode == null ? '': moveMode;
    selectRadio("moveMode",moveMode)
    selectRadio('action', action)
    editPanel.style.left = `${event.clientX}px`;
    editPanel.style.top = `${event.clientY}px`;
    editPanel.style.display = 'block';
    // editPanel.classList.remove('hidden');
}

function hideEditPanel() {
    // editPanel.classList.add('hidden');
    editPanel.style.display = 'none'
}

function updatePointPosition(newX, newY) {
    if (draggingPointIndex !== null) {
        const point = points[draggingPointIndex];
        point.x = newX + dragOffsetX;
        point.y = newY + dragOffsetY;
        drawPoints();
    }
}
drawPoints();
