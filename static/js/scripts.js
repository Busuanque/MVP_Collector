// ===== FUNÇÕES GLOBAIS DE EXPORT =====
// Função para exportar CSV (ajustado para /export - padrão backend)
window.exportData = function() {
    const dataMessage = document.getElementById('data-message');
    if (dataMessage) {
        dataMessage.innerHTML = '<p style="color: #007bff;">📥 A preparar exportação CSV...</p>';
    }
    
    // Criar link para download - AJUSTE: URL para /export
    const link = document.createElement('a');
    link.href = '/export';  // Mude para '/export_data' se backend for isso
    link.download = `analises_pele_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    setTimeout(() => {
        if (dataMessage) {
            dataMessage.innerHTML = '<p style="color: #28a745;">✓ CSV gerado e baixado!</p>';
            setTimeout(() => {
                dataMessage.innerHTML = '';
            }, 3000);
        }
    }, 1000);
};

// Função para exportar para MySQL (ajustado com melhor error handling)
window.exportDb = async function() {
    const dataMessage = document.getElementById('data-message');
    if (dataMessage) {
        dataMessage.innerHTML = '<p style="color: #007bff;">💾 A exportar para MySQL...</p>';
    }
    
    try {
        const response = await fetch('/export_db', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        });

        if (response.ok) {
            const result = await response.json();
            if (dataMessage) {
                dataMessage.innerHTML = `<p style="color: #28a745;">✓ ${result.quantidade || 'Registros'} salvos no MySQL!</p>`;
            }
            console.log('Resposta MySQL:', result);
            window.updateAnalysisCount();  // Atualiza contador
            
            if (result.erros && result.erros.length > 0) {
                console.warn('Erros encontrados:', result.erros);
            }
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);  // Lança erro para catch
        }
    } catch (error) {
        console.error('Erro na chamada MySQL:', error);
        if (dataMessage) {
            dataMessage.innerHTML = `<p style="color: #dc3545;">❌ Erro: ${error.message}</p>`;
        }
    }
    
    setTimeout(() => {
        if (dataMessage && dataMessage.innerHTML.includes('salvos')) {
            dataMessage.innerHTML = '';
        }
    }, 5000);
};

// Declara updateAnalysisCount no escopo global (ajustado com error handling)
window.updateAnalysisCount = function() {
    const countEl = document.getElementById("analysis-count");
    if (!countEl) return;
    
    axios.get("/count_analyses")
        .then(res => {
            if (res.data.status === "success") {
                countEl.textContent = `Total de análises realizadas: ${res.data.count}`;
            } else {
                countEl.textContent = "Não foi possível carregar o contador.";
            }
        })
        .catch(err => {
            console.error('Erro no contador:', err);
            countEl.textContent = "Erro ao carregar o contador.";
        });
};

// ===== RESTO DO CÓDIGO =====
document.addEventListener("DOMContentLoaded", () => {
    // Elementos principais - com verificação de existência
    const locationLabel = document.getElementById("location-label");
    const photoUpload = document.getElementById("photo-upload");
    const uploadButton = document.getElementById("upload-button");
    const cameraButton = document.getElementById("camera-button");
    const captureButton = document.getElementById("capture-button");
    const cameraFeed = document.getElementById("camera-feed");
    const analyzeButton = document.getElementById("analyze-button");
    const spinner = document.getElementById("spinner");
    const resultLabel = document.getElementById("result-label");

    const dataView = document.getElementById('data-view');
    const dataContent = document.getElementById('data-content');
    const dataMessage = document.getElementById('data-message');

    // Status pode ser 'status' ou 'status-label' - verificar ambos
    const statusLabel = document.getElementById("status-label") || document.getElementById("status");
    
    // Variáveis de controle
    let photoPath = null;
    let stream = null;

    // Função para mostrar status
    function showStatus(message, color = "#0080FF") {
        if (statusLabel) {
            statusLabel.textContent = message;
            statusLabel.style.color = color;
        }
        console.log("Status:", message);  // Log para debug
    }

    // Inicializa o contador (descomentado)
    window.updateAnalysisCount();

    // Detectar localização na inicialização
    if (locationLabel) {
        axios.get("/detect_location")
            .then(response => {
                if (response.data.status === "success") {
                    locationLabel.textContent = `Localização: ${response.data.location}`;
                    showStatus(response.data.message, response.data.message_color);
                    window.locationData = response.data.location;
                } else {
                    locationLabel.textContent = response.data.location;
                    showStatus(response.data.message, response.data.message_color);
                }
            })
            .catch(error => {
                locationLabel.textContent = "Erro na localização";
                showStatus("Erro ao detectar localização", "#FF0000");
                console.error("Erro localização:", error);
            });
    }

    // Upload de ficheiro: primeiro abre o seletor, depois processa a seleção
    if (uploadButton && photoUpload) {
        uploadButton.addEventListener("click", () => {
            // Abre o diálogo de seleção de arquivos
            photoUpload.click();
        });

        // Quando o usuário seleciona o arquivo, dispara o upload - AJUSTE: URL para '/upload' (mude para '/upload_photo' se backend for isso)
        photoUpload.addEventListener("change", () => {
            if (!photoUpload.files.length) {
                showStatus("Nenhuma foto selecionada", "#FF0000");
                return;
            }

            const formData = new FormData();
            formData.append("photo", photoUpload.files[0]);
            showStatus("A carregar foto...", "#0080FF");

            // AJUSTE: URL corrigida para matching backend; adicionei log e handling para 404
            axios.post("/upload", formData)  // Mude para "/upload_photo" se necessário
                .then(response => {
                    console.log("Upload success:", response.data);  // Log para debug
                    showStatus(response.data.message, response.data.message_color);
                    if (response.data.status === "success") {
                        photoPath = response.data.photo_path;
                        if (analyzeButton) analyzeButton.disabled = false;
                        stopCamera();
                    } else {
                        alert(response.data.message);
                    }
                })
                .catch(error => {
                    console.error("Erro upload:", error);  // Log detalhado
                    let errorMsg = "Erro desconhecido";
                    if (error.response) {
                        errorMsg = `HTTP ${error.response.status}: ${error.response.data?.message || error.response.statusText}`;
                        if (error.response.status === 404) {
                            errorMsg += " (Verifique se a rota /upload existe no backend)";
                        }
                    } else if (error.request) {
                        errorMsg = "Sem resposta do servidor";
                    } else {
                        errorMsg = error.message;
                    }
                    showStatus("Erro ao carregar foto", "#FF0000");
                    alert("Erro ao carregar foto: " + errorMsg);
                });
        });
    }

    // Função para parar câmera
    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
        if (cameraFeed) {
            cameraFeed.classList.add("d-none");
        }
        if (captureButton) {
            captureButton.classList.add("d-none");
        }
    }

    // Acesso à câmera
    if (cameraButton) {
        cameraButton.addEventListener("click", async () => {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { facingMode: "environment" } 
                });
                if (cameraFeed) {
                    cameraFeed.srcObject = stream;
                    cameraFeed.classList.remove("d-none");
                }
                if (captureButton) {
                    captureButton.classList.remove("d-none");
                }
                showStatus("Posicione a mão e capture a foto", "#0080FF");
            } catch (error) {
                showStatus("Erro ao acessar câmera", "#FF0000");
                console.error("Erro câmera:", error);
                alert("Erro ao acessar câmera: " + error.message);
            }
        });
    }

    // Captura de foto - AJUSTE: Mesma URL corrigida para upload
    if (captureButton && cameraFeed) {
        captureButton.addEventListener("click", () => {
            try {
                const canvas = document.createElement("canvas");
                canvas.width = cameraFeed.videoWidth;
                canvas.height = cameraFeed.videoHeight;
                canvas.getContext("2d").drawImage(cameraFeed, 0, 0);
                const photoData = canvas.toDataURL("image/jpeg");
                
                const formData = new FormData();
                formData.append("photo_data", photoData);  // Para backend processar dataURL
                showStatus("A processar foto capturada...", "#0080FF");
                
                // AJUSTE: URL corrigida
                axios.post("/upload", formData)  // Mude para "/upload_photo" se necessário
                    .then(response => {
                        console.log("Capture upload success:", response.data);
                        showStatus(response.data.message, response.data.message_color);
                        if (response.data.status === "success") {
                            photoPath = response.data.photo_path;
                            if (analyzeButton) {
                                analyzeButton.disabled = false;
                            }
                            stopCamera();
                        } else {
                            alert(response.data.message);
                        }
                    })
                    .catch(error => {
                        console.error("Erro captura:", error);
                        let errorMsg = "Erro desconhecido";
                        if (error.response && error.response.status === 404) {
                            errorMsg = "Rota não encontrada – verifique backend";
                        } else if (error.response) {
                            errorMsg = error.response.data?.message || error.response.statusText;
                        } else {
                            errorMsg = error.message;
                        }
                        showStatus("Erro ao processar foto", "#FF0000");
                        alert("Erro ao capturar foto: " + errorMsg);
                    });
            } catch (error) {
                showStatus("Erro na captura", "#FF0000");
                console.error("Erro captura canvas:", error);
            }
        });
    }

    // ANÁLISE - Botão principal (ajustado com logs extras)
    if (analyzeButton) {
        analyzeButton.addEventListener("click", () => {
            console.log("Botão analisar clicado!");  // Log para debug
            console.log("locationData:", window.locationData);
            console.log("photoPath:", photoPath);

            // Verificações
            if (!window.locationData) {
                showStatus("Localização não disponível", "#FF0000");
                alert("Localização não detectada. Tente atualizar a página.");
                return;
            }
            
            if (!photoPath) {
                showStatus("Foto não disponível", "#FF0000");
                alert("Por favor, carregue ou capture uma foto primeiro.");
                return;
            }

            // Mostrar loading
            if (spinner) {
                spinner.classList.remove("d-none");
            }
            showStatus("A analisar...", "#0080FF");
            analyzeButton.disabled = true;
            analyzeButton.textContent = "🔄 Analisando...";

            // Fazer análise
            axios.post("/analyze", {
                location: window.locationData,
                photo_path: photoPath
            })
                .then(response => {
                    console.log("Resposta análise:", response.data);  // Log para debug
                    
                    if (spinner) {
                        spinner.classList.add("d-none");
                    }
                    
                    showStatus(response.data.message, response.data.message_color);
                    
                    if (response.data.status === "success") {
                        if (resultLabel) {
                            let resultText = response.data.result;
                            // Tratamento de UV fallback
                            const uvLine = resultText.split("\\n").find(line => line.includes("Índice UV:"));
                            if (uvLine && uvLine.includes("-1.0")) {
                                resultText = resultText.replace(uvLine, "**Índice UV:** indisponível  ");
                            }
                            resultLabel.innerHTML = resultText;                            
                        }
                        
                        // Atualiza contador de análises
                        window.updateAnalysisCount();

                        // Reset para nova análise
                        if (photoUpload) {
                            photoUpload.value = "";
                        }
                        photoPath = null;
                        analyzeButton.textContent = "🔍 Analisar e Obter Dicas";
                        // Manter botão desabilitado até nova foto? Não, reabilite
                        analyzeButton.disabled = true;  // Ou false se quiser
                    } else {
                        alert("Erro na análise: " + response.data.message);
                        analyzeButton.disabled = false;
                        analyzeButton.textContent = "🔍 Analisar e Obter Dicas";
                    }
                })
                .catch(error => {
                    console.error("Erro análise:", error);  // Log detalhado
                    
                    if (spinner) {
                        spinner.classList.add("d-none");
                    }
                    
                    showStatus("Erro na análise", "#FF0000");
                    analyzeButton.disabled = false;
                    analyzeButton.textContent = "🔍 Analisar e Obter Dicas";
                    
                    let errorMsg = "Erro desconhecido";
                    if (error.response) {
                        errorMsg = error.response.data?.message || `HTTP ${error.response.status}`;
                        if (error.response.status === 404) {
                            errorMsg += " (Verifique se a rota /analyze existe no backend)";
                        }
                    } else if (error.request) {
                        errorMsg = "Sem resposta do servidor";
                    } else {
                        errorMsg = error.message;
                    }
                    
                    alert("Erro na análise: " + errorMsg);
                });
        });
    } else {
        console.error("Botão analyze-button não encontrado!");
    }
});