const canvas = document.getElementById('myCanvas');
const ctx = canvas.getContext('2d');
const editPanel = document.getElementById('editPanel');
const xInput = document.getElementById('x');
const yInput = document.getElementById('y');
const typeInput = document.getElementById('type');
// const moveModeInput = document.getElementById('moveMode');
const actionInput = document.getElementById('action');
const userXInput = document.getElementById('userX');
const userYInput = document.getElementById('userY');

const saveButton = document.getElementById('saveButton');
const deleteButton = document.getElementById('deleteButton');
const cancelButton = document.getElementById('cancelButton');
const newButton = document.getElementById('newButton');
const insertNodeButton = document.getElementById('insertNodeButton');

let selectedPointIndex = null;
let draggingPointIndex = null;
let dragOffsetX = 0;
let dragOffsetY = 0;
let isCtrlPressed = false;


// 加载数据
// data = jsonData;
// console.log(jsonData)

pos = { x: 0, y: 0, type: 'start' }
points = []

// fetch('data.json').then(response => response.json()).then(jsonData => {
//     points = jsonData.positions
//     console.log(points)
//     draw()
// })
//
// 更新画布中心
function updateCanvasCenter(newPoint) {
    pos  = newPoint;
    // 设置缩放比例和偏移量
    scale = 1; // 可以根据需要调整缩放比例
    offsetX = canvas.width / 2 - newPoint.x;
    offsetY = canvas.height / 2 - newPoint.y;
    draw()
    drawUserPoint(newPoint.x, newPoint.y);
    console.log(pos)
}

// 请求服务器获取新位置
function fetchNewPosition() {
    fetch('http://127.0.0.1:5000/minimap/get_position') // 替换为实际的服务器地址
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
setInterval(fetchNewPosition, 1000); // 每5秒请求一次


document.addEventListener("DOMContentLoaded", function() {
    const socket = io();
    socket.on('key_event', function(data) {
        // 处理从服务器接收到的键盘事件数据
        console.log('Key event:', data.key);
        if (data.key === 'insert') {
            insertPosition()
        } else if (data.key === 'backspace')
            points.pop()
        else if (data.key === 'delete') {
            points = []
        }
    });

    socket.on('connect', function() {
        console.log('WebSocket connection established');
    });

    socket.on('disconnect', function() {
        console.log('WebSocket connection closed');
    });
});



//################################## 快捷键
document.addEventListener('keydown', (event) => {
    if (event.ctrlKey) {
        isCtrlPressed = true;
        hideEditPanel()
    }
    console.log(event)
});


window.addEventListener('keydown', (event)=> {
    // 重新绑定键盘监听
    if (event.ctrlKey) {
        isCtrlPressed = true;
        hideEditPanel()
    }
    console.log(event)
});

document.addEventListener('keyup', (event) => {
    if (!event.ctrlKey) { isCtrlPressed = false; }
});

canvas.addEventListener('mousemove', (event) => {
    const canvasRect = canvas.getBoundingClientRect();
    const mouseX = event.clientX - canvasRect.left;
    const mouseY = event.clientY - canvasRect.top;

    if (draggingPointIndex !== null) {
        const { x: newX, y: newY } = getWorldCoords(mouseX, mouseY);
        updatePointPosition(newX, newY);
        return;
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
        points[selectedPointIndex].type = typeInput.value;
        points[selectedPointIndex].action = actionInput.value;
        points[selectedPointIndex].move_mode = getSelectedValue()
        hideEditPanel();
        draw();
    }
});

deleteButton.addEventListener('click', () => {
    if (selectedPointIndex !== null) {
        points.splice(selectedPointIndex, 1);
        selectedPointIndex = null;
        hideEditPanel();
        draw();
    }
});

cancelButton.addEventListener('click', () => {
    hideEditPanel();
});

newButton.addEventListener('click', (event) => {
    if (selectedPointIndex !== null) {
        newX = parseFloat(xInput.value);
        newY  = parseFloat(yInput.value);
        newType = typeInput.value;
        newAction = actionInput.value;
        newMoveMode = getSelectedValue()
        point = { x: newX - 10, y: newY , type: newType, action: newAction, move_mode: newMoveMode }
        points.splice(selectedPointIndex+1, 0, point);
        hideEditPanel();
        draw();
    }
})

function insertPosition() {
    node = {
        x: Number(userXInput.value),
        y: Number(userYInput.value),
        type: 'path',
        move_mode: 'normal'
    }
    console.log(node)
    points.push(node)
}
insertNodeButton.addEventListener('click', insertPosition)


function getSelectedValue() {
    // Get the selected radio button
    const selectedRadio = document.querySelector('input[name="moveMode"]:checked');

    // Check if a radio button is selected
    if (selectedRadio) {
        const selectedValue = selectedRadio.value;
        console.log('Selected mode:', selectedValue);
        // Optionally, do something with the selected value
        return selectedValue
    } else {
        console.log('No radio button selected');
        return "normal"
    }
}


function selectRadio(value) {
    // Deselect all radio buttons first
    document.querySelectorAll('input[name="moveMode"]').forEach(radio => {
        radio.checked = false;
    });

    // Select the radio button with the specified value
    const radioToSelect = document.querySelector(`input[name="moveMode"][value="${value}"]`);
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

function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

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
    ctx.arc(canvasX, canvasY, 5, 0, 2 * Math.PI);
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.fillStyle = color;
    ctx.fill();
}

function drawUserPoint(x,y) {
    const canvasX = x * scale + offsetX;
    const canvasY = y * scale + offsetY;

    ctx.beginPath();
    ctx.arc(canvasX, canvasY, 5, 0, 2 * Math.PI);
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

function isPointWithin(px, py, x, y, radius = 5) {
    return Math.sqrt((px - x) ** 2 + (py - y) ** 2) < radius;
}

function showEditPanel(x, y, type, moveMode, action) {
    xInput.value = x;
    yInput.value = y;
    typeInput.value = type;
    // moveModeInput.value = moveMode == null ? '': moveMode;
    selectRadio(moveMode)
    actionInput.value = action == null ? '':action;
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
        draw();
    }
}

draw();