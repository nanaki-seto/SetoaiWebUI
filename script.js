function send_message() {
    const userInput = document.getElementById('user-input').value;
    if (userInput.trim() === "") {
        return;
    }

    document.getElementById('user-input').value = "";

    const chatHistoryElement = document.getElementById('chat-history');
    chatHistoryElement.innerHTML += `<div class="message admin">Admin: ${userInput}</div>`;

    // Send user input to the AI server
    fetch('/ai', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ userInput: userInput })
    })
    .then(response => response.json())
    .then(data => {
        const aiResponse = data.prediction;
        process_ai_response(aiResponse);
        chatHistoryElement.scrollTop = chatHistoryElement.scrollHeight;
    })
    .catch(error => {
        console.error('Error:', error);
        chatHistoryElement.innerHTML += `<div class="message ai">Seto-AI: An error occurred while processing your request.</div>`;
    });
}

function process_ai_response(response) {
    const chatHistoryElement = document.getElementById('chat-history');
    const responses = response.split("\n");

    responses.forEach(res => {
        chatHistoryElement.innerHTML += `<div class="message ai">Seto-AI: ${res}</div>`;
    });
}
