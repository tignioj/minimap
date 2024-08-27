// 初始化 Ace Editor
    const editor = ace.edit("editor");
    editor.setTheme("ace/theme/monokai");
    editor.session.setMode("ace/mode/yaml");

    function saveConfig() {
        const yamlContent = editor.getValue();
        fetch(saveConfigURL, {
            method: 'POST',
                headers: {
                    'Content-Type': 'text/plain',  // 使用纯文本格式上传
                },
                body: yamlContent,  // 直接发送 YAML 文本
        })
            .then(response => response.json())
            .then(data => {
                alert(data.msg);
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to save configuration');
            });
    }