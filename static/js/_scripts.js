document.addEventListener("DOMContentLoaded", () => {
    const locationLabel = document.getElementById("location-label");
    //const instructionLabel = document.getElementById("instruction-label");
    const photoUpload = document.getElementById("photo-upload");
    const uploadButton = document.getElementById("upload-button");
    const cameraButton = document.getElementById("camera-button");
    const captureButton = document.getElementById("capture-button");
    const exportButton = document.getElementById("export-button");
    const cameraFeed = document.getElementById("camera-feed");
    const analyzeButton = document.getElementById("analyze-button");
    const spinner = document.getElementById("spinner");
    const resultLabel = document.getElementById("result-label");
    const statusLabel = document.getElementById("status-label");
    let photoPath = null;
    let stream = null;

    // Detect location on page load
    axios.get("/detect_location")
        .then(response => {
            if (response.data.status === "success") {
                locationLabel.textContent = `Localização: ${response.data.location}`;
                statusLabel.textContent = response.data.message;
                statusLabel.style.color = response.data.message_color;
                window.locationData = response.data.location;
            } else {
                locationLabel.textContent = response.data.location;
                statusLabel.textContent = response.data.message;
                statusLabel.style.color = response.data.message_color;
                alert(response.data.message);
            }
        })
        .catch(error => {
            statusLabel.textContent = "Erro ao detetar localização.";
            statusLabel.style.color = "#FF0000";
            alert("Erro ao detetar localização: " + error.message);
        });

    // Handle file upload
    uploadButton.addEventListener("click", () => {
        if (!photoUpload.files.length) {
            statusLabel.textContent = "Nenhuma foto selecionada.";
            statusLabel.style.color = "#FF0000";
            alert("Por favor, selecione uma foto.");
            return;
        }
        const formData = new FormData();
        formData.append("photo", photoUpload.files[0]);
        //instructionLabel.textContent = "Passo 2: Clique em 'Analisar e Obter Dicas'";
        axios.post("/upload_photo", formData)
            .then(response => {
                statusLabel.textContent = response.data.message;
                statusLabel.style.color = response.data.message_color;
                if (response.data.status === "success") {
                    photoPath = response.data.photo_path;
                    analyzeButton.disabled = false;
                    // Stop camera if active
                    if (stream) {
                        stream.getTracks().forEach(track => track.stop());
                        cameraFeed.classList.add("d-none");
                        captureButton.classList.add("d-none");
                        stream = null;
                    }
                } else {
                    alert(response.data.message);
                }
            })
            .catch(error => {
                statusLabel.textContent = "Erro ao carregar foto.";
                statusLabel.style.color = "#FF0000";
                alert("Erro ao carregar foto: " + error.message);
            });
    });

    // Handle camera access
    cameraButton.addEventListener("click", async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
            cameraFeed.srcObject = stream;
            cameraFeed.classList.remove("d-none");
            captureButton.classList.remove("d-none");
            //instructionLabel.textContent = "Passo 1: Posicione a mão e clique em 'Capturar Foto'";
        } catch (error) {
            statusLabel.textContent = "Erro ao acessar a câmara.";
            statusLabel.style.color = "#FF0000";
            alert("Erro ao acessar a câmara: " + error.message);
        }
    });

    // Handle photo capture
    captureButton.addEventListener("click", () => {
        const canvas = document.createElement("canvas");
        canvas.width = cameraFeed.videoWidth;
        canvas.height = cameraFeed.videoHeight;
        canvas.getContext("2d").drawImage(cameraFeed, 0, 0);
        const photoData = canvas.toDataURL("image/jpeg");
        const formData = new FormData();
        formData.append("photo_data", photoData);
        //instructionLabel.textContent = "Passo 2: Clique em 'Analisar e Obter Dicas'";
        axios.post("/upload_photo", formData)
            .then(response => {
                statusLabel.textContent = response.data.message;
                statusLabel.style.color = response.data.message_color;
                if (response.data.status === "success") {
                    photoPath = response.data.photo_path;
                    analyzeButton.disabled = false;
                    // Stop camera
                    if (stream) {
                        stream.getTracks().forEach(track => track.stop());
                        cameraFeed.classList.add("d-none");
                        captureButton.classList.add("d-none");
                        stream = null;
                    }
                } else {
                    alert(response.data.message);
                }
            })
            .catch(error => {
                statusLabel.textContent = "Erro ao capturar foto.";
                statusLabel.style.color = "#FF0000";
                alert("Erro ao capturar foto: " + error.message);
            });
    });

    // Handle analysis
    analyzeButton.addEventListener("click", () => {


        if (!window.locationData || !photoPath) {
            statusLabel.textContent = "Localização ou foto não disponível.";
            statusLabel.style.color = "#FF0000";
            alert("Localização ou foto não disponível.");
            return;
        }
        spinner.classList.remove("d-none");
        statusLabel.textContent = "A analisar...";
        statusLabel.style.color = "#0080FF";
        axios.post("/analyze", {
            location: window.locationData,
            photo_path: photoPath
        })
            .then(response => {
                spinner.classList.add("d-none");
                statusLabel.textContent = response.data.message;
                statusLabel.style.color = response.data.message_color;
                if (response.data.status === "success") {
                    resultLabel.innerHTML = response.data.result;
                    //instructionLabel.textContent = "Passo 1: Carregue ou capture uma nova foto para analisar novamente";
                    photoUpload.value = "";
                    analyzeButton.disabled = true;
                    photoPath = null;
                } else {
                    alert(response.data.message);
                }
            })
            .catch(error => {
                spinner.classList.add("d-none");
                statusLabel.textContent = "Erro na análise.";
                statusLabel.style.color = "#FF0000";
                alert("Erro na análise: " + error.message);
            });
    });

    exportButton.addEventListener("click", () => {
        alert("Export...");
        return;     
    });

// Funções para exportação e visualização de dados
function viewData() {
    const dataView = document.getElementById('data-view');
    const dataContent = document.getElementById('data-content');
    const dataMessage = document.getElementById('data-message');
    const viewButton = document.querySelector('[onclick="viewData()"]');
    
    // Desabilitar botão durante carregamento
    if (viewButton) {
        viewButton.disabled = true;
        viewButton.textContent = 'A Carregar...';
    }
    
    // Mostrar loading
    dataMessage.innerHTML = '<div class="data-loading">A carregar dados...</div>';
    dataView.style.display = 'block';
    
    // Fazer pedido para obter dados
    fetch('/view_data')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                if (data.data.length === 0) {
                    dataContent.innerHTML = '<p style="text-align: center; padding: 20px; color: #666;">Nenhum registo encontrado.</p>';
                    dataMessage.innerHTML = '';
                    return;
                }
                
                // Criar sumário
                const summary = `
                    <div class="data-summary">
                        <strong>Total de Registos: ${data.total_records}</strong>
                        <br><small>Últimos ${Math.min(data.total_records, 100)} registos apresentados</small>
                    </div>
                `;
                
                // Criar cabeçalho da tabela
                let table = `
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th class="col-id">ID</th>
                                <th class="col-timestamp">Data/Hora</th>
                                <th class="col-image">Imagem</th>
                                <th class="col-location">Localização</th>
                                <th class="col-uv">UV</th>
                                <th class="col-skin">Tipo Pele</th>
                                <th class="col-status">Estado</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                // Adicionar dados à tabela
                data.data.forEach(record => {
                    // Determinar classe CSS para o índice UV
                    let uvClass = 'uv-low';
                    const uvValue = parseFloat(record.uv_index);
                    if (!isNaN(uvValue)) {
                        if (uvValue >= 8) uvClass = 'uv-very-high';
                        else if (uvValue >= 6) uvClass = 'uv-high';
                        else if (uvValue >= 3) uvClass = 'uv-moderate';
                    }
                    
                    table += `
                        <tr>
                            <td class="col-id">${record.id}</td>
                            <td class="col-timestamp">${formatTimestamp(record.timestamp)}</td>
                            <td class="col-image" title="${record.image_name}">${truncateText(record.image_name, 15)}</td>
                            <td class="col-location" title="${record.location}">${truncateText(record.location, 20)}</td>
                            <td class="col-uv ${uvClass}">${record.uv_index}</td>
                            <td class="col-skin" title="${record.fitzpatrick_type}">${truncateText(record.fitzpatrick_type, 25)}</td>
                            <td class="col-status">${getStatusIcon(record.status)}</td>
                        </tr>
                    `;
                });
                
                table += '</tbody></table>';
                
                dataContent.innerHTML = summary + table;
                dataMessage.innerHTML = '<p style="color: #28a745;">✓ Dados carregados com sucesso!</p>';
                
                // Mostrar botão flutuante de exportação
                showExportFab();
                
            } else {
                dataContent.innerHTML = '';
                dataMessage.innerHTML = `<p style="color: #dc3545;">❌ ${data.message}</p>`;
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            dataContent.innerHTML = '';
            dataMessage.innerHTML = '<p style="color: #dc3545;">❌ Erro ao carregar dados. Tente novamente.</p>';
        })
        .finally(() => {
            // Reabilitar botão
            if (viewButton) {
                viewButton.disabled = false;
                viewButton.textContent = 'Ver Dados';
            }
        });
}

function exportData() {
    const dataMessage = document.getElementById('data-message');
    const exportButtons = document.querySelectorAll('[onclick="exportData()"]');
    
    // Desabilitar botões durante exportação
    exportButtons.forEach(btn => {
        btn.disabled = true;
        btn.textContent = 'A Exportar...';
    });
    
    dataMessage.innerHTML = '<p style="color: #007bff;">📥 A preparar exportação...</p>';
    
    // Criar link temporário para download
    const link = document.createElement('a');
    link.href = '/export_data';
    link.download = `analises_pele_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.csv`;
    
    // Adicionar evento para detectar quando o download começar
    let downloadStarted = false;
    
    link.addEventListener('click', () => {
        downloadStarted = true;
        setTimeout(() => {
            if (downloadStarted) {
                dataMessage.innerHTML = '<p style="color: #28a745;">✓ Dados exportados com sucesso!</p>';
                setTimeout(() => {
                    if (dataMessage.innerHTML.includes('exportados com sucesso')) {
                        dataMessage.innerHTML = '';
                    }
                }, 3000);
            }
        }, 1000);
    });
    
    // Executar download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Reabilitar botões
    setTimeout(() => {
        exportButtons.forEach(btn => {
            btn.disabled = false;
            btn.textContent = 'Exportar CSV';
        });
    }, 2000);
}

function clearDataView() {
    const dataView = document.getElementById('data-view');
    const dataContent = document.getElementById('data-content');
    const dataMessage = document.getElementById('data-message');
    
    dataView.style.display = 'none';
    dataContent.innerHTML = '';
    dataMessage.innerHTML = '';
    
    // Ocultar botão flutuante
    hideExportFab();
}

// Funções auxiliares
function formatTimestamp(timestamp) {
    try {
        const date = new Date(timestamp);
        return date.toLocaleString('pt-PT', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return timestamp;
    }
}

function truncateText(text, maxLength) {
    if (!text) return 'N/A';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
}

function getStatusIcon(status) {
    if (!status) return '❓';
    if (status.toLowerCase().includes('sucesso')) return '✅';
    if (status.toLowerCase().includes('erro')) return '❌';
    return '⚠️';
}

function showExportFab() {
    let fab = document.getElementById('export-fab');
    if (!fab) {
        fab = document.createElement('button');
        fab.id = 'export-fab';
        fab.className = 'export-fab';
        fab.innerHTML = '📥';
        fab.title = 'Exportar Dados';
        fab.onclick = exportData;
        document.body.appendChild(fab);
    }
    fab.classList.add('show');
}

function hideExportFab() {
    const fab = document.getElementById('export-fab');
    if (fab) {
        fab.classList.remove('show');
    }
}

// Auto-scroll para a seção de dados quando visualizar
function scrollToDataSection() {
    const dataSection = document.querySelector('.data-section');
    if (dataSection) {
        dataSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Adicionar event listener para detectar quando a seção de dados está visível
document.addEventListener('DOMContentLoaded', function() {
    // Observer para mostrar/ocultar botão flutuante baseado na visibilidade da seção
    const dataSection = document.querySelector('.data-section');
    if (dataSection && 'IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Seção visível - pode mostrar FAB se dados estão carregados
                    const dataView = document.getElementById('data-view');
                    if (dataView && dataView.style.display !== 'none') {
                        showExportFab();
                    }
                } else {
                    // Seção não visível - ocultar FAB
                    hideExportFab();
                }
            });
        });
        
        observer.observe(dataSection);
    }
});
});
