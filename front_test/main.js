let debugLogs = [];
        
function addDebugLog(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = {
        timestamp,
        message,
        type
    };
    debugLogs.push(logEntry);
    updateDebugDisplay();
}

function updateDebugDisplay() {
    const debugDiv = document.getElementById('debug');
    debugDiv.innerHTML = debugLogs
        .map(log => `
            <div class="log-entry">
                <span class="timestamp">[${log.timestamp}]</span>
                <span class="status ${log.type}">${log.message}</span>
            </div>
        `)
        .join('');
    debugDiv.scrollTop = debugDiv.scrollHeight;
}

function clearLogs() {
    debugLogs = [];
    document.getElementById('debug').innerHTML = '';
    document.getElementById('response').innerHTML = '';
    document.getElementById('dataTableContainer').style.display = 'none';
    document.getElementById('timeline').innerHTML = '';
    document.getElementById('answerContent').innerHTML = '';
    document.getElementById('answerContainer').style.display = 'none';
}

function createDataTable(data) {
    if (!data || !Array.isArray(data) || data.length === 0) return;

    const tableContainer = document.getElementById('dataTableContainer');
    const table = document.getElementById('dataTable');
    table.innerHTML = '';

    // 테이블 헤더 생성
    const headers = Object.keys(data[0]);
    const headerRow = document.createElement('tr');
    headers.forEach(header => {
        const th = document.createElement('th');
        th.textContent = header;
        headerRow.appendChild(th);
    });
    table.appendChild(headerRow);

    // 테이블 데이터 행 생성
    data.forEach(row => {
        const tr = document.createElement('tr');
        headers.forEach(header => {
            const td = document.createElement('td');
            td.textContent = row[header];
            tr.appendChild(td);
        });
        table.appendChild(tr);
    });

    tableContainer.style.display = 'block';
}

async function sendQuestion() {
    try {
        const sendBtn = document.getElementById('sendBtn');
        const responseDiv = document.getElementById('response');
        const question = document.getElementById('question').value;

        sendBtn.disabled = true;
        sendBtn.innerText = 'Processing...';
        
        responseDiv.innerHTML = '';
        
        addDebugLog(`Question received: ${question}`);

        const requestOptions = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({task: question})
        };
        addDebugLog(`Request options prepared`);

        addDebugLog('Sending request to backend...');
        const response = await fetch('http://localhost:8000/process', requestOptions);
        addDebugLog(`Response received (Status: ${response.status})`);

        if (!response.ok) {
            throw new Error(`Server responded with status ${response.status}`);
        }

        addDebugLog('Parsing response data...');
        const data = await response.json();

        // JSON 응답 표시
        responseDiv.innerHTML = `
            <div class="status success">Request Successful</div>
            <pre>${JSON.stringify(data, null, 2)}</pre>
        `;

        // timeline 표시
        if (data.execution_timeline) {
            updateTimeline(data.execution_timeline);
        }

        // result 값 표시
        if (data.result && data.result.answer) {
            updateAnswerContainer(data.result.answer);
        }
        
        // raw_data로 테이블 생성
        if (data.raw_data && Array.isArray(data.raw_data)) {
            createDataTable(data.raw_data);
        }

    } catch (error) {
        addDebugLog(`Error: ${error.message}`, 'error');
        responseDiv.innerHTML = `
            <div class="status error">
                Error: ${error.message}
            </div>
        `;
        document.getElementById('dataTableContainer').style.display = 'none';
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerText = 'Send';
    }
}

document.getElementById('question').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendQuestion();
    }
});

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const minutes = date.getMinutes();
    const seconds = date.getSeconds();
    const milliseconds = date.getMilliseconds();
    
    return `${minutes}m ${seconds}s ${String(milliseconds).padStart(4, '0')}`;
}

function calculateDuration(start, end) {
    const startTime = new Date(start);
    const endTime = new Date(end);
    const durationMs = endTime - startTime;
    
    const minutes = Math.floor(durationMs / (1000 * 60));
    const seconds = Math.floor((durationMs % (1000 * 60)) / 1000);
    const milliseconds = Math.round(durationMs % 1000);
    
    let durationStr = '';
    if (minutes > 0) {
        durationStr += `${minutes}m `;
    }
    durationStr += `${seconds}s ${String(milliseconds).padStart(4, '0')}`;
    
    return durationStr;
}

function updateTimeline(timelineData) {
    const timelineDiv = document.getElementById('timeline');
    timelineDiv.innerHTML = '';
    
    // Planner Phase
    if (timelineData.planner) {
        const plannerDuration = calculateDuration(timelineData.planner.start, timelineData.planner.end);
        const plannerHtml = `
            <div class="timeline-phase">
                <h4>Planner</h4>
                <p><strong>${plannerDuration}</strong></p>
                <p>Start: ${formatTime(timelineData.planner.start)}</p>
                <p>End: ${formatTime(timelineData.planner.end)}</p>
            </div>
        `;
        timelineDiv.innerHTML += plannerHtml;
    }
    
    // Tools Phase
    if (timelineData.tools && timelineData.tools.length > 0) {
        const toolsStartTime = timelineData.tools[0].start;
        const toolsEndTime = timelineData.tools[timelineData.tools.length - 1].end;
        const totalToolsDuration = calculateDuration(toolsStartTime, toolsEndTime);
        
        let toolsHtml = `
            <div class="timeline-phase">
                <h4>Tools</h4>
                <p><strong>${totalToolsDuration}</strong></p>
            </div>
        `;
        
        timelineData.tools.forEach((tool, index) => {
            const toolDuration = calculateDuration(tool.start, tool.end);
            toolsHtml += `
                <div class="timeline-phase">
                    <h4>Tool ${index + 1}</h4>
                    <p><strong>${toolDuration}</strong></p>
                    <p>Start: ${formatTime(tool.start)}</p>
                    <p>End: ${formatTime(tool.end)}</p>
                </div>
            `;
        });
        
        timelineDiv.innerHTML += toolsHtml;
    }
    
    // Solver Phase
    if (timelineData.solver) {
        const solverDuration = calculateDuration(timelineData.solver.start, timelineData.solver.end);
        const solverHtml = `
            <div class="timeline-phase">
                <h4>Solver</h4>
                <p><strong>${solverDuration}</strong></p>
                <p>Start: ${formatTime(timelineData.solver.start)}</p>
                <p>End: ${formatTime(timelineData.solver.end)}</p>
            </div>
        `;
        timelineDiv.innerHTML += solverHtml;
    }
}

function updateAnswerContainer(answerText) {
    const answerContainer = document.getElementById('answerContainer');
    const answerContent = document.getElementById('answerContent');
    
    if (answerText && typeof answerText === 'string') {
        // marked.js를 사용해 마크다운을 HTML로 변환
        answerContent.innerHTML = marked.parse(answerText);
        answerContainer.style.display = 'block';
    } else {
        answerContainer.style.display = 'none';
    }
}