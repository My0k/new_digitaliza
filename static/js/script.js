document.addEventListener('DOMContentLoaded', function() {
    // Botón de actualizar
    document.getElementById('refreshBtn').addEventListener('click', function() {
        refreshImages();
    });
    
    // Botón de escanear
    document.getElementById('scanBtn').addEventListener('click', function() {
        scanDocuments();
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
    
    // Botón de intercambio de documentos
    document.getElementById('swapDocsBtn').addEventListener('click', function() {
        swapDocuments();
    });
    
    // Subida de archivos
    document.getElementById('uploadBtn').addEventListener('click', function() {
        uploadFiles();
    });
    
    // Iniciar monitoreo de cambios en la carpeta
    startFolderMonitoring();
    
    // Inicializar zoom en imágenes
    initializeZoom();
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

// Función para intercambiar documentos
function swapDocuments() {
    const container = document.getElementById('documents-container');
    const cards = container.querySelectorAll('.document-card');
    
    if (cards.length === 2) {
        // Intercambiar el contenido de las tarjetas
        const firstCard = cards[0];
        const secondCard = cards[1];
        
        // Intercambiar clases y atributos de tipo de documento
        const firstType = firstCard.getAttribute('data-doc-type');
        const secondType = secondCard.getAttribute('data-doc-type');
        
        firstCard.setAttribute('data-doc-type', secondType);
        secondCard.setAttribute('data-doc-type', firstType);
        
        // Intercambiar etiquetas
        const firstLabel = firstCard.querySelector('.doc-type-label');
        const secondLabel = secondCard.querySelector('.doc-type-label');
        
        const tempText = firstLabel.textContent;
        firstLabel.textContent = secondLabel.textContent;
        secondLabel.textContent = tempText;
        
        // Intercambiar colores de encabezado
        const firstHeader = firstCard.querySelector('.card-header');
        const secondHeader = secondCard.querySelector('.card-header');
        
        if (firstHeader.classList.contains('bg-primary')) {
            firstHeader.classList.remove('bg-primary');
            firstHeader.classList.add('bg-success');
            secondHeader.classList.remove('bg-success');
            secondHeader.classList.add('bg-primary');
        } else {
            firstHeader.classList.remove('bg-success');
            firstHeader.classList.add('bg-primary');
            secondHeader.classList.remove('bg-primary');
            secondHeader.classList.add('bg-success');
        }
        
        console.log('Documentos intercambiados');
    }
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
            
            // Actualizar nombre de archivo (manteniendo la etiqueta de tipo)
            card.querySelector('.doc-filename').textContent = image.name;
            
            // Actualizar botones
            const buttons = card.querySelectorAll('button');
            buttons.forEach(button => {
                if (button.classList.contains('rotate-btn') || button.classList.contains('delete-btn')) {
                    button.setAttribute('data-filename', image.name);
                    button.disabled = !image.path;
                }
            });
            
            // Actualizar imagen
            const cardBody = card.querySelector('.card-body');
            const hadImage = cardBody.querySelector('.document-image') !== null;
            
            if (image.data) {
                // Si hay una imagen
                if (hadImage) {
                    // Actualizar imagen existente
                    cardBody.querySelector('.document-image').src = image.data;
                    cardBody.querySelector('.document-image').alt = image.name;
                } else {
                    // Crear nueva imagen
                    cardBody.innerHTML = `<img src="${image.data}" class="img-fluid document-image" alt="${image.name}">`;
                    
                    // Reinicializar zoom para esta imagen
                    const container = cardBody.closest('.document-container');
                    if (container && !container.querySelector('.zoom-controls')) {
                        // Si no hay controles de zoom, inicializar
                        initializeZoom();
                    }
                }
            } else {
                // Si no hay imagen
                cardBody.innerHTML = `
                <div class="no-document">
                    <i class="fas fa-file-image fa-5x text-muted"></i>
                    <p class="mt-3">No hay documento disponible</p>
                </div>`;
                
                // Eliminar controles de zoom si existen
                const container = cardBody.closest('.document-container');
                const zoomControls = container.querySelector('.zoom-controls');
                if (zoomControls) {
                    zoomControls.remove();
                }
            }
            
            // Actualizar fecha de modificación
            card.querySelector('.card-footer small').textContent = 'Modificado: ' + image.modified;
        }
    });
}

// Función para inicializar el zoom en las imágenes
function initializeZoom() {
    // Añadir controles de zoom a cada contenedor de documento
    document.querySelectorAll('.document-container').forEach(container => {
        // Crear controles de zoom
        const zoomControls = document.createElement('div');
        zoomControls.className = 'zoom-controls';
        zoomControls.innerHTML = `
            <button class="zoom-out-btn"><i class="fas fa-search-minus"></i></button>
            <span class="zoom-level">100%</span>
            <button class="zoom-in-btn"><i class="fas fa-search-plus"></i></button>
            <button class="zoom-reset-btn"><i class="fas fa-undo"></i></button>
        `;
        container.appendChild(zoomControls);
        
        // Obtener la imagen si existe
        const image = container.querySelector('.document-image');
        if (image) {
            // Inicializar variables de zoom
            let scale = 1;
            let isDragging = false;
            let startX, startY, translateX = 0, translateY = 0;
            
            // Actualizar el nivel de zoom mostrado
            const updateZoomLevel = () => {
                container.querySelector('.zoom-level').textContent = `${Math.round(scale * 100)}%`;
            };
            
            // Aplicar transformación a la imagen
            const applyTransform = () => {
                image.style.transform = `scale(${scale}) translate(${translateX}px, ${translateY}px)`;
                if (scale > 1) {
                    image.classList.add('zoomed');
                } else {
                    image.classList.remove('zoomed');
                    translateX = 0;
                    translateY = 0;
                }
            };
            
            // Evento de rueda del ratón para zoom
            container.addEventListener('wheel', (e) => {
                e.preventDefault();
                const delta = e.deltaY * -0.01;
                const newScale = Math.max(1, Math.min(5, scale + delta));
                
                // Ajustar la posición para hacer zoom hacia el cursor
                if (newScale !== scale) {
                    const rect = image.getBoundingClientRect();
                    const x = (e.clientX - rect.left) / scale;
                    const y = (e.clientY - rect.top) / scale;
                    
                    scale = newScale;
                    updateZoomLevel();
                    applyTransform();
                }
            });
            
            // Eventos para arrastrar la imagen cuando está ampliada
            image.addEventListener('mousedown', (e) => {
                if (scale > 1) {
                    isDragging = true;
                    startX = e.clientX - translateX;
                    startY = e.clientY - translateY;
                    image.style.cursor = 'grabbing';
                }
            });
            
            document.addEventListener('mousemove', (e) => {
                if (isDragging) {
                    translateX = e.clientX - startX;
                    translateY = e.clientY - startY;
                    applyTransform();
                }
            });
            
            document.addEventListener('mouseup', () => {
                if (isDragging) {
                    isDragging = false;
                    image.style.cursor = 'move';
                }
            });
            
            // Botones de control de zoom
            container.querySelector('.zoom-in-btn').addEventListener('click', () => {
                scale = Math.min(5, scale + 0.25);
                updateZoomLevel();
                applyTransform();
            });
            
            container.querySelector('.zoom-out-btn').addEventListener('click', () => {
                scale = Math.max(1, scale - 0.25);
                updateZoomLevel();
                applyTransform();
            });
            
            container.querySelector('.zoom-reset-btn').addEventListener('click', () => {
                scale = 1;
                translateX = 0;
                translateY = 0;
                updateZoomLevel();
                applyTransform();
            });
        }
    });
}

// Función para ejecutar el escaneo (llamar a gen_test_input.py)
function scanDocuments() {
    // Mostrar indicador de carga
    const scanBtn = document.getElementById('scanBtn');
    const originalText = scanBtn.innerHTML;
    scanBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Escaneando...';
    scanBtn.disabled = true;
    
    // Llamar al endpoint que ejecutará el script
    fetch('/scan')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Mostrar mensaje de éxito
                alert('Documentos escaneados correctamente');
                // Actualizar las imágenes
                refreshImages();
            } else {
                alert('Error al escanear documentos: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error al escanear:', error);
            alert('Error al escanear documentos');
        })
        .finally(() => {
            // Restaurar el botón
            scanBtn.innerHTML = originalText;
            scanBtn.disabled = false;
        });
}