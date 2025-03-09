document.addEventListener("DOMContentLoaded", function () {
    // Chat functionality
    const chatBody = document.getElementById("chat-body");
    const userInput = document.getElementById("user-input");
    const sendBtn = document.getElementById("send-btn");

    function appendMessage(sender, message) {
        const msgDiv = document.createElement("div");
        msgDiv.classList.add("message", sender === "user" ? "user-message" : "bot-message");
        msgDiv.textContent = message;
        chatBody.appendChild(msgDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
        return msgDiv;
    }

    function sendMessage() {
        const message = userInput?.value.trim();
        if (!message) return;

        appendMessage("user", message);
        userInput.value = "";

        // Insert a "thinking..." placeholder for the bot
        const botTypingMsg = appendMessage("bot", "Thinking...");

        fetch(`/chat/?message=${encodeURIComponent(message)}`)
            .then(response => response.json())
            .then(data => {
                botTypingMsg.innerHTML = marked.parse(data.response);
            })
            .catch(error => {
                console.error("Error:", error);
                botTypingMsg.textContent = "Oops! Something went wrong.";
            });
    }

    if (sendBtn && userInput) {
        sendBtn.addEventListener("click", sendMessage);
        userInput.addEventListener("keypress", function (event) {
            if (event.key === "Enter") {
                sendMessage();
            }
        });
    }

    // Resume Toggle Functionality
    function toggleResume(id) {
        let content = document.getElementById("resume-" + id);
        if (content) {
            content.style.display = content.style.display === "none" || content.style.display === "" ? "block" : "none";
        }
    }

    // Attach click event to all resume toggle buttons
    const resumeButtons = document.querySelectorAll(".toggle-btn");
    resumeButtons.forEach(button => {
        button.addEventListener("click", function () {
            const id = this.getAttribute("data-id"); // Get the ID from the data attribute
            toggleResume(id);
        });
    });
});
