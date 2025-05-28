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
        const codigo = document.getElementById('projectCode').value.trim();
        
        if (!codigo) {
            alert('Por favor ingrese un código de proyecto');
            return;
        }
        
        // Buscar el código en el CSV
        buscarCodigo(codigo).then(data => {
            let nombreProyecto = 'No encontrado';
            
            if (data.success && data.proyecto) {
                nombreProyecto = data.proyecto.NOMBRE_INICIATIVA;
            }
            
            // Obtener los valores de documento presente y observación
            const documentoPresente = document.getElementById('documentPresent').value;
            const observacion = document.getElementById('observation').value;
            
            // Preguntar al usuario si desea continuar
            if (confirm(`Estás añadiendo ${codigo}.pdf para el proyecto: ${nombreProyecto}\n\n¿Continuar?`)) {
                // Procesar el documento
                procesarDocumento(codigo, nombreProyecto, documentoPresente, observacion);
            }
        });
    });
    
    // Botón de OCR
    document.getElementById('ocrBtn').addEventListener('click', function() {
        executeOCR();
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

    // Actualizar la interfaz para mostrar solo lo necesario
    updateInterface();
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
                                    <button class="btn btn-sm btn-primary move-to-first-btn" data-filename="${image.name}" title="Mover a primera posición" ${index === 0 ? 'disabled' : ''}>
                                        <i class="fas fa-angle-double-up"></i>
                                    </button>
                                    <button class="btn btn-sm btn-danger delete-btn" data-filename="${image.name}" title="Eliminar">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                    <button class="btn btn-sm btn-info rotate-left" data-filename="${image.name}" title="Rotar izquierda">
                                        <i class="fas fa-undo"></i>
                                    </button>
                                    <button class="btn btn-sm btn-info rotate-right" data-filename="${image.name}" title="Rotar derecha">
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
    
    // Añadir eventos a los botones de mover a primera posición
    document.querySelectorAll('.move-to-first-btn').forEach(button => {
        button.addEventListener('click', function() {
            console.log('Click en mover a primera posición');
            const filename = this.getAttribute('data-filename');
            moveImageToFirst(filename);
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

// Función para mover una imagen a la primera posición
function moveImageToFirst(filename) {
    // Verificar que la imagen no es ya la primera
    const currentIndex = imageOrder.indexOf(filename);
    if (currentIndex <= 0) {
        return; // Ya es la primera imagen o no se encuentra
    }
    
    // Quitar la imagen de su posición actual
    imageOrder.splice(currentIndex, 1);
    // Añadirla al principio
    imageOrder.unshift(filename);
    
    // Guardar el nuevo orden en localStorage
    localStorage.setItem('imageOrder', JSON.stringify(imageOrder));
    
    // Actualizar la vista
    refreshImages();
    
    // Mostrar notificación
    showNotification('Imagen movida a la primera posición', 'success');
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

// Función para procesar el documento
function procesarDocumento(codigo, nombreProyecto, documentoPresente, observacion) {
    const processBtn = document.getElementById('processBtn');
    const originalText = processBtn.innerHTML;
    processBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
    processBtn.disabled = true;
    
    // Obtener todas las imágenes disponibles
    let selectedImages = [];
    document.querySelectorAll('.document-image').forEach(img => {
        const filename = img.alt;
        if (filename) {
            selectedImages.push(filename);
        }
    });
    
    // Enviar datos al servidor para procesar
    fetch('/procesar_documento', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            codigo: codigo,
            nombreProyecto: nombreProyecto,
            documentoPresente: documentoPresente,
            observacion: observacion,
            selectedImages: selectedImages
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`Documento procesado correctamente. PDF guardado como: ${data.pdf_filename}`);
            // Recargar la página para actualizar la vista (la carpeta input ya estará vacía)
            window.location.reload();
        } else {
            alert('Error al procesar documento: ' + data.error);
            // Restaurar botón
            processBtn.innerHTML = originalText;
            processBtn.disabled = false;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al procesar el documento');
        // Restaurar botón
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

// Función para OCR enfocada solo en encontrar el código de proyecto
function executeOCR() {
    const ocrBtn = document.getElementById('ocrBtn');
    const originalText = ocrBtn.innerHTML;
    ocrBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
    ocrBtn.disabled = true;
    
    fetch('/ocr')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                let matriculaMessage = '';
                
                // Prellenar el campo de código de proyecto si se encontró uno
                if (data.matriculas_encontradas && data.matriculas_encontradas.length > 0) {
                    const projectCodeField = document.getElementById('projectCode');
                    projectCodeField.value = data.matriculas_encontradas[0];
                    
                    // Efecto visual para mostrar que se ha rellenado
                    projectCodeField.classList.add('bg-success', 'text-white');
                    setTimeout(() => {
                        projectCodeField.classList.remove('bg-success', 'text-white');
                    }, 1500);
                    
                    // Mensaje de éxito
                    matriculaMessage = `<div class="alert alert-success">
                        <strong>Código encontrado:</strong> ${data.matriculas_encontradas[0]}
                    </div>`;
                    
                    // Si hay más de un código, mostrarlos todos y permitir seleccionar
                    if (data.matriculas_encontradas.length > 1) {
                        matriculaMessage += `<div class="alert alert-info">
                            <strong>Múltiples códigos encontrados:</strong>
                            <ul class="mb-0 mt-2 codigo-list">
                                ${data.matriculas_encontradas.map(m => 
                                    `<li><a href="#" class="codigo-link" data-codigo="${m}">${m}</a></li>`
                                ).join('')}
                            </ul>
                        </div>`;
                    }
                } else {
                    matriculaMessage = `<div class="alert alert-warning">
                        <strong>Código no encontrado.</strong> No se pudo detectar ningún código con formato 2301[A-Z]{1,2}\\d{4}
                    </div>`;
                }
                
                // Crear modal para mostrar el resultado del OCR
                const modalHtml = `
                <div class="modal fade" id="ocrResultModal" tabindex="-1" aria-labelledby="ocrResultModalLabel" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="ocrResultModalLabel">Resultados del OCR</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                ${matriculaMessage}
                                <h6>Texto extraído:</h6>
                                <pre class="bg-light p-3 border rounded" style="max-height:300px;overflow:auto;white-space:pre-wrap;">${data.ocr_text}</pre>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                            </div>
                        </div>
                    </div>
                </div>
                `;
                
                // Eliminar modal anterior si existe
                const oldModal = document.getElementById('ocrResultModal');
                if (oldModal) {
                    oldModal.remove();
                }
                
                // Añadir el nuevo modal al body
                document.body.insertAdjacentHTML('beforeend', modalHtml);
                
                // Mostrar el modal
                const ocrResultModal = new bootstrap.Modal(document.getElementById('ocrResultModal'));
                ocrResultModal.show();
                
                // Añadir event listeners para los enlaces de códigos alternativos
                document.querySelectorAll('.codigo-link').forEach(link => {
                    link.addEventListener('click', function(e) {
                        e.preventDefault();
                        const codigo = this.getAttribute('data-codigo');
                        document.getElementById('projectCode').value = codigo;
                        ocrResultModal.hide();
                    });
                });
            } else {
                console.error('Error en OCR:', data.error);
                alert(`Error al procesar OCR: ${data.error}`);
            }
            
            // Restaurar botón
            ocrBtn.innerHTML = originalText;
            ocrBtn.disabled = false;
        })
        .catch(error => {
            console.error('Error al ejecutar OCR:', error);
            alert('Error al ejecutar OCR. Por favor, inténtelo de nuevo.');
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
                // Limpiar solo el campo de proyecto
                document.getElementById('documentDataForm').reset();
                
                // Limpiar específicamente el campo de proyecto
                const matriculaField = document.getElementById('studentMatricula');
                if (matriculaField) {
                    matriculaField.value = '';
                }
                
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

// Función para modificar la interfaz al cargar la página
function updateInterface() {
    // No hacer nada, ya que el HTML tiene lo que necesitamos
    console.log("Interfaz ya configurada en HTML");
    
    // O simplemente eliminar esta función si no se usa para nada más
}

// Añadir función para buscar código en el CSV
function buscarCodigo(codigo) {
    return fetch(`/buscar_codigo/${codigo}`)
        .then(response => response.json())
        .then(data => {
            return data;
        })
        .catch(error => {
            console.error('Error al buscar código:', error);
            return { success: false, error: 'Error al buscar el código' };
        });
}