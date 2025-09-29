// scripts.js

document.addEventListener("DOMContentLoaded", () => {
    // Elementos principais
    const locationLabel = document.getElementById("location-label");
    const photoUpload = document.getElementById("photo-upload");
    const uploadButton = document.getElementById("upload-button");
    const cameraButton = document.getElementById("camera-button");
    
    const cameraContainer = document.querySelector(".camera-container");
    const captureButton = document.getElementById("capture-button");
    const cameraFeed = document.getElementById("camera-feed");

    const analyzeButton = document.getElementById("analyze-button");
    const spinner = document.getElementById("spinner");
    const resultLabel = document.getElementById("result-label");
    const dataMessage = document.getElementById("data-message");
    const countEl = document.getElementById("analysis-count");

    let photoPath = null;
    let stream = null;
    let isDialogOpen = false;

    // Função de status
    function showStatus(message, color = "#0080FF") {
        const statusEl = document.getElementById("status-label") || document.getElementById("status");
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.style.color = color;
        }
        console.log("Status:", message);
    }

    // Atualiza contador
    function updateAnalysisCount() {
        if (!countEl) return;
        axios.get("/count_analyses")
            .then(res => {
                if (res.data.status === "success") {
                    countEl.textContent = `Total de análises realizadas: ${res.data.count}`;
                } else {
                    countEl.textContent = "Contador indisponível";
                }
            })
            .catch(() => {
                countEl.textContent = "Erro ao carregar o contador";
            });
    }
    updateAnalysisCount();

    // Detectar localização
    if (locationLabel) {
        axios.get("/detect_location")
            .then(response => {
                const d = response.data;
                if (d.status === "success") {
                    locationLabel.textContent = `Localização: ${d.location}`;
                }
                showStatus(d.message, d.message_color);
                window.locationData = d.location;
            })
            .catch(() => {
                showStatus("Erro ao detectar localização", "#FF0000");
            });
    }

    // Upload de arquivo
    if (uploadButton && photoUpload) {
        // Evita diálogo duplo
        uploadButton.addEventListener("click", e => {
            e.preventDefault();
            e.stopImmediatePropagation();
            if (isDialogOpen) return;
            isDialogOpen = true;
            photoUpload.value = "";
            photoUpload.click();
            setTimeout(() => { isDialogOpen = false; }, 500);
        });

        photoUpload.addEventListener("change", () => {
            isDialogOpen = false;
            if (!photoUpload.files.length) {
                showStatus("Nenhuma foto selecionada", "#FF0000");
                return;
            }
            const formData = new FormData();
            formData.append("photo", photoUpload.files[0]);
            showStatus("A carregar foto...", "#0080FF");

            axios.post("/upload", formData)
                .then(response => {
                    const res = response.data;
                    showStatus(res.message, res.message_color);
                    if (res.status === "success") {
                        photoPath = res.filename;
                        analyzeButton.disabled = false;
                        stopCamera();
                    }
                })
                .catch(error => {
                    console.error("Erro upload:", error);
                    showStatus("Erro ao carregar foto", "#FF0000");
                    alert("Erro ao carregar foto: " + error.message);
                });
        });
    }

    // Acesso à câmera
    if (cameraButton && cameraFeed && captureButton) {
        cameraButton.addEventListener("click", async () => {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
                cameraFeed.srcObject = stream;
                cameraFeed.classList.remove("d-none");
                captureButton.classList.remove("d-none");
                cameraContainer.classList.remove("d-none");
                
                showStatus("Posicione a mão e capture a foto", "#0080FF");
            } catch (err) {
                console.error("Erro câmera:", err);
                showStatus("Erro ao acessar câmera", "#FF0000");
                alert("Erro ao acessar câmera: " + err.message);
            }
        });

        captureButton.addEventListener("click", () => {
            try {
                const canvas = document.createElement("canvas");
                canvas.width = cameraFeed.videoWidth;
                canvas.height = cameraFeed.videoHeight;
                canvas.getContext("2d").drawImage(cameraFeed, 0, 0);
                canvas.toBlob(blob => {
                    const formData = new FormData();
                    formData.append("photo", blob, "captured_photo.jpg");
                    showStatus("A processar foto capturada...", "#0080FF");

                    axios.post("/upload", formData)
                        .then(response => {
                            const res = response.data;
                            showStatus(res.message, res.message_color);
                            if (res.status === "success") {
                                photoPath = res.filename;
                                analyzeButton.disabled = false;
                                stopCamera();
                            }
                        })
                        .catch(error => {
                            console.error("Erro captura:", error);
                            showStatus("Erro ao processar foto", "#FF0000");
                            alert("Erro ao capturar foto: " + error.message);
                        });
                }, "image/jpeg", 0.8);
            } catch (err) {
                console.error("Erro captura canvas:", err);
                showStatus("Erro na captura", "#FF0000");
            }
        });
    }

    // Para câmera
    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(t => t.stop());
            stream = null;
        }
        if (cameraFeed) cameraFeed.classList.add("d-none");
        if (captureButton) captureButton.classList.add("d-none");
        if (cameraContainer) cameraContainer.classList.add("d-none");
    }

    // Análise
    if (analyzeButton) {
        analyzeButton.addEventListener("click", () => {
            if (!window.locationData) {
                showStatus("Localização não disponível", "#FF0000");
                alert("Localização não detectada.");
                return;
            }
            if (!photoPath) {
                showStatus("Foto não disponível", "#FF0000");
                alert("Por favor, carregue ou capture uma foto primeiro.");
                return;
            }

            if (spinner) spinner.classList.remove("d-none");
            showStatus("A analisar...", "#0080FF");
            analyzeButton.disabled = true;
            analyzeButton.textContent = "🔄 Analisando...";

            axios.post("/analyze", { filename: photoPath })
                .then(response => {
                    const res = response.data;
                    if (spinner) spinner.classList.add("d-none");
                    showStatus(res.message, res.message_color);

                    if (res.status === "success" && resultLabel) {
                        resultLabel.innerHTML = res.result_html;
                        updateAnalysisCount();
                        photoUpload.value = "";
                        photoPath = null;
                        analyzeButton.textContent = "🔍 Analisar e Obter Dicas";
                        analyzeButton.disabled = true;
                    } else {
                        alert("Erro na análise: " + res.message);
                        analyzeButton.disabled = false;
                        analyzeButton.textContent = "🔍 Analisar e Obter Dicas";
                    }

                })
                .catch(error => {
                    console.error("Erro análise:", error);
                    if (spinner) spinner.classList.add("d-none");
                    showStatus("Erro na análise", "#FF0000");
                    analyzeButton.disabled = false;
                    analyzeButton.textContent = "🔍 Analisar e Obter Dicas";
                    alert("Erro na análise: " + (error.response?.data?.message || error.message));
                });
        });
    } else {
        console.error("Botão analyze-button não encontrado!");
    }

    // Export CSV
    window.exportData = function() {
        if (dataMessage) dataMessage.innerHTML = '📥 Preparando exportação CSV...';
        const link = document.createElement("a");
        link.href = '/export';
        link.download = `analises_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => { if (dataMessage) dataMessage.innerHTML = ''; }, 2000);
    };

    // Export MySQL
    window.exportDb = async function() {
        const msgEl = document.getElementById("data-message");
        if (msgEl) msgEl.textContent = '💾 Exportando para MySQL...';

        try {
            const response = await axios.post('/export_db', {});
            const res = response.data;
            if (msgEl) {
                if (res.status === "success") {
                    msgEl.textContent = `✓ ${res.quantidade} registro(s) salvos no MySQL!`;
                } else {
                    msgEl.textContent = `⚠️ ${res.message}`;
                }
            }
            // Atualizar contador de análises se necessário
            updateAnalysisCount();
        } catch (error) {
            console.error("Erro exportDb:", error);
            if (msgEl) msgEl.textContent = `❌ Erro: ${error.message}`;
        }

        // Limpar mensagem após 1s
        setTimeout(() => {
            if (msgEl) msgEl.textContent = "";
        }, 1000);
    };



});
