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

    // Comprobar si estamos en la página de digitalización
    if (window.location.pathname === '/digitalizacion') {
        setupLazyLoading();
    }

    // Si estamos en la página de indexación, configurar las imágenes
    if (window.location.pathname === '/indexacion') {
        loadFolders();
        
        // Al cargar los folders, se llamará a updateFolderImageGrid 
        // que a su vez llamará a setupImageOpening
    }
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
    // Mostrar indicador de carga
    showLoadingIndicator('imageGrid');
    
    fetch('/refresh')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                setupLazyLoading();
                updateLastUpdateTime();
            } else {
                document.getElementById('imageGrid').innerHTML = 
                    '<div class="alert alert-danger">Error al cargar las imágenes: ' + data.error + '</div>';
                console.error('Error al refrescar imágenes:', data.error);
            }
        })
        .catch(error => {
            document.getElementById('imageGrid').innerHTML = 
                '<div class="alert alert-danger">Error al conectar con el servidor</div>';
            console.error('Error al refrescar imágenes:', error);
        });
}

function setupLazyLoading() {
    // Mostrar indicador de carga mientras obtenemos las imágenes
    showLoadingIndicator('imageGrid');
    
    // Obtener todas las imágenes
    fetch('/refresh')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const images = data.images;
                
                if (images.length === 0) {
                    document.getElementById('imageGrid').innerHTML = 
                        '<div class="col-12 text-center"><p>No hay imágenes disponibles</p></div>';
                    return;
                }
                
                // Mostrar solo las primeras 12 al inicio
                updateImageGrid(images.slice(0, 12));
                
                // Si hay más de 12 imágenes, configurar lazy loading
                if (images.length > 12) {
                    // Crear un elemento marcador para el final de las imágenes visibles
                    const loadMoreMarker = document.createElement('div');
                    loadMoreMarker.id = 'load-more-marker';
                    loadMoreMarker.style.height = '50px';
                    document.getElementById('imageGrid').appendChild(loadMoreMarker);
                    
                    // Configurar observer para cargar más imágenes cuando el marcador sea visible
                    const observer = new IntersectionObserver((entries) => {
                        entries.forEach(entry => {
                            if (entry.isIntersecting) {
                                // Cargar el siguiente lote de imágenes
                                const currentCount = document.querySelectorAll('#imageGrid .col').length;
                                const nextBatch = images.slice(currentCount, currentCount + 12);
                                
                                if (nextBatch.length > 0) {
                                    // Añadir el siguiente lote al grid
                                    appendToImageGrid(nextBatch);
                                } else {
                                    // Si no hay más imágenes, desconectar el observer
                                    observer.disconnect();
                                    // Y quitar el marcador
                                    loadMoreMarker.remove();
                                }
                            }
                        });
                    }, {
                        root: null,
                        rootMargin: '100px',
                        threshold: 0.1
                    });
                    
                    // Comenzar a observar el marcador
                    observer.observe(loadMoreMarker);
                }
                
                // Actualizar el tiempo de última actualización
                updateLastUpdateTime();
            } else {
                document.getElementById('imageGrid').innerHTML = 
                    '<div class="alert alert-danger">Error al cargar las imágenes: ' + data.error + '</div>';
                console.error('Error al refrescar imágenes:', data.error);
            }
        })
        .catch(error => {
            document.getElementById('imageGrid').innerHTML = 
                '<div class="alert alert-danger">Error al conectar con el servidor</div>';
            console.error('Error al refrescar imágenes:', error);
        });
}

function updateImageGrid(imageSet) {
    const imageGrid = document.getElementById('imageGrid');
    if (!imageGrid) return;
    
    imageGrid.innerHTML = '';
    
    if (imageSet.length === 0) {
        imageGrid.innerHTML = '<div class="col-12 text-center"><p>No hay imágenes disponibles</p></div>';
        return;
    }
    
    appendToImageGrid(imageSet);
}

function appendToImageGrid(imageSet) {
    const imageGrid = document.getElementById('imageGrid');
    if (!imageGrid) return;
    
    imageSet.forEach(image => {
        const col = document.createElement('div');
        col.className = 'col-md-6';
        
        // Crear la tarjeta con la imagen
        const card = document.createElement('div');
        card.className = 'card h-100 image-card';
        
        // Crear la imagen con evento de clic
        const img = document.createElement('img');
        img.src = image.data;
        img.className = 'card-img-top';
        img.alt = image.name;
        img.loading = 'lazy';
        img.style.cursor = 'pointer'; // Cambiar cursor para indicar que es clickeable
        
        // Añadir evento de clic para mostrar imagen original
        img.addEventListener('click', function() {
            // Construir la URL para la imagen original
            const originalImageUrl = `/get_original_image?path=${encodeURIComponent(image.path)}`;
            
            // Abrir en una nueva ventana o modal
            window.open(originalImageUrl, '_blank');
        });
        
        // Añadir el resto de la tarjeta
        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';
        
        const h5 = document.createElement('h5');
        h5.className = 'card-title';
        h5.textContent = image.name;
        
        const p = document.createElement('p');
        p.className = 'card-text';
        p.textContent = image.modified;
        
        cardBody.appendChild(h5);
        cardBody.appendChild(p);
        
        // Añadir el footer de botones
        const cardFooter = document.createElement('div');
        cardFooter.className = 'card-footer text-center';
        
        const leftButton = document.createElement('button');
        leftButton.className = 'btn btn-sm btn-info me-1';
        leftButton.innerHTML = '<i class="fas fa-undo"></i>';
        leftButton.addEventListener('click', function() {
            rotateImage(image.name, 'left');
        });
        
        const rightButton = document.createElement('button');
        rightButton.className = 'btn btn-sm btn-info me-1';
        rightButton.innerHTML = '<i class="fas fa-redo"></i>';
        rightButton.addEventListener('click', function() {
            rotateImage(image.name, 'right');
        });
        
        const deleteButton = document.createElement('button');
        deleteButton.className = 'btn btn-sm btn-danger';
        deleteButton.innerHTML = '<i class="fas fa-trash"></i>';
        deleteButton.addEventListener('click', function() {
            if (confirm('¿Está seguro de que desea eliminar este documento?')) {
                deleteImage(image.name);
            }
        });
        
        cardFooter.appendChild(leftButton);
        cardFooter.appendChild(rightButton);
        cardFooter.appendChild(deleteButton);
        
        card.appendChild(img);
        card.appendChild(cardBody);
        card.appendChild(cardFooter);
        
        col.appendChild(card);
        imageGrid.appendChild(col);
    });
    
    // Asegurarse de que el marcador siempre está al final
    const loadMoreMarker = document.getElementById('load-more-marker');
    if (loadMoreMarker) {
        imageGrid.appendChild(loadMoreMarker);
    }
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
                // Mostrar mensaje de éxito en un toast o notificación menos intrusiva
                showToast('Iniciando escaneo de documentos...', 'success');
                
                // Refrescar inmediatamente
                refreshImages();
                
                // Configurar refrescos automáticos cada 10 segundos, hasta 10 veces
                let refreshCount = 0;
                const maxRefreshes = 10;
                
                // Crear o actualizar contador de imágenes
                let imageCounterElement = document.getElementById('imageCounter');
                if (!imageCounterElement) {
                    imageCounterElement = document.createElement('div');
                    imageCounterElement.id = 'imageCounter';
                    imageCounterElement.className = 'mt-2 text-center small text-muted';
                    const refreshBtn = document.getElementById('refreshBtn');
                    if (refreshBtn) {
                        refreshBtn.parentNode.insertBefore(imageCounterElement, refreshBtn.nextSibling);
                    } else {
                        document.querySelector('.card-header').appendChild(imageCounterElement);
                    }
                }
                imageCounterElement.innerHTML = 'Buscando imágenes...';
                
                const refreshInterval = setInterval(() => {
                    refreshCount++;
                    
                    // Actualizar imágenes y contador
                    fetch('/refresh')
                        .then(response => response.json())
                        .then(refreshData => {
                            if (refreshData.success) {
                                // Actualizar contador de imágenes
                                const imageCount = refreshData.images ? refreshData.images.length : 0;
                                imageCounterElement.innerHTML = `Imágenes en carpeta: <strong>${imageCount}</strong> (Refresh ${refreshCount}/${maxRefreshes})`;
                            }
                            refreshImages();
                        });
                    
                    console.log(`Refresh automático ${refreshCount} de ${maxRefreshes}`);
                    
                    // Mostrar indicador de progreso
                    scanBtn.innerHTML = `<i class="fas fa-sync fa-spin"></i> Actualizando (${refreshCount}/${maxRefreshes})`;
                    
                    // Detener después de 10 refrescos
                    if (refreshCount >= maxRefreshes) {
                        clearInterval(refreshInterval);
                        scanBtn.innerHTML = originalText;
                        scanBtn.disabled = false;
                        showToast('Actualización de imágenes completada', 'info');
                        
                        // Mantener el contador de imágenes visible
                        fetch('/refresh')
                            .then(response => response.json())
                            .then(finalData => {
                                if (finalData.success) {
                                    const finalImageCount = finalData.images ? finalData.images.length : 0;
                                    imageCounterElement.innerHTML = `Imágenes en carpeta: <strong>${finalImageCount}</strong>`;
                                }
                            });
                    }
                }, 10000); // 10 segundos
            } else {
                showToast('Error al escanear documentos: ' + data.error, 'error');
                scanBtn.innerHTML = originalText;
                scanBtn.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error al escanear:', error);
            showToast('Error al escanear documentos', 'error');
            scanBtn.innerHTML = originalText;
            scanBtn.disabled = false;
        });
}

// Función auxiliar para mostrar notificaciones tipo toast
function showToast(message, type = 'info') {
    // Si existe un sistema de toast en la aplicación, usarlo
    // Si no, podemos usar una alerta simple o implementar un toast básico
    if (typeof Toastify === 'function') {
        Toastify({
            text: message,
            duration: 3000,
            close: true,
            gravity: "top",
            position: "right",
            backgroundColor: type === 'success' ? "#4caf50" : 
                             type === 'error' ? "#f44336" : "#2196f3",
        }).showToast();
    } else {
        // Fallback a console y un alert menos intrusivo
        console.log(message);
        
        // Solo mostrar alerta para errores
        if (type === 'error') {
            alert(message);
        }
    }
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
    // Mostrar indicador de carga en el selector de carpetas
    const folderSelect = document.getElementById('folderSelect');
    if (folderSelect) {
        folderSelect.innerHTML = '<option value="">Cargando carpetas...</option>';
        folderSelect.disabled = true;
    }
    
    // Mostrar indicador en el grid de imágenes
    showLoadingIndicator('folderImageGrid');
    
    fetch('/get_folders')
        .then(response => response.json())
        .then(data => {
            updateFolderSelect(data.folders, data.current_folder);
            if (data.current_folder) {
                updateFolderImageGrid(data.images);
            } else {
                document.getElementById('folderImageGrid').innerHTML = 
                    '<div class="alert alert-info">Seleccione una carpeta para ver sus imágenes</div>';
            }
        })
        .catch(error => {
            console.error('Error al cargar carpetas:', error);
            document.getElementById('folderImageGrid').innerHTML = 
                '<div class="alert alert-danger">Error al cargar las imágenes. Por favor, intente nuevamente.</div>';
            
            // Restaurar selector de carpetas
            if (folderSelect) {
                folderSelect.innerHTML = '<option value="">Error al cargar carpetas</option>';
                folderSelect.disabled = false;
            }
        });
}

function updateFolderSelect(folders, currentFolder) {
    const folderSelect = document.getElementById('folderSelect');
    if (!folderSelect) return;
    
    folderSelect.innerHTML = '';
    folderSelect.disabled = false;
    
    if (folders.length === 0) {
        folderSelect.innerHTML = '<option value="">No hay carpetas disponibles</option>';
        folderSelect.disabled = true;
        return;
    }
    
    // Opción por defecto
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Seleccione una carpeta';
    folderSelect.appendChild(defaultOption);
    
    // Añadir cada carpeta como una opción
    folders.forEach(folder => {
        const option = document.createElement('option');
        option.value = folder;
        option.textContent = `Carpeta ${folder}`;
        option.selected = folder === currentFolder;
        folderSelect.appendChild(option);
    });
    
    // Evento al cambiar de carpeta
    folderSelect.onchange = function() {
        if (this.value) {
            loadFolderImages(this.value);
        } else {
            document.getElementById('folderImageGrid').innerHTML = 
                '<div class="alert alert-info">Seleccione una carpeta para ver sus imágenes</div>';
        }
    };
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
        col.className = 'col-md-4 mb-3';
        col.innerHTML = `
            <div class="card h-100">
                <img src="${image.data}" class="card-img-top indexing-image" alt="${image.name}" 
                     loading="lazy" data-original-path="${image.path || ''}" data-full-size-url="${image.original_url || image.data}">
                <div class="card-body">
                    <h6 class="card-title">${image.name}</h6>
                    <p class="card-text small">${image.modified}</p>
                </div>
            </div>
        `;
        imageGrid.appendChild(col);
    });
    
    // Configurar las imágenes para que se abran en una nueva pestaña
    setupImageOpening();
}

function loadFolderImages(folderId) {
    // Mostrar indicador de carga
    showLoadingIndicator('folderImageGrid');
    
    fetch(`/get_folders?folder=${folderId}`)
        .then(response => response.json())
        .then(data => {
            updateFolderImageGrid(data.images);
        })
        .catch(error => {
            console.error('Error al cargar imágenes de la carpeta:', error);
            document.getElementById('folderImageGrid').innerHTML = 
                '<div class="alert alert-danger">Error al cargar las imágenes. Por favor, intente nuevamente.</div>';
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

// Función para generar una nueva carpeta
function generateFolder() {
    // Confirmar antes de crear la carpeta
    Swal.fire({
        title: '¿Crear nueva carpeta?',
        text: 'Se moverán todas las imágenes actuales a una nueva carpeta numerada',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Sí, crear carpeta',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            // Mostrar carga
            Swal.fire({
                title: 'Creando carpeta...',
                text: 'Espere un momento mientras se procesa',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });
            
            // Hacer petición al servidor para generar carpeta
            fetch('/generar_carpeta', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    Swal.fire({
                        icon: 'success',
                        title: 'Carpeta creada correctamente',
                        text: `Se ha creado la carpeta ${data.folder_name}`,
                        confirmButtonText: 'Aceptar'
                    }).then(() => {
                        // Recargar imágenes
                        refreshImages();
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
            });
        }
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

// Modificar la función para extraer solo el ID de la carpeta
function generateIndexedPdf() {
    // Obtener los valores del formulario
    const folderSelect = document.getElementById('folderSelect');
    const folderId = folderSelect.value;
    
    // Extraer solo el ID de la carpeta (sin el prefijo "Carpeta ")
    const folderFullName = folderSelect.options[folderSelect.selectedIndex].text;
    const folderName = folderFullName.replace('Carpeta ', ''); // Eliminar el prefijo "Carpeta "
    
    const projectCode = document.getElementById('projectCode').value;
    const boxNumber = document.getElementById('boxNumber').value;
    const documentPresent = document.querySelector('input[name="documentPresent"]:checked').value;
    const observation = document.getElementById('observation').value;
    
    // Validar que se haya seleccionado una carpeta
    if (!folderId) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Debe seleccionar una carpeta para indexar'
        });
        return;
    }
    
    // Validar el código de proyecto (campo obligatorio)
    if (!projectCode) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Debe ingresar un código de proyecto'
        });
        return;
    }
    
    // Mostrar indicador de carga
    Swal.fire({
        title: 'Procesando',
        text: 'Indexando documento...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    // Preparar datos para enviar
    const formData = new FormData();
    formData.append('folder_id', folderId);
    formData.append('folder_name', folderName); // Enviar solo el ID de la carpeta
    formData.append('project_code', projectCode);
    formData.append('box_number', boxNumber);
    formData.append('document_present', documentPresent);
    formData.append('observation', observation);
    
    // Enviar petición al servidor
    fetch('/actualizar_indexacion', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: 'Éxito',
                text: 'Documento indexado correctamente'
            });
            
            // Limpiar el formulario después de indexar exitosamente
            document.getElementById('projectCode').value = '';
            document.getElementById('boxNumber').value = '';
            document.getElementById('observation').value = '';
            document.getElementById('documentPresentYes').checked = true;
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.error || 'No se pudo indexar el documento'
            });
        }
    })
    .catch(error => {
        console.error('Error al indexar documento:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Ocurrió un error al procesar la solicitud'
        });
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

// Función para cargar carpetas en la vista de procesamiento
function loadProcessFolders() {
    fetch('/get_process_folders')
        .then(response => response.json())
        .then(data => {
            updateProcessFoldersList(data.folders);
        })
        .catch(error => {
            console.error('Error al cargar carpetas para procesar:', error);
        });
}

// Función para actualizar la lista de carpetas para procesar
function updateProcessFoldersList(folders) {
    const folderTableBody = document.querySelector('#processTable tbody');
    if (!folderTableBody) return;
    
    folderTableBody.innerHTML = '';
    
    if (folders.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="5" class="text-center">No hay carpetas disponibles</td>';
        folderTableBody.appendChild(row);
        return;
    }
    
    folders.forEach(folder => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${folder.name}</td>
            <td>${folder.created_at || '-'}</td>
            <td>${folder.image_count || 'Desconocido'}</td>
            <td><span class="badge bg-${folder.processed ? 'success' : 'secondary'}">${folder.processed ? 'Procesado' : 'Pendiente'}</span></td>
            <td>
                <button class="btn btn-sm btn-primary process-folder-btn" data-folder="${folder.name}" ${folder.processed ? 'disabled' : ''}>
                    <i class="fas fa-magic me-1"></i> Procesar
                </button>
            </td>
        `;
        folderTableBody.appendChild(row);
    });
    
    // Añadir eventos a los botones
    document.querySelectorAll('.process-folder-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const folder = this.getAttribute('data-folder');
            processFolder(folder);
        });
    });
}

// Función para procesar una carpeta específica
function processFolder(folder) {
    Swal.fire({
        icon: 'info',
        title: 'En proceso',
        text: `La funcionalidad de procesamiento para la carpeta ${folder} se está implementando`
    });
}

// Función para hacer que las imágenes en la indexación se abran en una nueva pestaña
function setupImageOpening() {
    // Seleccionar todas las imágenes en la vista de indexación
    const indexImages = document.querySelectorAll('.indexing-image');
    
    indexImages.forEach(img => {
        img.style.cursor = 'pointer'; // Cambiar el cursor para indicar que es clickeable
        
        img.addEventListener('click', function(e) {
            // Prevenir cualquier comportamiento predeterminado
            e.stopPropagation();
            
            // Obtener la URL de la imagen en tamaño completo
            const fullSizeUrl = this.getAttribute('data-full-size-url');
            const originalPath = this.getAttribute('data-original-path');
            
            // Si existe una ruta original, obtener la imagen a través de la API
            if (originalPath) {
                // Construir una URL para obtener la imagen original
                const imageRequestUrl = `/get_original_image?path=${encodeURIComponent(originalPath)}`;
                
                // Abrir la URL en una nueva pestaña
                window.open(imageRequestUrl, '_blank');
            } else if (fullSizeUrl) {
                // Si hay una URL de tamaño completo, usarla
                window.open(fullSizeUrl, '_blank');
            } else {
                // Como respaldo, usar la URL de la miniatura
                window.open(this.src, '_blank');
            }
        });
    });
}

// Función para mostrar un indicador de carga
function showLoadingIndicator(elementId) {
    const container = document.getElementById(elementId);
    if (!container) return;
    
    container.innerHTML = `
        <div class="text-center p-5 w-100">
            <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                <span class="visually-hidden">Cargando...</span>
            </div>
            <p class="mt-3">Cargando imágenes...</p>
        </div>
    `;
}

// Función para crear una nueva carpeta
function createNewFolder() {
    // Mostrar un indicador de carga o un mensaje
    Swal.fire({
        title: 'Creando carpeta',
        text: 'Por favor espere...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    // Hacer una solicitud al servidor para crear una nueva carpeta
    fetch('/create_new_folder', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Mostrar un mensaje de éxito con el nombre de la carpeta
            Swal.fire({
                icon: 'success',
                title: 'Carpeta creada',
                text: `Se ha creado la carpeta: ${data.folder_name}`,
                confirmButtonText: 'Aceptar'
            }).then((result) => {
                // Recargar la página o actualizar la lista de carpetas
                if (result.isConfirmed) {
                    window.location.reload();
                }
            });
        } else {
            // Mostrar un mensaje de error
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.error || 'No se pudo crear la carpeta'
            });
        }
    })
    .catch(error => {
        console.error('Error al crear carpeta:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Ocurrió un error al crear la carpeta'
        });
    });
}