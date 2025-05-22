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
    
    // Botón de procesar documento
    document.getElementById('processBtn').addEventListener('click', function() {
        processDocument();
    });
    
    // Botón de OCR
    document.getElementById('ocrBtn').addEventListener('click', function() {
        runOCR();
    });
    
    // Iniciar monitoreo de cambios en la carpeta
    startFolderMonitoring();
    
    // Inicializar zoom en imágenes
    initializeZoom();

    // Añadir evento para el botón de Nueva Digitalización
    document.getElementById('newDigitalizationBtn').addEventListener('click', function() {
        newDigitalization();
    });
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
                    const container = cardBody;
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
                const container = cardBody;
                const zoomControls = container.querySelector('.zoom-controls');
                if (zoomControls) {
                    zoomControls.remove();
                }
                const dragIndicator = container.querySelector('.drag-indicator');
                if (dragIndicator) {
                    dragIndicator.remove();
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
        // Limpiar controles existentes si los hay
        const existingControls = container.querySelector('.zoom-controls');
        if (existingControls) {
            existingControls.remove();
        }
        
        // Crear controles de zoom
        const zoomControls = document.createElement('div');
        zoomControls.className = 'zoom-controls';
        zoomControls.innerHTML = `
            <button class="zoom-out-btn" title="Reducir"><i class="fas fa-search-minus"></i></button>
            <span class="zoom-level">100%</span>
            <button class="zoom-in-btn" title="Ampliar"><i class="fas fa-search-plus"></i></button>
            <button class="zoom-reset-btn" title="Restablecer"><i class="fas fa-undo"></i></button>
        `;
        container.appendChild(zoomControls);
        
        // Añadir indicador de arrastre
        const dragIndicator = document.createElement('div');
        dragIndicator.className = 'drag-indicator';
        dragIndicator.textContent = 'Arrastra para mover • Rueda para zoom';
        container.appendChild(dragIndicator);
        
        // Ocultar el indicador después de 3 segundos
        setTimeout(() => {
            dragIndicator.classList.add('fade');
        }, 3000);
        
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
                    
                    // Mostrar el indicador brevemente al hacer zoom
                    dragIndicator.classList.remove('fade');
                    dragIndicator.textContent = `Zoom: ${Math.round(scale * 100)}%`;
                    setTimeout(() => {
                        dragIndicator.classList.add('fade');
                    }, 1500);
                }
            });
            
            // Eventos para arrastrar la imagen
            image.addEventListener('mousedown', (e) => {
                e.preventDefault(); // Prevenir selección de texto
                isDragging = true;
                startX = e.clientX - translateX * scale;
                startY = e.clientY - translateY * scale;
                image.style.cursor = 'grabbing';
                
                // Mostrar el indicador al comenzar a arrastrar
                if (scale > 1) {
                    dragIndicator.classList.remove('fade');
                    dragIndicator.textContent = 'Arrastrando...';
                }
            });
            
            document.addEventListener('mousemove', (e) => {
                if (isDragging && scale > 1) {
                    translateX = (e.clientX - startX) / scale;
                    translateY = (e.clientY - startY) / scale;
                    
                    // Limitar el arrastre para que la imagen no se salga demasiado
                    const maxTranslate = (scale - 1) * 100;
                    translateX = Math.max(-maxTranslate, Math.min(maxTranslate, translateX));
                    translateY = Math.max(-maxTranslate, Math.min(maxTranslate, translateY));
                    
                    applyTransform();
                }
            });
            
            document.addEventListener('mouseup', () => {
                if (isDragging) {
                    isDragging = false;
                    image.style.cursor = 'grab';
                    
                    // Ocultar el indicador después de arrastrar
                    setTimeout(() => {
                        dragIndicator.classList.add('fade');
                    }, 800);
                }
            });
            
            // Botones de control de zoom
            container.querySelector('.zoom-in-btn').addEventListener('click', () => {
                scale = Math.min(5, scale + 0.5); // Incremento mayor para zoom más rápido
                updateZoomLevel();
                applyTransform();
                
                // Mostrar el indicador brevemente
                dragIndicator.classList.remove('fade');
                dragIndicator.textContent = `Zoom: ${Math.round(scale * 100)}%`;
                setTimeout(() => {
                    dragIndicator.classList.add('fade');
                }, 1500);
            });
            
            container.querySelector('.zoom-out-btn').addEventListener('click', () => {
                scale = Math.max(1, scale - 0.5); // Decremento mayor para zoom más rápido
                updateZoomLevel();
                applyTransform();
                
                // Mostrar el indicador brevemente
                dragIndicator.classList.remove('fade');
                dragIndicator.textContent = `Zoom: ${Math.round(scale * 100)}%`;
                setTimeout(() => {
                    dragIndicator.classList.add('fade');
                }, 1500);
            });
            
            container.querySelector('.zoom-reset-btn').addEventListener('click', () => {
                scale = 1;
                translateX = 0;
                translateY = 0;
                updateZoomLevel();
                applyTransform();
                
                // Mostrar el indicador brevemente
                dragIndicator.classList.remove('fade');
                dragIndicator.textContent = 'Vista restablecida';
                setTimeout(() => {
                    dragIndicator.classList.add('fade');
                }, 1500);
            });
            
            // Inicializar con un zoom ligeramente mayor para mejor visualización
            scale = 1.2;
            updateZoomLevel();
            applyTransform();
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

// Función para procesar el documento con los datos ingresados
function processDocument() {
    // Recopilar datos del formulario
    const formData = {
        student: {
            rut: document.getElementById('studentRut').value,
            name: document.getElementById('studentName').value,
            email: document.getElementById('studentEmail').value
        },
        aval: {
            rut: document.getElementById('avalRut').value,
            name: document.getElementById('avalName').value,
            address: document.getElementById('avalAddress').value,
            phone: document.getElementById('avalPhone').value,
            relationship: document.getElementById('avalRelationship').value
        }
    };
    
    // Validar datos básicos
    if (!formData.student.rut || !formData.student.name || 
        !formData.aval.rut || !formData.aval.name) {
        alert('Por favor complete los campos obligatorios (RUT y Nombre) tanto del estudiante como del aval.');
        return;
    }
    
    // Mostrar indicador de carga
    const processBtn = document.getElementById('processBtn');
    const originalText = processBtn.innerHTML;
    processBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Procesando...';
    processBtn.disabled = true;
    
    // Simular procesamiento (aquí se enviarían los datos al servidor)
    setTimeout(() => {
        console.log('Datos del documento a procesar:', formData);
        
        // Mostrar resultado (en una aplicación real, esto vendría del servidor)
        alert('Documento procesado correctamente');
        
        // Restaurar el botón
        processBtn.innerHTML = originalText;
        processBtn.disabled = false;
    }, 1500);
    
    // En una aplicación real, enviaríamos los datos al servidor:
    /*
    fetch('/process_document', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Documento procesado correctamente');
        } else {
            alert('Error al procesar el documento: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al procesar el documento');
    })
    .finally(() => {
        // Restaurar el botón
        processBtn.innerHTML = originalText;
        processBtn.disabled = false;
    });
    */
}

// Función para separar el RUT chileno en número y dígito verificador
function splitRut(rutCompleto) {
    if (!rutCompleto) return { numero: '', dv: '' };
    
    // Eliminar puntos y guiones
    let rutLimpio = rutCompleto.replace(/\./g, '').replace(/-/g, '');
    
    // Obtener el dígito verificador (último carácter)
    const dv = rutLimpio.slice(-1);
    
    // Obtener el número (todo excepto el último carácter)
    const numero = rutLimpio.slice(0, -1);
    
    return { numero, dv };
}

// Modificar la función runOCR para separar el RUT
function runOCR() {
    // Mostrar indicador de carga
    const ocrBtn = document.getElementById('ocrBtn');
    const originalText = ocrBtn.innerHTML;
    ocrBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> OCR...';
    ocrBtn.disabled = true;
    
    // Llamar al endpoint que ejecutará el script
    fetch('/ocr')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Rellenar SOLO los campos RUT y Folio con los datos extraídos
                if (data.student_data) {
                    // Separar y rellenar RUT del estudiante
                    if (data.student_data.rut) {
                        const rutParts = splitRut(data.student_data.rut);
                        document.getElementById('studentRutNumber').value = rutParts.numero;
                        document.getElementById('studentRutDV').value = rutParts.dv;
                    }
                    
                    // Rellenar folio del estudiante
                    if (data.student_data.folio) {
                        document.getElementById('studentFolio').value = data.student_data.folio;
                    }
                }
                
                // Crear modal para mostrar el resultado del OCR
                const modalHtml = `
                <div class="modal fade" id="ocrResultModal" tabindex="-1" aria-labelledby="ocrResultModalLabel" aria-hidden="true">
                    <div class="modal-dialog modal-lg modal-dialog-scrollable">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="ocrResultModalLabel">Resultados del OCR</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="alert alert-success mb-3">
                                    <strong>Datos extraídos:</strong>
                                    <ul class="mb-0 mt-2">
                                        <li><strong>RUT:</strong> ${data.student_data.rut || 'No encontrado'}</li>
                                        <li><strong>Folio:</strong> ${data.student_data.folio || 'No encontrado'}</li>
                                    </ul>
                                </div>
                                <h6>Texto completo extraído:</h6>
                                <pre class="ocr-result">${data.ocr_text}</pre>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                                <button type="button" class="btn btn-primary" id="copyOcrBtn">
                                    <i class="fas fa-copy me-1"></i> Copiar al portapapeles
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                `;
                
                // Añadir el modal al DOM
                const modalContainer = document.createElement('div');
                modalContainer.innerHTML = modalHtml;
                document.body.appendChild(modalContainer);
                
                // Mostrar el modal
                const ocrModal = new bootstrap.Modal(document.getElementById('ocrResultModal'));
                ocrModal.show();
                
                // Manejar el botón de copiar
                document.getElementById('copyOcrBtn').addEventListener('click', function() {
                    const ocrText = data.ocr_text;
                    navigator.clipboard.writeText(ocrText).then(() => {
                        this.innerHTML = '<i class="fas fa-check me-1"></i> Copiado';
                        setTimeout(() => {
                            this.innerHTML = '<i class="fas fa-copy me-1"></i> Copiar al portapapeles';
                        }, 2000);
                    });
                });
                
                // Eliminar el modal del DOM cuando se cierre
                document.getElementById('ocrResultModal').addEventListener('hidden.bs.modal', function() {
                    this.remove();
                });
            } else {
                alert('Error al ejecutar OCR: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error al ejecutar OCR:', error);
            alert('Error al ejecutar OCR');
        })
        .finally(() => {
            // Restaurar el botón
            ocrBtn.innerHTML = originalText;
            ocrBtn.disabled = false;
        });
}

// Función para iniciar una nueva digitalización (sin confirmación)
function newDigitalization() {
    // Mostrar indicador de carga
    const newDigBtn = document.getElementById('newDigitalizationBtn');
    const originalText = newDigBtn.innerHTML;
    newDigBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
    newDigBtn.disabled = true;
    
    // Llamar al endpoint para eliminar las imágenes
    fetch('/clear_input')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Limpiar todos los campos del formulario
                document.getElementById('documentDataForm').reset();
                document.getElementById('studentRutNumber').value = '';
                document.getElementById('studentRutDV').value = '';
                document.getElementById('studentFolio').value = '';
                
                // Actualizar las imágenes (ahora deberían estar vacías)
                refreshImages();
            } else {
                console.error('Error al iniciar nueva digitalización:', data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        })
        .finally(() => {
            // Restaurar el botón
            newDigBtn.innerHTML = originalText;
            newDigBtn.disabled = false;
        });
}