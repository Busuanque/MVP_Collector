// Declara updateAnalysisCount no escopo global
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
    .catch(() => {
      countEl.textContent = "Erro ao carregar o contador.";
    });
};


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

    const dataView    = document.getElementById('data-view');
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
        console.log("Status:", message);
    }

    // Inicializa o contador
    //updateAnalysisCount();

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

    // Quando o usuário seleciona o arquivo, dispara o upload
    photoUpload.addEventListener("change", () => {
        if (!photoUpload.files.length) {
        showStatus("Nenhuma foto selecionada", "#FF0000");
        return;
        }

        const formData = new FormData();
        formData.append("photo", photoUpload.files[0]);
        showStatus("A carregar foto...", "#0080FF");

        axios.post("/upload_photo", formData)
        .then(response => {
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
            showStatus("Erro ao carregar foto", "#FF0000");
            console.error("Erro upload:", error);
            alert("Erro ao carregar foto: " + error.message);
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

    // Captura de foto
    if (captureButton && cameraFeed) {
        captureButton.addEventListener("click", () => {
            try {
                const canvas = document.createElement("canvas");
                canvas.width = cameraFeed.videoWidth;
                canvas.height = cameraFeed.videoHeight;
                canvas.getContext("2d").drawImage(cameraFeed, 0, 0);
                const photoData = canvas.toDataURL("image/jpeg");
                
                const formData = new FormData();
                formData.append("photo_data", photoData);
                showStatus("A processar foto capturada...", "#0080FF");
                
                axios.post("/upload_photo", formData)
                    .then(response => {
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
                        showStatus("Erro ao processar foto", "#FF0000");
                        console.error("Erro captura:", error);
                        alert("Erro ao capturar foto: " + error.message);
                    });
            } catch (error) {
                showStatus("Erro na captura", "#FF0000");
                console.error("Erro captura canvas:", error);
            }
        });
    }

    // ANÁLISE - Botão principal que não estava funcionando
    if (analyzeButton) {
        analyzeButton.addEventListener("click", () => {
            console.log("Botão analisar clicado!");
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
                    console.log("Resposta análise:", response.data);
                    
                    if (spinner) {
                        spinner.classList.add("d-none");
                    }
                    
                    showStatus(response.data.message, response.data.message_color);
                    
                    if (response.data.status === "success") {
                        if (resultLabel) {
                            //resultLabel.innerHTML = response.data.result;

                            let resultText = response.data.result;
                            // Tratamento de UV fallback
                            const uvLine = resultText.split("\\n").find(line => line.includes("Índice UV:"));
                            if (uvLine && uvLine.includes("-1.0")) {
                            resultText = resultText.replace(uvLine, "**Índice UV:** indisponível  ");
                            }
                            document.getElementById("result-label").innerHTML = resultText;                            
                        }
                        
                        // Atualiza contador de análises
                        window.updateAnalysisCount();

                        // Reset para nova análise
                        if (photoUpload) {
                            photoUpload.value = "";
                        }
                        photoPath = null;
                        analyzeButton.textContent = "🔍 Analisar e Obter Dicas";
                        // Manter botão desabilitado até nova foto
                    } else {
                        alert("Erro na análise: " + response.data.message);
                        analyzeButton.disabled = false;
                        analyzeButton.textContent = "🔍 Analisar e Obter Dicas";
                    }
                })
                .catch(error => {
                    console.error("Erro análise:", error);
                    
                    if (spinner) {
                        spinner.classList.add("d-none");
                    }
                    
                    showStatus("Erro na análise", "#FF0000");
                    analyzeButton.disabled = false;
                    analyzeButton.textContent = "🔍 Analisar e Obter Dicas";
                    
                    let errorMsg = "Erro desconhecido";
                    if (error.response) {
                        errorMsg = error.response.data?.message || "Erro do servidor";
                    } else if (error.request) {
                        errorMsg = "Sem resposta do servidor";
                    } else {
                        errorMsg = error.message;
                    }
                    
                    alert("Erro na análise: " + errorMsg);
                });
            // Atualiza o contador
            //updateAnalysisCount();
        });
    } else {
        console.error("Botão analyze-button não encontrado!");
    }

    window.exportData = function() {
        const dataMessage = document.getElementById('data-message');
        if (dataMessage) {
            dataMessage.innerHTML = '<p style="color: #007bff;">📥 A preparar exportação...</p>';
        }
        
        // Criar link para download
        const link = document.createElement('a');
        link.href = '/export_data';
        link.download = `analises_pele_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        setTimeout(() => {
            if (dataMessage) {
                dataMessage.innerHTML = '<p style="color: #28a745;">✓ Download iniciado!</p>';
                setTimeout(() => {
                    dataMessage.innerHTML = '';
                }, 3000);
            }
        }, 1000);
    };

    window.clearDataView = function() {
        const dataView = document.getElementById('data-view');
        const dataContent = document.getElementById('data-content');
        const dataMessage = document.getElementById('data-message');
        
        if (dataView) dataView.style.display = 'none';
        if (dataContent) dataContent.innerHTML = '';
        if (dataMessage) dataMessage.innerHTML = '';
    };

    // Debug info
    console.log("Script carregado com sucesso!");
    console.log("Elementos encontrados:", {
        locationLabel: !!locationLabel,
        photoUpload: !!photoUpload,
        uploadButton: !!uploadButton,
        cameraButton: !!cameraButton,
        captureButton: !!captureButton,
        cameraFeed: !!cameraFeed,
        analyzeButton: !!analyzeButton,
        spinner: !!spinner,
        resultLabel: !!resultLabel,
        statusLabel: !!statusLabel
    });

    // Nova função: Chama POST para /save_to_db
async function saveToDb() {
    try {
        const response = await fetch('/save_to_db', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})  // Corpo vazio, ou passe dados se precisar
        });

        if (response.ok) {
            const result = await response.json();
            alert(`Sucesso! ${result.quantidade || 1} análises salvas no DB.`);
            console.log('Resposta do DB:', result);
        } else {
            alert('Erro ao salvar no DB. Verifique console.');
        }
    } catch (error) {
        console.error('Erro na chamada:', error);
        alert('Falha na conexão com o servidor.');
    }
}
});