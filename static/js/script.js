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
    
    // Inicializar imágenes y cargar eventos iniciales
    refreshImages();
});

// Variable para almacenar la última modificación conocida
let lastKnownModification = 0;

// Variable global para almacenar el orden de las imágenes
let imageOrder = [];

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
/*
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
*/

// Función para actualizar las imágenes
function refreshImages() {
    fetch('/refresh')
        .then(response => response.json())
        .then(data => {
            // Si es la primera carga o tenemos nuevas imágenes, inicializar el orden
            if (imageOrder.length === 0 || data.length !== imageOrder.length) {
                imageOrder = data.map(image => image.name);
            }
            
            // Ordenar los datos según el orden actual
            const orderedData = [];
            for (const imageName of imageOrder) {
                const image = data.find(img => img.name === imageName);
                if (image) {
                    orderedData.push(image);
                }
            }
            
            // Añadir cualquier imagen nueva que no esté en nuestro orden
            for (const image of data) {
                if (!imageOrder.includes(image.name)) {
                    orderedData.push(image);
                    imageOrder.push(image.name);
                }
            }

            const documentContainer = document.getElementById('documentContainer');
            documentContainer.innerHTML = ''; // Limpiar contenedor
            
            orderedData.forEach((image, index) => {
                if (!image.data) {
                    // Si no hay imagen, mostrar mensaje
                    const noImageDiv = document.createElement('div');
                    noImageDiv.className = 'col-md-6 mb-4';
                    noImageDiv.innerHTML = `
                        <div class="card h-100">
                            <div class="card-header bg-secondary text-white">
                                <h5 class="card-title mb-0">No hay imagen disponible</h5>
                            </div>
                            <div class="card-body d-flex align-items-center justify-content-center">
                                <p class="text-muted">No se han subido imágenes</p>
                            </div>
                        </div>
                    `;
                    documentContainer.appendChild(noImageDiv);
                } else {
                    // Crear tarjeta para la imagen
                    const imageCard = document.createElement('div');
                    imageCard.className = 'col-md-6 mb-4';
                    
                    // Añadir una clase especial a la primera imagen
                    const isFirstImage = index === 0;
                    const cardHeaderClass = isFirstImage ? 'bg-success' : 'bg-primary';
                    const firstImageBadge = isFirstImage ? 
                        '<span class="badge bg-warning text-dark me-2">Primera</span>' : '';
                    
                    imageCard.innerHTML = `
                        <div class="card h-100 ${isFirstImage ? 'border border-success border-3' : ''}">
                            <div class="card-header ${cardHeaderClass} text-white d-flex justify-content-between align-items-center">
                                <h5 class="card-title mb-0">
                                    ${firstImageBadge}${image.name}
                                </h5>
                                <div class="document-tools">
                                    <button class="btn btn-sm btn-secondary move-up-btn" data-filename="${image.name}" title="Mover arriba" ${index === 0 ? 'disabled' : ''}>
                                        <i class="fas fa-arrow-up"></i>
                                    </button>
                                    <button class="btn btn-sm btn-secondary move-down-btn" data-filename="${image.name}" title="Mover abajo" ${index === orderedData.length - 1 ? 'disabled' : ''}>
                                        <i class="fas fa-arrow-down"></i>
                                    </button>
                                    <button class="btn btn-sm btn-danger delete-btn" data-filename="${image.name}" title="Eliminar">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                    <button class="btn btn-sm btn-light rotate-left" data-filename="${image.name}" title="Rotar izquierda">
                                        <i class="fas fa-undo"></i>
                                    </button>
                                    <button class="btn btn-sm btn-light rotate-right" data-filename="${image.name}" title="Rotar derecha">
                                        <i class="fas fa-redo"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="card-body document-container">
                                <img src="${image.data}" class="img-fluid document-image" alt="${image.name}">
                            </div>
                            <div class="card-footer text-muted">
                                <small>Modificado: ${image.modified}</small>
                                <span class="badge bg-info float-end">Página ${index + 1}</span>
                            </div>
                        </div>
                    `;
                    documentContainer.appendChild(imageCard);
                }
            });
            
            // Añadir eventos a los botones después de crear los elementos
            addButtonEvents();
        })
        .catch(error => console.error('Error al actualizar imágenes:', error));
}

function addButtonEvents() {
    console.log('Añadiendo eventos a los botones');
    
    // Botones de movimiento
    document.querySelectorAll('.move-up-btn').forEach(button => {
        button.addEventListener('click', function() {
            console.log('Click en mover arriba');
            const filename = this.getAttribute('data-filename');
            moveImage(filename, 'up');
        });
    });
    
    document.querySelectorAll('.move-down-btn').forEach(button => {
        button.addEventListener('click', function() {
            console.log('Click en mover abajo');
            const filename = this.getAttribute('data-filename');
            moveImage(filename, 'down');
        });
    });
    
    // Añadir eventos a los botones de eliminar
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', function() {
            const filename = this.getAttribute('data-filename');
            if (confirm(`¿Estás seguro de que deseas eliminar el archivo ${filename}?`)) {
                deleteImage(filename);
            }
        });
    });
    
    // Añadir eventos a los botones de rotar
    document.querySelectorAll('.rotate-left').forEach(button => {
        button.addEventListener('click', function() {
            const filename = this.getAttribute('data-filename');
            rotateImage(filename, 'left');
        });
    });
    
    document.querySelectorAll('.rotate-right').forEach(button => {
        button.addEventListener('click', function() {
            const filename = this.getAttribute('data-filename');
            rotateImage(filename, 'right');
        });
    });
}

function deleteImage(filename) {
    fetch(`/delete/${filename}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                refreshImages(); // Actualizar la vista después de eliminar
            } else {
                alert('Error al eliminar la imagen: ' + data.error);
            }
        })
        .catch(error => console.error('Error al eliminar imagen:', error));
}

function rotateImage(filename, direction) {
    fetch(`/rotate/${filename}/${direction}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                refreshImages(); // Actualizar la vista después de rotar
            } else {
                alert('Error al rotar la imagen: ' + data.error);
            }
        })
        .catch(error => console.error('Error al rotar imagen:', error));
}

// Función para mover una imagen arriba/abajo en el orden
function moveImage(filename, direction) {
    const index = imageOrder.indexOf(filename);
    if (index === -1) return;
    
    if (direction === 'up' && index > 0) {
        // Intercambiar con el elemento anterior
        [imageOrder[index], imageOrder[index - 1]] = [imageOrder[index - 1], imageOrder[index]];
        refreshImages();
    } else if (direction === 'down' && index < imageOrder.length - 1) {
        // Intercambiar con el elemento siguiente
        [imageOrder[index], imageOrder[index + 1]] = [imageOrder[index + 1], imageOrder[index]];
        refreshImages();
    }
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
    // Obtener el folio ingresado
    const folio = document.getElementById('studentFolio').value.trim();
    
    if (!folio) {
        alert('Por favor, ingrese un número de folio');
        return;
    }
    
    // Mostrar indicador de carga
    const processBtn = document.getElementById('processBtn');
    const originalText = processBtn.innerHTML;
    processBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
    processBtn.disabled = true;
    
    // Llamar al endpoint para buscar el folio
    fetch(`/buscar_folio/${folio}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Llenar los campos con los datos obtenidos
                document.getElementById('studentName').value = data.datos.nombre_estudiante;
                document.getElementById('avalName').value = data.datos.nombre_aval;
                document.getElementById('avalRut').value = data.datos.rut_aval;
                document.getElementById('amount').value = data.datos.monto;
                document.getElementById('avalEmail').value = data.datos.email_aval;
                
                // Mostrar botón de finalizar procesado
                mostrarBotonFinalizar();
            } else {
                alert('Error: ' + (data.error || 'No se encontró el folio especificado'));
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
}

// Función para mostrar el botón de finalizar procesado
function mostrarBotonFinalizar() {
    // Verificar si ya existe el botón
    if (document.getElementById('finishBtn')) {
        return;
    }
    
    // Ocultar el botón de procesar documento
    const processBtn = document.getElementById('processBtn');
    processBtn.style.display = 'none';
    
    // Crear el botón
    const finishBtn = document.createElement('button');
    finishBtn.type = 'button';
    finishBtn.id = 'finishBtn';
    finishBtn.className = 'btn btn-success btn-lg w-100 mt-3';
    finishBtn.innerHTML = '<i class="fas fa-check-circle me-2"></i> Finalizar Procesado';
    
    // Añadir evento al botón
    finishBtn.addEventListener('click', function() {
        finalizarProcesado();
    });
    
    // Añadir el botón al formulario
    const form = document.getElementById('documentDataForm');
    form.appendChild(finishBtn);
}

// Función para finalizar el procesado
function finalizarProcesado() {
    // Obtener los datos necesarios
    const rutNumber = document.getElementById('studentRutNumber').value.trim();
    const rutDV = document.getElementById('studentRutDV').value.trim();
    const folio = document.getElementById('studentFolio').value.trim();
    
    // Validar datos
    if (!rutNumber || !rutDV || !folio) {
        alert('Faltan datos necesarios (RUT o Folio)');
        return;
    }
    
    // Mostrar indicador de carga
    const finishBtn = document.getElementById('finishBtn');
    const originalText = finishBtn.innerHTML;
    finishBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando PDF...';
    finishBtn.disabled = true;
    
    // Preparar datos para enviar al servidor
    const data = {
        rutNumber: rutNumber,
        rutDV: rutDV,
        folio: folio,
        selectedImages: imageOrder // Enviar el orden actual de las imágenes
    };
    
    // Llamar al endpoint para generar el PDF
    fetch('/generar_pdf', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`Documento procesado correctamente.\nPDF guardado como: ${data.filename}`);
            
            // Restaurar la interfaz para una nueva digitalización
            document.getElementById('documentDataForm').reset();
            document.getElementById('studentRutNumber').value = '';
            document.getElementById('studentRutDV').value = '';
            document.getElementById('studentFolio').value = '';
            document.getElementById('studentName').value = '';
            document.getElementById('avalName').value = '';
            document.getElementById('avalRut').value = '';
            document.getElementById('amount').value = '';
            document.getElementById('avalEmail').value = '';
            
            // Quitar el botón de finalizar y mostrar el de procesar
            finishBtn.remove();
            document.getElementById('processBtn').style.display = 'block';
            
            // Opcional: iniciar una nueva digitalización
            newDigitalization();
        } else {
            alert('Error al generar el PDF: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al generar el PDF');
    })
    .finally(() => {
        // Restaurar el botón
        finishBtn.innerHTML = originalText;
        finishBtn.disabled = false;
    });
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

// Mejorar el manejo del texto OCR en el modal
function runOCR() {
    // Mostrar indicador de carga
    const ocrBtn = document.getElementById('ocrBtn');
    const originalText = ocrBtn.innerHTML;
    ocrBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> OCR...';
    ocrBtn.disabled = true;
    
    // Verificar si hay imágenes
    if (imageOrder.length === 0) {
        alert('No hay imágenes para procesar');
        ocrBtn.innerHTML = originalText;
        ocrBtn.disabled = false;
        return;
    }
    
    // Obtener el nombre de la primera imagen según el orden actual
    const firstImageName = imageOrder[0];
    console.log("Procesando OCR en la primera imagen:", firstImageName);
    
    // Añadir un indicador visual temporal
    const firstImageCard = document.querySelector('.col-md-6:first-child .card');
    if (firstImageCard) {
        firstImageCard.classList.add('border-danger', 'border-5');
        setTimeout(() => {
            firstImageCard.classList.remove('border-danger', 'border-5');
        }, 2000);
    }
    
    // Llamar al endpoint que ejecutará el script con la imagen específica
    fetch(`/ocr?filename=${firstImageName}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Datos OCR completos:', data);
                
                // Mensaje para mostrar si no se encontraron datos
                let ocrMessage = '';
                let dataFound = false;
                
                // Rellenar SOLO los campos RUT y Folio con los datos extraídos
                if (data.student_data) {
                    // Separar y rellenar RUT del estudiante
                    if (data.student_data.rut) {
                        dataFound = true;
                        const rutParts = splitRut(data.student_data.rut);
                        document.getElementById('studentRutNumber').value = rutParts.numero;
                        document.getElementById('studentRutDV').value = rutParts.dv;
                    }
                    
                    // Rellenar folio del estudiante
                    if (data.student_data.folio) {
                        dataFound = true;
                        document.getElementById('studentFolio').value = data.student_data.folio;
                    }
                }
                
                if (!dataFound) {
                    ocrMessage = '<div class="alert alert-warning">No se detectaron datos automáticamente. Por favor, ingrese manualmente el RUT y Folio.</div>';
                }
                
                // Asegurarse de que el texto OCR esté disponible y formateado correctamente
                const ocrText = data.ocr_text || "No se pudo extraer texto de la imagen";
                
                // Crear modal para mostrar el resultado del OCR
                const modalHtml = `
                <div class="modal fade" id="ocrResultModal" tabindex="-1" aria-labelledby="ocrResultModalLabel" aria-hidden="true">
                    <div class="modal-dialog modal-lg modal-dialog-scrollable">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="ocrResultModalLabel">Resultados del OCR (Página 1: ${firstImageName})</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                ${ocrMessage}
                                <div class="alert alert-info mb-3">
                                    <strong>Datos extraídos:</strong>
                                    <ul class="mb-0 mt-2">
                                        <li><strong>RUT:</strong> ${data.student_data?.rut || 'No encontrado'}</li>
                                        <li><strong>Folio:</strong> ${data.student_data?.folio || 'No encontrado'}</li>
                                    </ul>
                                    <div class="mt-3 text-dark fw-bold">
                                        Revisa los datos en la pantalla principal antes de procesar el documento
                                    </div>
                                </div>
                                
                                <div class="mb-3">
                                    <button class="btn btn-outline-secondary btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#collapseOcrText" aria-expanded="false" aria-controls="collapseOcrText">
                                        <i class="fas fa-plus-circle me-1"></i> Mostrar texto completo extraído
                                    </button>
                                </div>
                                
                                <div class="collapse show" id="collapseOcrText">
                                    <div class="card card-body">
                                        <h6>Texto completo extraído:</h6>
                                        <pre class="ocr-result" style="white-space: pre-wrap; max-height: 300px; overflow-y: auto;">${ocrText}</pre>
                                    </div>
                                </div>
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
                
                // Cambiar el texto del botón cuando se expande/contrae
                document.querySelector('[data-bs-toggle="collapse"]').addEventListener('click', function() {
                    const expanded = this.getAttribute('aria-expanded') === 'true';
                    if (expanded) {
                        this.innerHTML = '<i class="fas fa-minus-circle me-1"></i> Ocultar texto completo extraído';
                    } else {
                        this.innerHTML = '<i class="fas fa-plus-circle me-1"></i> Mostrar texto completo extraído';
                    }
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

// Añadir esta función si no existe
function initializeZoom() {
    // Implementar funcionalidad de zoom si es necesario
    // O dejar vacía si no se necesita esta funcionalidad
}