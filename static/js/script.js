document.addEventListener('DOMContentLoaded', function() {
    // Botón de actualizar
    document.getElementById('refreshBtn').addEventListener('click', function() {
        refreshImages();
    });
    
    // Botones de rotación
    document.querySelectorAll('.rotate-btn').forEach(button => {
        button.addEventListener('click', function() {
            const filename = this.getAttribute('data-filename');
            const direction = this.getAttribute('data-direction');
            rotateImage(filename, direction);
        });
    });
    
    // Botones de eliminación
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', function() {
            const filename = this.getAttribute('data-filename');
            if (confirm('¿Está seguro de que desea eliminar este documento?')) {
                deleteImage(filename);
            }
        });
    });
    
    // Subida de archivos
    document.getElementById('uploadBtn').addEventListener('click', function() {
        uploadFiles();
    });
    
    // Iniciar monitoreo de cambios en la carpeta
    startFolderMonitoring();
});

// Variable para almacenar la última modificación conocida
let lastKnownModification = 0;

// Función para iniciar el monitoreo de la carpeta
function startFolderMonitoring() {
    // Verificar cambios cada 3 segundos
    setInterval(checkForUpdates, 3000);
}

// Función para verificar si hay actualizaciones
function checkForUpdates() {
    fetch('/check_updates')
        .then(response => response.json())
        .then(data => {
            // Si hay una nueva modificación, actualizar las imágenes
            if (data.last_modified > lastKnownModification) {
                lastKnownModification = data.last_modified;
                console.log('Cambios detectados en la carpeta, actualizando imágenes...');
                refreshImages();
            }
        })
        .catch(error => {
            console.error('Error al verificar actualizaciones:', error);
        });
}

// Función para actualizar las imágenes
function refreshImages() {
    fetch('/refresh')
        .then(response => response.json())
        .then(data => {
            updateImagesUI(data);
        })
        .catch(error => {
            console.error('Error al actualizar imágenes:', error);
        });
}

// Función para rotar una imagen
function rotateImage(filename, direction) {
    fetch(`/rotate/${filename}/${direction}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Añadir un parámetro de tiempo para evitar caché
                const timestamp = new Date().getTime();
                const imgElements = document.querySelectorAll('.document-image');
                imgElements.forEach(img => {
                    if (img.alt === filename) {
                        const currentSrc = img.src.split('?')[0];
                        img.src = `${currentSrc}?t=${timestamp}`;
                    }
                });
            } else {
                alert('Error al rotar la imagen: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error al rotar la imagen:', error);
        });
}

// Función para eliminar una imagen
function deleteImage(filename) {
    fetch(`/delete/${filename}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                refreshImages();
            } else {
                alert('Error al eliminar la imagen: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error al eliminar la imagen:', error);
        });
}

// Función para subir archivos
function uploadFiles() {
    const fileInput = document.getElementById('fileInput');
    const files = fileInput.files;
    
    if (files.length === 0) {
        showUploadStatus('Por favor, seleccione al menos un archivo', 'danger');
        return;
    }
    
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('file', files[i]);
    }
    
    // Mostrar barra de progreso
    const progressBar = document.querySelector('#uploadProgress .progress-bar');
    document.getElementById('uploadProgress').classList.remove('d-none');
    progressBar.style.width = '0%';
    
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showUploadStatus(`${data.files.length} archivo(s) subido(s) correctamente`, 'success');
            document.getElementById('uploadForm').reset();
            setTimeout(() => {
                refreshImages();
                // Cerrar modal después de 1 segundo
                setTimeout(() => {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
                    modal.hide();
                    // Ocultar mensajes y barra de progreso
                    document.getElementById('uploadStatus').classList.add('d-none');
                    document.getElementById('uploadProgress').classList.add('d-none');
                }, 1000);
            }, 500);
        } else {
            showUploadStatus('Error: ' + data.error, 'danger');
        }
    })
    .catch(error => {
        console.error('Error al subir archivos:', error);
        showUploadStatus('Error al subir archivos', 'danger');
    });
    
    // Simular progreso (en una aplicación real, usaría XMLHttpRequest con eventos de progreso)
    let progress = 0;
    const interval = setInterval(() => {
        progress += 10;
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
        
        if (progress >= 100) {
            clearInterval(interval);
        }
    }, 200);
}

// Función para mostrar el estado de la subida
function showUploadStatus(message, type) {
    const statusElement = document.getElementById('uploadStatus');
    statusElement.textContent = message;
    statusElement.className = `alert alert-${type}`;
    statusElement.classList.remove('d-none');
}

// Función para actualizar la interfaz con las nuevas imágenes
function updateImagesUI(imagesData) {
    const documentCards = document.querySelectorAll('.document-card');
    
    imagesData.forEach((image, index) => {
        if (index < documentCards.length) {
            const card = documentCards[index];
            
            // Actualizar título
            card.querySelector('.card-title').textContent = image.name;
            
            // Actualizar botones
            const buttons = card.querySelectorAll('button');
            buttons.forEach(button => {
                button.setAttribute('data-filename', image.name);
                button.disabled = !image.path;
            });
            
            // Actualizar imagen
            const cardBody = card.querySelector('.card-body');
            if (image.data) {
                // Si hay una imagen
                if (cardBody.querySelector('.document-image')) {
                    // Actualizar imagen existente
                    cardBody.querySelector('.document-image').src = image.data;
                    cardBody.querySelector('.document-image').alt = image.name;
                } else {
                    // Crear nueva imagen
                    cardBody.innerHTML = `<img src="${image.data}" class="img-fluid document-image" alt="${image.name}">`;
                }
            } else {
                // Si no hay imagen
                cardBody.innerHTML = `
                <div class="no-document">
                    <i class="fas fa-file-image fa-5x text-muted"></i>
                    <p class="mt-3">No hay documento disponible</p>
                </div>`;
            }
            
            // Actualizar fecha de modificación
            card.querySelector('.card-footer small').textContent = 'Modificado: ' + image.modified;
        }
    });
}