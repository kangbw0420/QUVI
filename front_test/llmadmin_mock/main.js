const BASE_URL = "http://localhost:8000/llmadmin";

// Users
async function fetchUsers() {
    try {
        const response = await fetch(`${BASE_URL}/users`);
        const users = await response.json();
        console.log('GET /users 응답:', users);
        
        const userList = document.getElementById('userList');
        userList.innerHTML = '<h2>Users</h2>';
        users.forEach(user => {
            const userDiv = document.createElement('div');
            userDiv.textContent = user;
            userDiv.style.cursor = 'pointer';
            userDiv.onclick = () => fetchSessions(user);
            userList.appendChild(userDiv);
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
        
        const sessionList = document.getElementById('sessionList');
        sessionList.innerHTML = `<h2>Sessions for ${userId}</h2>`;
        sessions.forEach(session => {
            const sessionDiv = document.createElement('div');
            sessionDiv.textContent = `Start: ${session.session_start} | End: ${session.session_end} | Status: ${session.session_status}`;
            sessionDiv.style.cursor = 'pointer';
            sessionDiv.onclick = () => fetchChains(session.session_id);
            sessionList.appendChild(sessionDiv);
        });

        // Clear subsequent displays
        document.getElementById('chainList').innerHTML = '';
        document.getElementById('traceInfo').innerHTML = '';
        document.getElementById('qnaList').innerHTML = '';
        document.getElementById('stateList').innerHTML = '';
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
        
        const chainList = document.getElementById('chainList');
        chainList.innerHTML = `<h2>Chains for Session ${sessionId}</h2>`;
        chains.forEach(chain => {
            const chainDiv = document.createElement('div');
            chainDiv.textContent = `Question: ${chain.chain_question} | Start: ${chain.chain_start} | Status: ${chain.chain_status}`;
            chainDiv.style.cursor = 'pointer';
            chainDiv.onclick = () => fetchTraces(chain.id);
            chainList.appendChild(chainDiv);
        });

        // Clear subsequent displays
        document.getElementById('traceInfo').innerHTML = '';
        document.getElementById('qnaList').innerHTML = '';
        document.getElementById('stateList').innerHTML = '';
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
        
        const traceInfo = document.getElementById('traceInfo');
        traceInfo.innerHTML = `<h2>Chain and Traces Info</h2>
            <div>Question: ${data.chain.chain_question}</div>
            <div>Answer: ${data.chain.chain_answer}</div>
            <h3>Traces:</h3>`;
        
        data.traces.forEach(trace => {
            const traceDiv = document.createElement('div');
            traceDiv.textContent = `Type: ${trace.node_type} | Status: ${trace.trace_status}`;
            traceDiv.style.cursor = 'pointer';
            traceDiv.onclick = () => {
                fetchQnas(trace.id);
                fetchStates(trace.id);
            };
            traceInfo.appendChild(traceDiv);
        });

        // Clear subsequent displays
        document.getElementById('qnaList').innerHTML = '';
        document.getElementById('stateList').innerHTML = '';
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
        
        const qnaList = document.getElementById('qnaList');
        qnaList.innerHTML = `<h2>QnAs for Trace ${traceId}</h2>`;
        qnas.forEach(qna => {
            const qnaDiv = document.createElement('div');
            qnaDiv.innerHTML = `
                <div>Q: ${qna.question}</div>
                <div>A: ${qna.answer}</div>
                <div>Model: ${qna.model}</div>
                <hr>
            `;
            qnaList.appendChild(qnaDiv);
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
        
        const stateList = document.getElementById('stateList');
        stateList.innerHTML = `<h2>States for Trace ${traceId}</h2>`;
        states.forEach(state => {
            const stateDiv = document.createElement('div');
            stateDiv.innerHTML = `
                <div>Question: ${state.user_question}</div>
                <div>Selected Table: ${state.selected_table}</div>
                <div>SQL: ${state.sql_query}</div>
                <div>Answer: ${state.final_answer}</div>
                <hr>
            `;
            stateList.appendChild(stateDiv);
        });
    } catch (error) {
        console.error('Error:', error);
    }
}

// Initial load
window.onload = fetchUsers;