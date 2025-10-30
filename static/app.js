const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const syncButton = document.getElementById("syncButton");
const statusLogSync = document.getElementById("statusLogSync");
const deckNameInput = document.getElementById("deckName");
const modelInput = document.getElementById("modelSelect");
const romanizedToggle = document.getElementById("romanizedToggle");

const deckSelect = document.getElementById("deckSelect");
const refreshDecksButton = document.getElementById("refreshDecks");
const generateAudioButton = document.getElementById("generateAudio");
const generateImagesButton = document.getElementById("generateImages");
const statusLogMedia = document.getElementById("statusLogMedia");

const tabButtons = document.querySelectorAll(".tab-button");
const tabPanels = document.querySelectorAll(".tab-panel");

let selectedFile = null;

function setStatus(element, message, append = false) {
    if (append) {
        element.textContent += `\n${message}`;
    } else {
        element.textContent = message;
    }
}

function showProgress(element, text) {
    const container = document.createElement("div");
    container.className = "progress";
    const spinner = document.createElement("div");
    spinner.className = "spinner";
    const label = document.createElement("span");
    label.textContent = text;
    container.appendChild(spinner);
    container.appendChild(label);
    element.parentNode.insertBefore(container, element);
    return container;
}

function updateProgress(container, text, etaText) {
    if (!container) {
        return;
    }
    const label = container.querySelector("span");
    if (label) {
        label.textContent = text;
        if (etaText) {
            label.innerHTML = `${text}<br><span class="eta-text">${etaText}</span>`;
        }
    }
}

function removeProgress(container) {
    if (container && container.parentNode) {
        container.parentNode.removeChild(container);
    }
}

function updateSyncButton() {
    syncButton.disabled = !selectedFile;
}

function handleFiles(files) {
    const file = files[0];
    if (!file) {
        return;
    }
    if (!file.name.toLowerCase().endsWith(".pdf")) {
        setStatus(statusLogSync, "Please choose a PDF file.");
        selectedFile = null;
        updateSyncButton();
        return;
    }
    selectedFile = file;
    setStatus(statusLogSync, `Ready to sync: ${file.name}`);
    updateSyncButton();
}

function switchTab(tabName) {
    tabButtons.forEach((button) => {
        button.classList.toggle("active", button.dataset.tab === tabName);
    });
    tabPanels.forEach((panel) => {
        panel.classList.toggle("active", panel.id === `tab-${tabName}`);
    });
}

tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
        switchTab(button.dataset.tab);
    });
});

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
    setStatus(statusLogSync, "Uploading and syncing deck...");
    const progressNode = showProgress(statusLogSync, "Processing PDF...");
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
            const etaText = data.eta_text || "";
            updateProgress(progressNode, "Sync complete!", etaText);
            setStatus(
                statusLogSync,
                `✅ ${data.message}${data.items_processed !== undefined ? ` (cards processed: ${data.items_processed})` : ""}\n\n${data.stdout}`
            );
            if (data.stderr) {
                setStatus(statusLogSync, `✅ ${data.message}\n\n${data.stdout}\n${data.stderr}`, true);
            }
        } else {
            setStatus(
                statusLogSync,
                `⚠️ ${data.message}\n\n${data.stdout || ""}\n${data.stderr || ""}`
            );
        }
    } catch (error) {
        setStatus(statusLogSync, `❌ Request failed: ${error}`);
    } finally {
        syncButton.disabled = false;
        removeProgress(progressNode);
    }
});

function updateMediaButtons() {
    const hasDeck = Boolean(deckSelect.value);
    generateAudioButton.disabled = !hasDeck;
    generateImagesButton.disabled = !hasDeck;
}

deckSelect.addEventListener("change", updateMediaButtons);

async function loadDecks() {
    setStatus(statusLogMedia, "Fetching decks...");
    deckSelect.disabled = true;
    generateAudioButton.disabled = true;
    generateImagesButton.disabled = true;

    try {
        const response = await fetch("/api/decks");
        const data = await response.json();
        deckSelect.innerHTML = "";
        if (data.ok && Array.isArray(data.decks) && data.decks.length > 0) {
            for (const deck of data.decks) {
                const option = document.createElement("option");
                option.value = deck;
                option.textContent = deck;
                deckSelect.appendChild(option);
            }
            setStatus(statusLogMedia, "Select a deck and choose an action.");
        } else {
            const option = document.createElement("option");
            option.value = "";
            option.textContent = data.message || "No decks found.";
            deckSelect.appendChild(option);
            setStatus(statusLogMedia, data.message || "No decks available.");
        }
    } catch (error) {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "Error loading decks.";
        deckSelect.appendChild(option);
        setStatus(statusLogMedia, `❌ Failed to fetch decks: ${error}`);
    } finally {
        deckSelect.disabled = false;
        updateMediaButtons();
    }
}

refreshDecksButton.addEventListener("click", () => {
    loadDecks();
});

async function triggerGeneration(endpoint, actionDescription) {
    const deck = deckSelect.value;
    if (!deck) {
        setStatus(statusLogMedia, "Please select a deck first.");
        return;
    }

    setStatus(statusLogMedia, `${actionDescription} for deck "${deck}"...`);
    const progressNode = showProgress(statusLogMedia, "Working...");
    generateAudioButton.disabled = true;
    generateImagesButton.disabled = true;

    try {
        const response = await fetch(endpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ deck }),
        });
        const data = await response.json();
        if (data.ok) {
            updateProgress(progressNode, "Job complete!", data.eta_text);
            const items = data.items_processed !== undefined ? ` (cards processed: ${data.items_processed})` : "";
            setStatus(
                statusLogMedia,
                `✅ ${data.message}${items}\n\n${data.stdout}${data.stderr ? `\n${data.stderr}` : ""}`
            );
        } else {
            setStatus(
                statusLogMedia,
                `⚠️ ${data.message}\n\n${data.stdout || ""}\n${data.stderr || ""}`
            );
        }
    } catch (error) {
        setStatus(statusLogMedia, `❌ Request failed: ${error}`);
    } finally {
        updateMediaButtons();
        removeProgress(progressNode);
    }
}

generateAudioButton.addEventListener("click", () => {
    triggerGeneration("/generate/audio", "Generating audio");
});

generateImagesButton.addEventListener("click", () => {
    triggerGeneration("/generate/images", "Generating images");
});

// Initialize
updateSyncButton();
loadDecks();
