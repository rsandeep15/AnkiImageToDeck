const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const syncButton = document.getElementById("syncButton");
const statusLogSync = document.getElementById("statusLogSync");
const deckNameInput = document.getElementById("deckName");
const textModelSelect = document.getElementById("textModelSelect");
const romanizedToggle = document.getElementById("romanizedToggle");

const audioDeckSelect = document.getElementById("audioDeckSelect");
const audioModelSelect = document.getElementById("audioModelSelect");
const refreshDecksAudio = document.getElementById("refreshDecksAudio");
const audioWorkerSelect = document.getElementById("audioWorkerSelect");
const generateAudioButton = document.getElementById("generateAudio");
const statusLogAudio = document.getElementById("statusLogAudio");

const imageDeckSelect = document.getElementById("imageDeckSelect");
const imageModelSelect = document.getElementById("imageModelSelect");
const skipGatingToggle = document.getElementById("skipGatingToggle");
const refreshDecksImages = document.getElementById("refreshDecksImages");
const imageWorkerSelect = document.getElementById("imageWorkerSelect");
const generateImagesButton = document.getElementById("generateImages");
const statusLogImages = document.getElementById("statusLogImages");

const tabButtons = document.querySelectorAll(".tab-button");
const tabPanels = document.querySelectorAll(".tab-panel");

let selectedFile = null;

function setStatus(element, message, append = false) {
    if (!element) return;
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
    label.innerHTML = text;
    container.appendChild(spinner);
    container.appendChild(label);
    element.parentNode.insertBefore(container, element);
    return container;
}

function updateProgress(container, text, etaText) {
    if (!container) return;
    const label = container.querySelector("span");
    if (!label) return;
    if (etaText) {
        label.innerHTML = `${text}<br><span class="eta-text">${etaText}</span>`;
    } else {
        label.textContent = text;
    }
}

function removeProgress(container) {
    if (container?.parentNode) {
        container.parentNode.removeChild(container);
    }
}

function updateSyncButton() {
    syncButton.disabled = !selectedFile || !textModelSelect.value;
}

function handleFiles(files) {
    const file = files[0];
    if (!file) return;
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
    button.addEventListener("click", () => switchTab(button.dataset.tab));
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

fileInput.addEventListener("change", (event) => handleFiles(event.target.files));

async function loadModels(kind, select, preferredValue, statusElement, onComplete) {
    if (!select) return;
    select.innerHTML = `<option value="">Loading ${kind} models...</option>`;
    select.disabled = true;
    try {
        const response = await fetch(`/api/models/${kind}`);
        const data = await response.json();
        if (data.ok && Array.isArray(data.models) && data.models.length) {
            select.innerHTML = "";
            data.models.forEach((id) => {
                const option = document.createElement("option");
                option.value = id;
                option.textContent = id;
                select.appendChild(option);
            });
            if (preferredValue && data.models.includes(preferredValue)) {
                select.value = preferredValue;
            }
        } else {
            select.innerHTML = `<option value="">No ${kind} models</option>`;
            if (statusElement) {
                setStatus(statusElement, data.message || `No ${kind} models available.`);
            }
        }
    } catch (error) {
        select.innerHTML = `<option value="">Unavailable</option>`;
        if (statusElement) {
            setStatus(statusElement, `❌ Failed to load ${kind} models: ${error}`);
        }
    } finally {
        select.disabled = false;
        if (typeof onComplete === "function") onComplete();
    }
}

function populateDeckSelect(select, decks) {
    if (!select) return;
    select.innerHTML = "";
    decks.forEach((deck) => {
        const option = document.createElement("option");
        option.value = deck;
        option.textContent = deck;
        select.appendChild(option);
    });
    if (!select.value && decks.length) {
        select.value = decks[0];
    }
}

async function loadDecks() {
    const selects = [audioDeckSelect, imageDeckSelect];
    selects.forEach((select) => {
        if (select) {
            select.innerHTML = '<option value="">Loading decks...</option>';
            select.disabled = true;
        }
    });
    setStatus(statusLogAudio, "Fetching decks...");
    setStatus(statusLogImages, "Fetching decks...");
    try {
        const response = await fetch("/api/decks");
        const data = await response.json();
        if (data.ok && Array.isArray(data.decks) && data.decks.length) {
            selects.forEach((select) => populateDeckSelect(select, data.decks));
            setStatus(statusLogAudio, "Select a deck and model to begin.");
            setStatus(statusLogImages, "Select a deck and model to begin.");
        } else {
            const message = data.message || "No decks found.";
            selects.forEach((select) => {
                if (select) {
                    select.innerHTML = `<option value="">${message}</option>`;
                }
            });
            setStatus(statusLogAudio, message);
            setStatus(statusLogImages, message);
        }
    } catch (error) {
        selects.forEach((select) => {
            if (select) {
                select.innerHTML = '<option value="">Error loading decks</option>';
            }
        });
        setStatus(statusLogAudio, `❌ Failed to fetch decks: ${error}`);
        setStatus(statusLogImages, `❌ Failed to fetch decks: ${error}`);
    } finally {
        selects.forEach((select) => {
            if (select) select.disabled = false;
        });
        updateAudioControls();
        updateImageControls();
    }
}

function updateAudioControls() {
    const hasDeck = Boolean(audioDeckSelect?.value);
    const hasModel = Boolean(audioModelSelect?.value);
    const hasWorkers = Boolean(audioWorkerSelect?.value);
    generateAudioButton.disabled = !(hasDeck && hasModel && hasWorkers);
}

function updateImageControls() {
    const hasDeck = Boolean(imageDeckSelect?.value);
    const hasImageModel = Boolean(imageModelSelect?.value);
    const hasWorkers = Boolean(imageWorkerSelect?.value);
    generateImagesButton.disabled = !(hasDeck && hasImageModel && hasWorkers);
}

syncButton.addEventListener("click", async () => {
    if (!selectedFile || !textModelSelect.value) {
        return;
    }

    setStatus(statusLogSync, "Uploading and syncing deck...");
    const progressNode = showProgress(statusLogSync, "Processing PDF...");
    syncButton.disabled = true;

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("deck", deckNameInput.value);
    formData.append("model", textModelSelect.value);
    formData.append("romanized", romanizedToggle.checked ? "true" : "false");

    try {
        const response = await fetch("/sync", {
            method: "POST",
            body: formData,
        });
        const data = await response.json();
        if (data.ok) {
            updateProgress(progressNode, "Sync complete!", data.eta_text);
            const processed = data.items_processed !== undefined ? ` (cards processed: ${data.items_processed})` : "";
            setStatus(
                statusLogSync,
                `✅ ${data.message}${processed}\n\n${data.stdout}`
            );
            if (data.stderr) {
                setStatus(statusLogSync, data.stderr, true);
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

async function generateAudio() {
    const deck = audioDeckSelect.value;
    const model = audioModelSelect.value;
    const workers = audioWorkerSelect.value;
    if (!deck || !model) {
        setStatus(statusLogAudio, "Please select a deck and audio model.");
        return;
    }
    if (!workers) {
        setStatus(statusLogAudio, "Please choose worker count.");
        return;
    }

    setStatus(statusLogAudio, `Generating audio for deck "${deck}"...`);
    const progressNode = showProgress(statusLogAudio, "Generating audio...");
    generateAudioButton.disabled = true;

    try {
        const response = await fetch("/generate/audio", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ deck, model, workers: Number(workers) }),
        });
        const data = await response.json();
        if (data.ok) {
            updateProgress(progressNode, "Audio complete!", data.eta_text);
            const processed = data.items_processed !== undefined ? ` (cards processed: ${data.items_processed})` : "";
            setStatus(
                statusLogAudio,
                `✅ ${data.message}${processed}\n\n${data.stdout}${data.stderr ? `\n${data.stderr}` : ""}`
            );
        } else {
            setStatus(
                statusLogAudio,
                `⚠️ ${data.message}\n\n${data.stdout || ""}\n${data.stderr || ""}`
            );
        }
    } catch (error) {
        setStatus(statusLogAudio, `❌ Request failed: ${error}`);
    } finally {
        removeProgress(progressNode);
        updateAudioControls();
    }
}

generateAudioButton.addEventListener("click", generateAudio);

async function generateImages() {
    const deck = imageDeckSelect.value;
    const imageModel = imageModelSelect.value;
    const skipGating = skipGatingToggle.checked;
    const workers = imageWorkerSelect.value;

    if (!deck || !imageModel) {
        setStatus(statusLogImages, "Please select a deck and image model.");
        return;
    }
    if (!workers) {
        setStatus(statusLogImages, "Please choose worker count.");
        return;
    }

    setStatus(statusLogImages, `Generating images for deck "${deck}"...`);
    const progressNode = showProgress(statusLogImages, "Generating images...");
    generateImagesButton.disabled = true;

    const payload = {
        deck,
        image_model: imageModel,
        skip_gating: skipGating,
        workers: Number(workers),
    };

    try {
        const response = await fetch("/generate/images", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (data.ok) {
            updateProgress(progressNode, "Images complete!", data.eta_text);
            const processed = data.items_processed !== undefined ? ` (cards processed: ${data.items_processed})` : "";
            setStatus(
                statusLogImages,
                `✅ ${data.message}${processed}\n\n${data.stdout}${data.stderr ? `\n${data.stderr}` : ""}`
            );
        } else {
            setStatus(
                statusLogImages,
                `⚠️ ${data.message}\n\n${data.stdout || ""}\n${data.stderr || ""}`
            );
        }
    } catch (error) {
        setStatus(statusLogImages, `❌ Request failed: ${error}`);
    } finally {
        removeProgress(progressNode);
        updateImageControls();
    }
}

generateImagesButton.addEventListener("click", generateImages);

refreshDecksAudio.addEventListener("click", loadDecks);
refreshDecksImages.addEventListener("click", loadDecks);

audioDeckSelect.addEventListener("change", updateAudioControls);
audioModelSelect.addEventListener("change", updateAudioControls);
audioWorkerSelect.addEventListener("change", updateAudioControls);

imageDeckSelect.addEventListener("change", updateImageControls);
imageModelSelect.addEventListener("change", updateImageControls);
skipGatingToggle.addEventListener("change", updateImageControls);
imageWorkerSelect.addEventListener("change", updateImageControls);

loadDecks();
loadModels("text", textModelSelect, "gpt-4.1-mini", statusLogSync, updateSyncButton);
loadModels("audio", audioModelSelect, "gpt-4o-mini-tts", statusLogAudio, updateAudioControls);
loadModels("image", imageModelSelect, "gpt-image-1", statusLogImages, updateImageControls);

textModelSelect.addEventListener("change", updateSyncButton);
updateSyncButton();
updateAudioControls();
updateImageControls();
