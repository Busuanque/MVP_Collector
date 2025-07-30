document.addEventListener("DOMContentLoaded", () => {
    const locationLabel = document.getElementById("location-label");
    const instructionLabel = document.getElementById("instruction-label");
    const photoUpload = document.getElementById("photo-upload");
    const uploadButton = document.getElementById("upload-button");
    const cameraButton = document.getElementById("camera-button");
    const captureButton = document.getElementById("capture-button");
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
        instructionLabel.textContent = "Passo 2: Clique em 'Analisar e Obter Dicas'";
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
            instructionLabel.textContent = "Passo 1: Posicione a mão e clique em 'Capturar Foto'";
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
        instructionLabel.textContent = "Passo 2: Clique em 'Analisar e Obter Dicas'";
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
                    instructionLabel.textContent = "Passo 1: Carregue ou capture uma nova foto para analisar novamente";
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
});