document.addEventListener('DOMContentLoaded', function() {
    // Botón de actualizar
    document.getElementById('refreshBtn').addEventListener('click', function() {
        refreshImages();
    });
    
    // Botón de escanear
    document.getElementById('scanBtn').addEventListener('click', function() {
        scanDocuments();
    });
    
    // Botón de exportar a Gesdoc
    document.getElementById('exportToGesdocBtn').addEventListener('click', function() {
        exportarAGesdoc();
    });
    
    // Botón de invertir orden
    document.getElementById('toggleOrderBtn').addEventListener('click', function() {
        toggleImagesOrder();
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
    
    // Actualizar la apariencia del botón de invertir orden según el estado guardado
    updateToggleOrderButton();
});

// Variable para almacenar la última modificación conocida
let lastKnownModification = 0;

// Variable global para almacenar el orden de las imágenes
let imageOrder = [];

// Variable global para el estado de inversión de orden
let orderInverted = false;

// Función para iniciar el monitoreo de la carpeta
function startFolderMonitoring() {
    // Cargar el estado de inversión de orden desde localStorage
    orderInverted = localStorage.getItem('orderInverted') === 'true';
    
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

            // Aplicar inversión de orden si está activada
            let displayData = orderedData;
            if (orderInverted) {
                displayData = [...orderedData].reverse();
            }

            const documentContainer = document.getElementById('documentContainer');
            documentContainer.innerHTML = ''; // Limpiar contenedor
            
            displayData.forEach((image, index) => {
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
                                    <button class="btn btn-sm btn-secondary move-down-btn" data-filename="${image.name}" title="Mover abajo" ${index === displayData.length - 1 ? 'disabled' : ''}>
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
            
            // Actualizar la apariencia del botón de inversión de orden
            updateToggleOrderButton();
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
    
    // Si el orden está invertido, invertir la dirección de movimiento
    const actualDirection = orderInverted ? (direction === 'up' ? 'down' : 'up') : direction;
    
    if (actualDirection === 'up' && index > 0) {
        // Intercambiar con el elemento anterior
        [imageOrder[index], imageOrder[index - 1]] = [imageOrder[index - 1], imageOrder[index]];
        refreshImages();
    } else if (actualDirection === 'down' && index < imageOrder.length - 1) {
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
    // Añadirla al principio o al final según el estado de inversión
    if (orderInverted) {
        imageOrder.push(filename); // Si está invertido, añadir al final
    } else {
        imageOrder.unshift(filename); // Si no está invertido, añadir al principio
    }
    
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
function processDocument() {
    const folio = document.getElementById('studentFolio').value.trim();
    
    if (!folio) {
        alert('Por favor, ingrese un número de folio');
        return;
    }
    
    // Obtener el RUT si está disponible
    const rutNumber = document.getElementById('studentRutNumber').value.trim();
    const rutDV = document.getElementById('studentRutDV').value.trim();
    let rutParameter = '';
    
    // Si tenemos RUT completo, incluirlo como parámetro para ayudar en la búsqueda API
    if (rutNumber && rutDV) {
        rutParameter = `?rut=${rutNumber}-${rutDV}`;
    }
    
    // Mostrar indicador de carga
    const processBtn = document.getElementById('processBtn');
    const originalText = processBtn.innerHTML;
    processBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
    processBtn.disabled = true;
    
    // Llamar al endpoint para buscar el folio
    fetch(`/buscar_folio/${folio}${rutParameter}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Llenar los campos con los datos obtenidos
                document.getElementById('studentName').value = data.datos.nombre_estudiante;
                document.getElementById('avalName').value = data.datos.nombre_aval;
                document.getElementById('avalRut').value = data.datos.rut_aval;
                document.getElementById('amount').value = data.datos.monto;
                document.getElementById('avalEmail').value = data.datos.email_aval;
                
                // Mostrar la alerta si existe
                if (data.datos.mensaje_alerta) {
                    alert(data.datos.mensaje_alerta);
                }
                
                // Mostrar botón de finalizar procesado
                mostrarBotonFinalizar();
            } else {
                // Construir mensaje de error
                let errorMessage = data.error || 'No se encontró el folio especificado';
                
                // Si hay un mensaje específico de la API, mostrarlo
                if (data.api_message) {
                    errorMessage = `${errorMessage}\n\nRespuesta de la API: ${data.api_message}`;
                }
                
                // Mostrar el mensaje de error
                alert(errorMessage);
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
        selectedImages: orderInverted ? [...imageOrder].reverse() : imageOrder // Enviar el orden actual de las imágenes
    };
    
    // Llamar al endpoint para generar el PDF
    fetch('/generar_pdf', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        // Capturar el código de estado para poder manejar errores 404 y otros
        if (!response.ok) {
            return response.json().then(errorData => {
                throw { status: response.status, data: errorData };
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            let successMessage = `Documento procesado correctamente.\nPDF guardado como: ${data.filename}`;
            
            // Si hay información sobre el formato de RUT usado, agregarla
            if (data.formato_rut_usado) {
                successMessage += `\n\nFormato de RUT usado: ${data.formato_rut_usado}`;
            }
            
            alert(successMessage);
            
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
        
        // Manejar errores específicos
        if (error.status === 404 && error.data && error.data.error) {
            // Si es un error 404 (folio no encontrado) mostrar un mensaje más específico
            let errorMessage = error.data.error;
            
            // Si hay un mensaje de la API, agregarlo
            if (error.data.api_message) {
                errorMessage += '\n\nDetalle del error: ' + error.data.api_message;
                
                // Si hay un tipo de error específico, agregarlo
                if (error.data.error_type) {
                    errorMessage += `\nTipo de error: ${error.data.error_type}`;
                }
                
                // Si hay intentos con diferentes formatos, mostrarlos
                if (error.data.intentos && Array.isArray(error.data.intentos)) {
                    errorMessage += '\n\nIntentos realizados con diferentes formatos de RUT:';
                    error.data.intentos.forEach((intento, index) => {
                        errorMessage += `\n${index + 1}. ${intento}`;
                    });
                }
            }
            
            // Sugerir acciones si es un error de API
            if (error.data.error_type === 'API_NO_DATA' || error.data.error_type === 'API_REQUEST_ERROR') {
                errorMessage += '\n\nSugerencia: Verifique que el folio y RUT sean correctos y estén registrados en el sistema.';
                
                // Si contiene Bad Request, agregar una sugerencia específica sobre el formato del RUT
                if (error.data.api_message && error.data.api_message.includes('Bad Request')) {
                    errorMessage += '\n\nEs posible que el formato del RUT no sea el esperado por la API. Intente nuevamente o contacte al administrador del sistema.';
                }
            }
            
            alert(errorMessage);
        } else {
            // Otros errores
            alert('Error al generar el PDF: ' + (error.data?.error || 'Error desconocido'));
        }
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
    
    // Obtener las dos primeras imágenes según el orden actual
    const firstImageName = imageOrder[0];
    const secondImageName = imageOrder[1];
    console.log("Procesando OCR en las imágenes:", firstImageName, secondImageName);
    
    // Añadir un indicador visual temporal
    const firstImageCard = document.querySelector('.col-md-6:first-child .card');
    if (firstImageCard) {
        firstImageCard.classList.add('border-danger', 'border-5');
        setTimeout(() => {
            firstImageCard.classList.remove('border-danger', 'border-5');
        }, 2000);
    }
    
    // Llamar al endpoint que ejecutará el script con ambas imágenes
    fetch(`/ocr?filename=${firstImageName}&second_image=${secondImageName}`)
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
                
                // Crear mensaje sobre las imágenes procesadas
                let processedImagesMessage = '';
                if (data.processed_files && data.processed_files.length > 0) {
                    processedImagesMessage = `
                        <div class="alert alert-info mb-3">
                            <strong>Imágenes procesadas:</strong>
                            <ul class="mb-0 mt-2">
                                ${data.processed_files.map(file => `<li>${file}</li>`).join('')}
                            </ul>
                        </div>
                    `;
                }
                
                // Crear el contenido del texto OCR
                let ocrTextContent = '';
                if (data.ocr_texts && data.ocr_texts.length > 0) {
                    ocrTextContent = data.ocr_texts.map(ocr => `
                        <div class="mb-3">
                            <h6>Texto extraído de ${ocr.file}:</h6>
                            <pre class="ocr-result" style="white-space: pre-wrap; max-height: 300px; overflow-y: auto;">${ocr.text}</pre>
                        </div>
                    `).join('');
                } else {
                    ocrTextContent = '<div class="alert alert-warning">No se pudo extraer texto de las imágenes</div>';
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
                                ${ocrMessage}
                                ${processedImagesMessage}
                                <div class="alert alert-info mb-3">
                                    <strong>Datos extraídos:</strong>
                                    <ul class="mb-0 mt-2">
                                        <li><strong>RUT:</strong> ${data.student_data?.rut || 'No encontrado'}</li>
                                        <li><strong>Folio:</strong> ${data.student_data?.folio || 'No encontrado'}
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
                                        ${ocrTextContent}
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
                    const allText = data.ocr_texts.map(ocr => `=== ${ocr.file} ===\n${ocr.text}`).join('\n\n');
                    navigator.clipboard.writeText(allText).then(() => {
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

// Función para exportar documentos a Gesdoc
function exportarAGesdoc() {
    // Mostrar indicador de carga
    const exportBtn = document.getElementById('exportToGesdocBtn');
    const originalText = exportBtn.innerHTML;
    exportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Exportando...';
    exportBtn.disabled = true;
    
    // Llamar al endpoint para exportar a Gesdoc
    fetch('/exportar_gesdoc')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Construir mensaje para mostrar en la alerta
                let mensaje = data.mensaje + ":\n\n";
                
                // Añadir detalles de los documentos
                if (data.detalles && data.detalles.length > 0) {
                    mensaje += data.detalles.join('\n');
                }
                
                // Mostrar alerta con la información
                alert(mensaje);
            } else {
                // Mostrar mensaje de error
                alert('Error: ' + data.mensaje);
            }
        })
        .catch(error => {
            console.error('Error al exportar a Gesdoc:', error);
            alert('Error al exportar a Gesdoc');
        })
        .finally(() => {
            // Restaurar el botón
            exportBtn.innerHTML = originalText;
            exportBtn.disabled = false;
        });
}

// Añadir esta función si no existe
function initializeZoom() {
    // Implementar funcionalidad de zoom si es necesario
    // O dejar vacía si no se necesita esta funcionalidad
}

// Función para invertir el orden de las imágenes
function toggleImagesOrder() {
    // Cambiar el estado de inversión
    orderInverted = !orderInverted;
    
    // Guardar el estado en localStorage
    localStorage.setItem('orderInverted', orderInverted);
    
    // Actualizar la vista
    refreshImages();
    
    // Actualizar la apariencia del botón
    updateToggleOrderButton();
    
    // Mostrar notificación
    const message = orderInverted ? 'Orden invertido activado' : 'Orden invertido desactivado';
    showNotification(message, 'success');
}

// Función para actualizar la apariencia del botón de invertir orden
function updateToggleOrderButton() {
    const toggleOrderBtn = document.getElementById('toggleOrderBtn');
    
    if (orderInverted) {
        toggleOrderBtn.innerHTML = '<i class="fas fa-exchange-alt me-1"></i> Orden Invertido: ON';
        toggleOrderBtn.classList.remove('btn-warning');
        toggleOrderBtn.classList.add('btn-success');
    } else {
        toggleOrderBtn.innerHTML = '<i class="fas fa-exchange-alt me-1"></i> Orden Invertido: OFF';
        toggleOrderBtn.classList.remove('btn-success');
        toggleOrderBtn.classList.add('btn-warning');
    }
}

// Función para mostrar notificaciones
function showNotification(message, type = 'info') {
    // Verificar si ya existe un contenedor de notificaciones
    let notifContainer = document.getElementById('notificationContainer');
    
    if (!notifContainer) {
        // Crear el contenedor si no existe
        notifContainer = document.createElement('div');
        notifContainer.id = 'notificationContainer';
        notifContainer.style.position = 'fixed';
        notifContainer.style.top = '20px';
        notifContainer.style.right = '20px';
        notifContainer.style.zIndex = '9999';
        document.body.appendChild(notifContainer);
    }
    
    // Crear la notificación
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Añadir la notificación al contenedor
    notifContainer.appendChild(notification);
    
    // Eliminar la notificación después de 3 segundos
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}