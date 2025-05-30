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
            const boxNumber = document.getElementById('boxNumber').value.trim();
            
            // Preguntar al usuario si desea continuar
            if (confirm(`Estás añadiendo ${codigo}.pdf para el proyecto: ${nombreProyecto}\n\n¿Continuar?`)) {
                // Procesar el documento
                procesarDocumento(codigo, nombreProyecto, documentoPresente, observacion, boxNumber);
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

    // Añadir el event listener para el botón de cuadratura
    document.getElementById('cuadraturaBtn').addEventListener('click', function() {
        generarCuadratura();
    });

    // Cuando se busca un código de proyecto
    document.getElementById('projectCode').addEventListener('blur', function() {
        const codigo = this.value.trim();
        if (codigo.length > 0) {
            fetch(`/buscar_codigo/${codigo}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Autocompletar campos con los datos del proyecto
                        const proyecto = data.proyecto;
                        
                        // Mostrar el número de caja si está disponible
                        if (proyecto.CAJA) {
                            document.getElementById('boxNumber').value = proyecto.CAJA;
                        } else {
                            document.getElementById('boxNumber').value = '';
                        }
                        
                        // Completar otros campos si están disponibles
                        if (proyecto.DOC_PRESENTE) {
                            document.getElementById('documentPresent').value = proyecto.DOC_PRESENTE;
                        }
                        
                        if (proyecto.OBSERVACION) {
                            document.getElementById('observation').value = proyecto.OBSERVACION;
                        }
                        
                        // Mostrar alguna notificación de éxito o completar otros campos
                        console.log("Proyecto encontrado:", proyecto);
                    } else {
                        // Limpiar campos si el código no existe
                        document.getElementById('boxNumber').value = '';
                        // Mostrar mensaje de error
                        console.error("Error:", data.error);
                    }
                })
                .catch(error => {
                    console.error("Error en la búsqueda:", error);
                });
        }
    });
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
function procesarDocumento(codigo, nombreProyecto, documentoPresente, observacion, boxNumber) {
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
            selectedImages: selectedImages,
            boxNumber: boxNumber
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

// Función para generar la cuadratura
function generarCuadratura() {
    // Mostrar indicador de carga
    const cuadraturaBtn = document.getElementById('cuadraturaBtn');
    const originalText = cuadraturaBtn.innerHTML;
    cuadraturaBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando...';
    cuadraturaBtn.disabled = true;
    
    // Llamar al endpoint para generar la cuadratura
    fetch('/generar_cuadratura')
        .then(response => {
            if (!response.ok) {
                throw new Error('Error al generar la cuadratura');
            }
            return response.blob();
        })
        .then(blob => {
            // Crear un enlace de descarga para el archivo Excel
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            
            // Obtener la fecha y hora actual para el nombre del archivo
            const now = new Date();
            const timestamp = now.toISOString().replace(/[:.]/g, '-');
            
            a.href = url;
            a.download = `cuadratura_${timestamp}.xlsx`;
            document.body.appendChild(a);
            a.click();
            
            // Limpiar
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            // Mostrar mensaje de éxito
            alert('Cuadratura generada correctamente');
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al generar la cuadratura: ' + error.message);
        })
        .finally(() => {
            // Restaurar el botón
            cuadraturaBtn.innerHTML = originalText;
            cuadraturaBtn.disabled = false;
        });
}

// Función para establecer el modo activo
function setActiveMode(mode) {
    window.currentMode = mode;
    
    // Esta función se utiliza para mantener la compatibilidad con el código existente
    // que depende de saber qué modo está activo
    console.log('Modo activo establecido:', mode);
}

// Funciones para cargar datos específicos de cada modo
function loadFolders() {
    fetch('/get_folders')
        .then(response => response.json())
        .then(data => {
            updateFolderList(data);
            if (data.images && data.images.length > 0) {
                updateFolderImageGrid(data.images);
            }
        })
        .catch(error => {
            console.error('Error al cargar carpetas:', error);
        });
}

function updateFolderList(data) {
    const folderList = document.getElementById('folderList');
    if (!folderList) return;
    
    folderList.innerHTML = '';
    
    if (data.folders && data.folders.length > 0) {
        data.folders.forEach(folder => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.className = 'dropdown-item';
            a.href = '#';
            a.textContent = folder;
            if (data.current_folder === folder) {
                a.className += ' active';
            }
            a.addEventListener('click', function() {
                loadFolderImages(folder);
            });
            li.appendChild(a);
            folderList.appendChild(li);
        });
        
        // Actualizar el texto del botón dropdown
        const folderDropdown = document.getElementById('folderDropdown');
        if (folderDropdown) {
            folderDropdown.textContent = `Carpeta: ${data.current_folder || 'Ninguna'}`;
        }
    }
}

function updateFolderImageGrid(images) {
    const imageGrid = document.getElementById('folderImageGrid');
    if (!imageGrid) return;
    
    imageGrid.innerHTML = '';
    
    if (images.length === 0) {
        imageGrid.innerHTML = '<div class="col-12 text-center"><p>No hay imágenes en esta carpeta</p></div>';
        return;
    }
    
    images.forEach(image => {
        const col = document.createElement('div');
        col.className = 'col';
        col.innerHTML = `
            <div class="card h-100 image-card">
                <img src="${image.data}" class="card-img-top" alt="${image.name}">
                <div class="card-body">
                    <h5 class="card-title">${image.name}</h5>
                    <p class="card-text">${image.modified}</p>
                </div>
            </div>
        `;
        imageGrid.appendChild(col);
    });
}

function loadFolderImages(folder) {
    fetch(`/get_folders?folder=${folder}`)
        .then(response => response.json())
        .then(data => {
            updateFolderList(data);
            if (data.images) {
                updateFolderImageGrid(data.images);
            }
        })
        .catch(error => {
            console.error(`Error al cargar imágenes de carpeta ${folder}:`, error);
        });
}

function loadPdfs() {
    fetch('/list_pdfs')
        .then(response => response.json())
        .then(data => {
            updatePdfTable(data);
        })
        .catch(error => {
            console.error('Error al cargar PDFs:', error);
        });
}

function updatePdfTable(pdfs) {
    const tableBody = document.getElementById('pdfTableBody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    if (!pdfs || pdfs.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="4" class="text-center">No hay documentos PDF disponibles</td>';
        tableBody.appendChild(row);
        return;
    }
    
    pdfs.forEach(pdf => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${pdf.name}</td>
            <td>${pdf.modified}</td>
            <td>${pdf.size}</td>
            <td>
                <a href="/por_procesar/${pdf.name}" class="btn btn-sm btn-primary" target="_blank">
                    <i class="fas fa-eye me-1"></i> Ver
                </a>
                <a href="/por_procesar/${pdf.name}" class="btn btn-sm btn-success" download>
                    <i class="fas fa-download me-1"></i> Descargar
                </a>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

// Configuración de controles específicos
function setupAutoRefresh() {
    const autoRefreshSwitch = document.getElementById('autoRefreshSwitch');
    if (autoRefreshSwitch) {
        autoRefreshSwitch.addEventListener('change', function() {
            if (this.checked) {
                startFolderMonitoring();
            } else {
                clearInterval(window.folderCheckInterval);
            }
        });
    }
}

function setupFileUpload() {
    const fileUpload = document.getElementById('fileUpload');
    if (fileUpload) {
        fileUpload.addEventListener('change', function() {
            if (this.files.length > 0) {
                uploadSelectedFiles(this.files);
            }
        });
    }
}

function setupClearButton() {
    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            if (confirm('¿Está seguro que desea eliminar todas las imágenes?')) {
                clearInputFolder();
            }
        });
    }
}

// Funciones para las acciones específicas de cada modo
function generateFolder() {
    // Mostrar indicador de carga
    const btn = document.getElementById('generateFolderBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Creando carpeta...';
    btn.disabled = true;
    
    fetch('/generar_carpeta')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'Carpeta creada',
                    text: `Se ha creado la carpeta ${data.folder} con ${data.files_moved} imágenes`,
                    confirmButtonText: 'Ir a Indexación',
                    showCancelButton: true,
                    cancelButtonText: 'Continuar Digitalizando'
                }).then((result) => {
                    if (result.isConfirmed) {
                        // Redirigir a la página de indexación
                        window.location.href = '/indexacion';
                    } else {
                        // Refrescar las imágenes
                        refreshImages();
                    }
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: data.error || 'No se pudo crear la carpeta'
                });
            }
        })
        .catch(error => {
            console.error('Error al generar carpeta:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Ocurrió un error al crear la carpeta'
            });
        })
        .finally(() => {
            // Restaurar el botón
            btn.innerHTML = originalText;
            btn.disabled = false;
        });
}

function extractProjectCode() {
    // Obtener la carpeta actual
    const folderDropdown = document.getElementById('folderDropdown');
    const currentFolder = folderDropdown.textContent.replace('Carpeta: ', '');
    
    if (!currentFolder || currentFolder === 'Ninguna') {
        Swal.fire({
            icon: 'warning',
            title: 'No hay carpeta seleccionada',
            text: 'Seleccione una carpeta para extraer el código'
        });
        return;
    }
    
    // Mostrar indicador de carga
    const btn = document.getElementById('extractCodeBtn');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;
    
    fetch(`/ocr?folder=${currentFolder}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Llenar campos con información extraída
                if (data.extracted_info.project_code) {
                    document.getElementById('projectCode').value = data.extracted_info.project_code;
                }
                if (data.extracted_info.box_number) {
                    document.getElementById('boxNumber').value = data.extracted_info.box_number;
                }
                if (data.extracted_info.observation) {
                    document.getElementById('observation').value = data.extracted_info.observation;
                }
                
                Swal.fire({
                    icon: 'success',
                    title: 'OCR Completado',
                    text: `Se procesaron ${data.images_processed} imágenes`
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Error en OCR',
                    text: data.error || 'No se pudo extraer información'
                });
            }
        })
        .catch(error => {
            console.error('Error en OCR:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Ocurrió un error al procesar las imágenes'
            });
        })
        .finally(() => {
            // Restaurar el botón
            btn.innerHTML = '<i class="fas fa-magic"></i>';
            btn.disabled = false;
        });
}

function generateIndexedPdf() {
    // Obtener la carpeta actual
    const folderDropdown = document.getElementById('folderDropdown');
    const currentFolder = folderDropdown.textContent.replace('Carpeta: ', '');
    
    if (!currentFolder || currentFolder === 'Ninguna') {
        Swal.fire({
            icon: 'warning',
            title: 'No hay carpeta seleccionada',
            text: 'Seleccione una carpeta para generar el PDF'
        });
        return;
    }
    
    // Obtener datos del formulario
    const projectCode = document.getElementById('projectCode').value;
    const boxNumber = document.getElementById('boxNumber').value;
    const documentPresent = document.querySelector('input[name="documentPresent"]:checked').value;
    const observation = document.getElementById('observation').value;
    
    // Validar código de proyecto (opcional)
    if (projectCode && !(projectCode.length >= 6 && projectCode.startsWith('23'))) {
        Swal.fire({
            icon: 'warning',
            title: 'Código de proyecto inválido',
            text: 'El código debe comenzar con 23 y tener al menos 6 caracteres'
        });
        return;
    }
    
    // Mostrar indicador de carga
    const btn = document.getElementById('generatePdfBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Generando PDF...';
    btn.disabled = true;
    
    // Datos para enviar
    const data = {
        folder_id: currentFolder,
        project_code: projectCode,
        box_number: boxNumber,
        document_present: documentPresent,
        observation: observation
    };
    
    fetch('/generar_pdf_indexado', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: 'PDF Generado',
                text: data.message,
                confirmButtonText: 'Ir a Procesado',
                showCancelButton: true,
                cancelButtonText: 'Continuar Indexando'
            }).then((result) => {
                if (result.isConfirmed) {
                    // Redirigir a la página de procesado
                    window.location.href = '/procesado';
                } else {
                    // Limpiar el formulario
                    document.getElementById('projectCode').value = '';
                    document.getElementById('boxNumber').value = '';
                    document.getElementById('docPresentYes').checked = true;
                    document.getElementById('observation').value = '';
                }
            });
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.error || 'No se pudo generar el PDF'
            });
        }
    })
    .catch(error => {
        console.error('Error al generar PDF:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Ocurrió un error al generar el PDF'
        });
    })
    .finally(() => {
        // Restaurar el botón
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

function startWorkflow() {
    // Este botón ahora inicia el flujo de trabajo de indexación
    executeOCR();
}

function generateReport() {
    // Mostrar indicador de carga
    const btn = document.getElementById('generateReportBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Generando...';
    btn.disabled = true;
    
    fetch('/generate_cuadratura')
        .then(response => {
            if (!response.ok) {
                throw new Error('Error al generar el reporte');
            }
            return response.blob();
        })
        .then(blob => {
            // Crear enlace de descarga
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            const now = new Date().toISOString().replace(/[:.]/g, '-');
            a.href = url;
            a.download = `cuadratura_${now}.xlsx`;
            document.body.appendChild(a);
            a.click();
            
            // Limpiar
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            Swal.fire({
                icon: 'success',
                title: 'Reporte Generado',
                text: 'El reporte de cuadratura se ha descargado correctamente'
            });
        })
        .catch(error => {
            console.error('Error:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Ocurrió un error al generar el reporte'
            });
        })
        .finally(() => {
            // Restaurar el botón
            btn.innerHTML = originalText;
            btn.disabled = false;
        });
}

function exportData() {
    // Función para exportar datos
    Swal.fire({
        icon: 'info',
        title: 'Exportación de Datos',
        text: 'Esta funcionalidad será implementada próximamente'
    });
}

// Funciones adicionales de utilidad
function clearInputFolder() {
    fetch('/clear_input')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                refreshImages();
                Swal.fire({
                    icon: 'success',
                    title: 'Carpeta limpiada',
                    text: 'Se han eliminado todas las imágenes de la carpeta de entrada'
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: data.error || 'No se pudo limpiar la carpeta'
                });
            }
        })
        .catch(error => {
            console.error('Error al limpiar carpeta:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Ocurrió un error al limpiar la carpeta'
            });
        });
}

function uploadSelectedFiles(files) {
    if (files.length === 0) return;
    
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('file', files[i]);
    }
    
    // Mostrar indicador de progreso
    Swal.fire({
        title: 'Subiendo archivos',
        html: 'Por favor espere mientras se suben los archivos...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: 'Archivos Subidos',
                text: `Se subieron ${data.files.length} archivos correctamente`
            });
            refreshImages();
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.error || 'No se pudieron subir los archivos'
            });
        }
    })
    .catch(error => {
        console.error('Error al subir archivos:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Ocurrió un error al subir los archivos'
        });
    });
}