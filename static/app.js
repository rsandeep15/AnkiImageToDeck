const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const syncButton = document.getElementById("syncButton");
const statusLog = document.getElementById("statusLog");
const deckNameInput = document.getElementById("deckName");
const modelInput = document.getElementById("modelSelect");
const romanizedToggle = document.getElementById("romanizedToggle");

let selectedFile = null;

function setStatus(message, append = false) {
    if (append) {
        statusLog.textContent += `\n${message}`;
    } else {
        statusLog.textContent = message;
    }
}

function updateButtonState() {
    syncButton.disabled = !selectedFile;
}

function handleFiles(files) {
    const file = files[0];
    if (!file) {
        return;
    }
    if (!file.name.toLowerCase().endsWith(".pdf")) {
        setStatus("Please choose a PDF file.");
        selectedFile = null;
        updateButtonState();
        return;
    }
    selectedFile = file;
    setStatus(`Ready to sync: ${file.name}`);
    updateButtonState();
}

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragover");
    handleFiles(event.dataTransfer.files);
});

fileInput.addEventListener("change", (event) => {
    handleFiles(event.target.files);
});

syncButton.addEventListener("click", async () => {
    if (!selectedFile) {
        return;
    }
    setStatus("Uploading and syncing deck...");
    syncButton.disabled = true;

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("deck", deckNameInput.value);
    formData.append("model", modelInput.value);
    formData.append("romanized", romanizedToggle.checked ? "true" : "false");

    try {
        const response = await fetch("/sync", {
            method: "POST",
            body: formData,
        });
        const data = await response.json();
        if (data.ok) {
            setStatus(`✅ ${data.message}\n\n${data.stdout}`);
            if (data.stderr) {
                setStatus(`✅ ${data.message}\n\n${data.stdout}\n${data.stderr}`, true);
            }
        } else {
            setStatus(`⚠️ ${data.message}\n\n${data.stdout || ""}\n${data.stderr || ""}`);
        }
    } catch (error) {
        setStatus(`❌ Request failed: ${error}`);
    } finally {
        syncButton.disabled = false;
    }
});
