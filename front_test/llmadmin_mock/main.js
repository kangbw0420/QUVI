const BASE_URL = "http://localhost:8000/llmadmin";

// Router
function handleRoute() {
    const path = window.location.pathname;
    const contentDiv = document.getElementById('content');
    
    // Clear previous content
    contentDiv.innerHTML = '<div id="data"></div>';
    
    if (path === '/' || path === '/users') {
        fetchUsers();
    } else if (path.startsWith('/sessions/')) {
        const userId = path.split('/sessions/')[1];
        fetchSessions(userId);
    } else if (path.startsWith('/chains/')) {
        const sessionId = path.split('/chains/')[1];
        fetchChains(sessionId);
    } else if (path.startsWith('/traces/')) {
        const chainId = path.split('/traces/')[1];
        fetchTraces(chainId);
    } else if (path.startsWith('/qnas/')) {
        const traceId = path.split('/qnas/')[1];
        fetchQnas(traceId);
    } else if (path.startsWith('/states/')) {
        const traceId = path.split('/states/')[1];
        fetchStates(traceId);
    }
}

// Users
async function fetchUsers() {
    try {
        const response = await fetch(`${BASE_URL}/users`);
        const users = await response.json();
        console.log('GET /users 응답:', users);
        
        const dataDiv = document.getElementById('data');
        dataDiv.innerHTML = '<h2>Users</h2>';
        users.forEach(user => {
            const userDiv = document.createElement('div');
            userDiv.textContent = user;
            userDiv.style.cursor = 'pointer';
            userDiv.onclick = () => {
                history.pushState({}, '', `/sessions/${user}`);
                handleRoute();
            };
            dataDiv.appendChild(userDiv);
        });
    } catch (error) {
        console.error('Error:', error);
    }
}

// Sessions
async function fetchSessions(userId) {
    try {
        const response = await fetch(`${BASE_URL}/sessions/${userId}`);
        const sessions = await response.json();
        console.log(`GET /sessions/${userId} 응답:`, sessions);
        
        const dataDiv = document.getElementById('data');
        dataDiv.innerHTML = `
            <h2>Sessions for ${userId}</h2>
            <div onclick="history.back()" style="cursor: pointer">← Back</div>
        `;
        
        sessions.forEach(session => {
            const sessionDiv = document.createElement('div');
            sessionDiv.textContent = `ID: ${session.session_id} | Start: ${session.session_start} | Status: ${session.session_status}`;
            sessionDiv.style.cursor = 'pointer';
            sessionDiv.onclick = () => {
                history.pushState({}, '', `/chains/${session.session_id}`);
                handleRoute();
            };
            dataDiv.appendChild(sessionDiv);
        });
    } catch (error) {
        console.error('Error:', error);
    }
}

// Chains
async function fetchChains(sessionId) {
    try {
        const response = await fetch(`${BASE_URL}/chains/${sessionId}`);
        const chains = await response.json();
        console.log(`GET /chains/${sessionId} 응답:`, chains);
        
        const dataDiv = document.getElementById('data');
        dataDiv.innerHTML = `
            <h2>Chains for Session ${sessionId}</h2>
            <div onclick="history.back()" style="cursor: pointer">← Back</div>
        `;
        
        chains.forEach(chain => {
            const chainDiv = document.createElement('div');
            chainDiv.textContent = `Question: ${chain.chain_question} | Start: ${chain.chain_start} | Status: ${chain.chain_status}`;
            chainDiv.style.cursor = 'pointer';
            chainDiv.onclick = () => {
                history.pushState({}, '', `/traces/${chain.id}`);
                handleRoute();
            };
            dataDiv.appendChild(chainDiv);
        });
    } catch (error) {
        console.error('Error:', error);
    }
}

// Traces
async function fetchTraces(chainId) {
    try {
        const response = await fetch(`${BASE_URL}/traces/${chainId}`);
        const data = await response.json();
        console.log(`GET /traces/${chainId} 응답:`, data);
        
        const dataDiv = document.getElementById('data');
        dataDiv.innerHTML = `
            <h2>Chain and Traces Info</h2>
            <div onclick="history.back()" style="cursor: pointer">← Back</div>
            <div>Question: ${data.chain.chain_question}</div>
            <div>Answer: ${data.chain.chain_answer}</div>
            <h3>Traces:</h3>
        `;
        
        data.traces.forEach(trace => {
            const traceDiv = document.createElement('div');
            traceDiv.style.cursor = 'pointer';
            traceDiv.innerHTML = `
                <div>Type: ${trace.node_type} | Status: ${trace.trace_status}</div>
                <div>
                    <span onclick="history.pushState({}, '', '/qnas/${trace.id}'); handleRoute();" style="color: blue; margin-right: 10px; cursor: pointer">View QnAs</span>
                    <span onclick="history.pushState({}, '', '/states/${trace.id}'); handleRoute();" style="color: blue; cursor: pointer">View States</span>
                </div>
                <hr>
            `;
            dataDiv.appendChild(traceDiv);
        });
    } catch (error) {
        console.error('Error:', error);
    }
}

// QnAs
async function fetchQnas(traceId) {
    try {
        const response = await fetch(`${BASE_URL}/qnas/${traceId}`);
        const qnas = await response.json();
        console.log(`GET /qnas/${traceId} 응답:`, qnas);
        
        const dataDiv = document.getElementById('data');
        dataDiv.innerHTML = `
            <h2>QnAs for Trace ${traceId}</h2>
            <div onclick="history.back()" style="cursor: pointer">← Back</div>
        `;
        
        qnas.forEach(qna => {
            const qnaDiv = document.createElement('div');
            qnaDiv.innerHTML = `
                <div>Q: ${qna.question}</div>
                <div>A: ${qna.answer}</div>
                <div>Model: ${qna.model}</div>
                <hr>
            `;
            dataDiv.appendChild(qnaDiv);
        });
    } catch (error) {
        console.error('Error:', error);
    }
}

// States
async function fetchStates(traceId) {
    try {
        const response = await fetch(`${BASE_URL}/states/${traceId}`);
        const states = await response.json();
        console.log(`GET /states/${traceId} 응답:`, states);
        
        const dataDiv = document.getElementById('data');
        dataDiv.innerHTML = `
            <h2>States for Trace ${traceId}</h2>
            <div onclick="history.back()" style="cursor: pointer">← Back</div>
        `;
        
        states.forEach(state => {
            const stateDiv = document.createElement('div');
            stateDiv.innerHTML = `
                <div>Question: ${state.user_question}</div>
                <div>Selected Table: ${state.selected_table}</div>
                <div>SQL: ${state.sql_query}</div>
                <div>Answer: ${state.final_answer}</div>
                <hr>
            `;
            dataDiv.appendChild(stateDiv);
        });
    } catch (error) {
        console.error('Error:', error);
    }
}

// Handle initial load and browser navigation
window.onload = handleRoute;
window.onpopstate = handleRoute;