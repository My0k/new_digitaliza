// Maneja la lógica de los botones de flujo de trabajo
document.addEventListener('DOMContentLoaded', function() {
    // Definir los estados del flujo de trabajo
    const WORKFLOW_STATES = {
        OCR: 'ocr',
        FINALIZE: 'finalize'  // Combinamos PROCESS y FINALIZE en un solo estado
    };
    
    // Estado inicial
    let currentState = WORKFLOW_STATES.OCR;
    
    // Obtener el botón de flujo de trabajo y el botón Nueva Digitalización
    const workflowButton = document.getElementById('workflow-button');
    const newDigitalizationBtn = document.getElementById('newDigitalizationBtn');
    
    if (workflowButton) {
        // Configurar el botón para el estado inicial
        updateButtonState();
        
        // Asignar evento de clic
        workflowButton.addEventListener('click', handleWorkflowButtonClick);
    }
    
    // Conectar el botón de Nueva Digitalización para reiniciar el flujo
    if (newDigitalizationBtn) {
        newDigitalizationBtn.addEventListener('click', function() {
            currentState = WORKFLOW_STATES.OCR;
            updateButtonState();
            
            // Limpiar campos y resultados
            document.getElementById('projectCode').value = '';
            document.getElementById('boxNumber').value = '';
            document.getElementById('observation').value = '';
            document.getElementById('documentPresent').value = 'SI';
            
            // Ocultar resultados OCR
            const ocrResultsDiv = document.getElementById('ocr-results');
            if (ocrResultsDiv) {
                ocrResultsDiv.style.display = 'none';
            }
            
            // Actualizar imágenes
            refreshImages();
        });
    }
    
    // Función para manejar el clic en el botón de flujo de trabajo
    function handleWorkflowButtonClick() {
        switch (currentState) {
            case WORKFLOW_STATES.OCR:
                // Ejecutar OCR
                executeOCR().then(function(success) {
                    if (success) {
                        // Avanzar al siguiente estado
                        currentState = WORKFLOW_STATES.FINALIZE;
                        updateButtonState();
                    }
                });
                break;
                
            case WORKFLOW_STATES.FINALIZE:
                // Finalizar procesado (generar cuadratura)
                finalizeDocument();
                break;
        }
    }
    
    // Actualizar el estado visual del botón
    function updateButtonState() {
        if (!workflowButton) return;
        
        switch (currentState) {
            case WORKFLOW_STATES.OCR:
                workflowButton.innerHTML = '<i class="fas fa-file-alt me-2"></i> Ejecutar OCR';
                workflowButton.className = 'btn btn-primary btn-lg w-100';
                workflowButton.onclick = executeOCR;
                break;
                
            case WORKFLOW_STATES.FINALIZE:
                workflowButton.innerHTML = '<i class="fas fa-check-circle me-2"></i> Finalizar Documento';
                workflowButton.className = 'btn btn-success btn-lg w-100';  // Cambiamos a verde (success)
                workflowButton.onclick = finalizeDocument;
                break;
        }
    }
    
    // Función para ejecutar OCR
    async function executeOCR() {
        try {
            // Mostrar indicador de carga
            const workflowButton = document.getElementById('workflow-button');
            if (workflowButton) {
                workflowButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Procesando OCR...';
                workflowButton.disabled = true;
            }
            
            // Determinar el modo actual
            const isDigitalizationMode = document.getElementById('mode-digitalization').checked;
            
            // Construir la URL para OCR
            let url = '/ocr';
            
            if (isDigitalizationMode) {
                // En modo Digitalización, verificar si hay imágenes seleccionadas
                const selectedImages = Array.from(document.querySelectorAll('.image-checkbox:checked'))
                    .map(checkbox => checkbox.value);
                    
                // Solo incluir el archivo si hay uno seleccionado
                if (selectedImages.length === 1) {
                    url += `?filename=${selectedImages[0]}`;
                } else if (selectedImages.length > 1) {
                    alert('Por favor, seleccione solo una imagen para procesar con OCR');
                    
                    // Restaurar botón
                    if (workflowButton) {
                        workflowButton.innerHTML = '<i class="fas fa-file-alt me-2"></i> Ejecutar OCR';
                        workflowButton.disabled = false;
                    }
                    
                    return false;
                }
            } else {
                // En modo Indexación, incluir la carpeta actual (procesará todas las imágenes)
                const folderSelector = document.getElementById('folderSelector');
                if (folderSelector && folderSelector.value) {
                    url += `?folder=${folderSelector.value}`;
                } else {
                    alert('Por favor, seleccione una carpeta primero');
                    
                    // Restaurar botón
                    if (workflowButton) {
                        workflowButton.innerHTML = '<i class="fas fa-file-alt me-2"></i> Ejecutar OCR';
                        workflowButton.disabled = false;
                    }
                    
                    return false;
                }
            }
            
            console.log("Ejecutando OCR con URL:", url);
            
            const response = await fetch(url);
            const data = await response.json();
            
            // Restaurar botón
            if (workflowButton) {
                workflowButton.innerHTML = '<i class="fas fa-file-alt me-2"></i> Ejecutar OCR';
                workflowButton.disabled = false;
            }
            
            if (data.success) {
                // Mostrar resultados del OCR
                showOCRResults(data);
                
                // Autocompletar campos con la información extraída
                if (data.extracted_info) {
                    const projectCodeInput = document.getElementById('projectCode');
                    const boxNumberInput = document.getElementById('boxNumber');
                    const observationInput = document.getElementById('observation');
                    
                    if (projectCodeInput && data.extracted_info.project_code) {
                        projectCodeInput.value = data.extracted_info.project_code;
                    }
                    
                    if (boxNumberInput && data.extracted_info.box_number) {
                        boxNumberInput.value = data.extracted_info.box_number;
                    }
                    
                    if (observationInput && data.extracted_info.observation) {
                        observationInput.value = data.extracted_info.observation;
                    }
                }
                
                // Cambiar al estado FINALIZE (saltando PROCESS)
                currentState = WORKFLOW_STATES.FINALIZE;
                updateButtonState();
                
                return true;
            } else {
                alert('Error en OCR: ' + data.error);
                return false;
            }
        } catch (error) {
            console.error('Error ejecutando OCR:', error);
            alert('Error al ejecutar OCR');
            
            // Restaurar botón
            const workflowButton = document.getElementById('workflow-button');
            if (workflowButton) {
                workflowButton.innerHTML = '<i class="fas fa-file-alt me-2"></i> Ejecutar OCR';
                workflowButton.disabled = false;
            }
            
            return false;
        }
    }
    
    // Función para finalizar el documento
    async function finalizeDocument() {
        try {
            // Mostrar indicador de carga
            const workflowButton = document.getElementById('workflow-button');
            if (workflowButton) {
                workflowButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Procesando...';
                workflowButton.disabled = true;
            }
            
            // Obtener datos del formulario
            const projectCode = document.getElementById('projectCode').value.trim();
            const boxNumber = document.getElementById('boxNumber').value.trim();
            const documentPresent = document.getElementById('documentPresent').value;
            const observation = document.getElementById('observation').value.trim();

            // Validar que exista un código de proyecto
            if (!projectCode) {
                alert('Por favor ingrese un código de proyecto');
                workflowButton.disabled = false;
                updateButtonState();
                return;
            }
            
            // Obtener la carpeta actual
            const folderSelector = document.getElementById('folderSelector');
            const currentFolder = folderSelector ? folderSelector.value : null;
            
            if (!currentFolder) {
                alert('No se pudo determinar la carpeta actual');
                workflowButton.disabled = false;
                updateButtonState();
                return;
            }
            
            // Crear el FormData con los datos necesarios
            const formData = new FormData();
            formData.append('projectCode', projectCode);
            formData.append('boxNumber', boxNumber);
            formData.append('documentPresent', documentPresent);
            formData.append('observation', observation);
            formData.append('folder', currentFolder);
            
            // Enviar datos al servidor para generar el PDF
            const response = await fetch('/process_and_finalize', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Mostrar mensaje con la información
                const message = `
Documento procesado correctamente:
--------------------------------
Carpeta: ${currentFolder}
Archivo: ${projectCode}.pdf
Caja: ${boxNumber || 'No especificada'}
Observación: ${observation || 'Ninguna'}
Presenta documento: ${documentPresent}
--------------------------------
La carpeta ${currentFolder} ha sido eliminada.
                `;
                
                alert(message);
                
                // Mostrar mensaje de éxito
                showAlert(`Documento procesado y carpeta ${currentFolder} eliminada`, 'success');
                
                // Reiniciar el flujo de trabajo (volver al estado OCR)
                resetWorkflow();
                
                // Recargar la lista de carpetas
                await loadFolders();
                
                // Seleccionar automáticamente la siguiente carpeta disponible
                selectNextFolder();
                
                // Recargar la página para empezar fresco con la nueva carpeta
                setTimeout(() => {
                    window.location.reload();
                }, 1500); // Esperar 1.5 segundos para que el usuario vea el mensaje de éxito
                
            } else {
                // Mostrar mensaje de error
                showAlert(`Error: ${result.error || 'Error desconocido'}`, 'danger');
                workflowButton.disabled = false;
                updateButtonState();
            }
        } catch (error) {
            console.error('Error al procesar documento:', error);
            showAlert('Error de comunicación con el servidor', 'danger');
            
            // Reactivar botón
            const workflowButton = document.getElementById('workflow-button');
            if (workflowButton) {
                workflowButton.disabled = false;
                updateButtonState();
            }
        }
    }
    
    // Función para seleccionar automáticamente la siguiente carpeta disponible
    function selectNextFolder() {
        const folderSelector = document.getElementById('folderSelector');
        if (folderSelector && folderSelector.options.length > 0) {
            // Seleccionar la primera opción disponible (después de "Seleccionar carpeta")
            if (folderSelector.options.length > 1) {
                folderSelector.selectedIndex = 1;
                
                // Disparar evento de cambio para cargar las imágenes de la carpeta
                const event = new Event('change');
                folderSelector.dispatchEvent(event);
            }
        }
    }
    
    // Función para mostrar los resultados del OCR
    function showOCRResults(data) {
        // Obtener el div donde mostraremos los resultados
        let ocrResultsDiv = document.getElementById('ocr-results');
        
        // Si no existe, no podemos mostrar los resultados
        if (!ocrResultsDiv) {
            console.error("No se encontró el elemento para mostrar resultados OCR");
            return;
        }
        
        // Construir el HTML para los resultados
        let html = `
            <div class="mt-4 bg-light p-3 border rounded">
                <h4 class="mb-3">Resultados OCR (${data.images_processed} imágenes procesadas)</h4>
                <div class="accordion" id="ocrAccordion">`;
        
        // Añadir cada resultado a un acordeón
        data.ocr_results.forEach((result, index) => {
            html += `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="heading${index}">
                        <button class="accordion-button ${index > 0 ? 'collapsed' : ''}" type="button" 
                                data-bs-toggle="collapse" data-bs-target="#collapse${index}" 
                                aria-expanded="${index === 0 ? 'true' : 'false'}" aria-controls="collapse${index}">
                            <strong>${result.filename}</strong>
                            ${result.error ? ' <span class="text-danger ms-2">(Error)</span>' : ''}
                        </button>
                    </h2>
                    <div id="collapse${index}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}" 
                         aria-labelledby="heading${index}" data-bs-parent="#ocrAccordion">
                        <div class="accordion-body">
                            ${result.error ? 
                                `<div class="alert alert-danger">${result.error}</div>` : 
                                `<pre class="ocr-text">${result.text}</pre>`
                            }
                            
                            <div class="extracted-info mt-3">
                                <h5>Información extraída:</h5>
                                <ul class="list-group">
                                    <li class="list-group-item">
                                        <strong>Código de proyecto:</strong> 
                                        ${result.project_code ? result.project_code : '<span class="text-muted">No detectado</span>'}
                                    </li>
                                    <li class="list-group-item">
                                        <strong>Número de caja:</strong> 
                                        ${result.box_number ? result.box_number : '<span class="text-muted">No detectado</span>'}
                                    </li>
                                    <li class="list-group-item">
                                        <strong>Observación:</strong> 
                                        ${result.observation ? result.observation : '<span class="text-muted">No detectada</span>'}
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>`;
        });
        
        html += `</div>`;
        
        // Añadir información extraída en general
        if (data.extracted_info) {
            html += `
                <div class="mt-4 p-3 bg-light border rounded">
                    <h5>Información combinada:</h5>
                    <div class="row">
                        <div class="col-md-4">
                            <strong>Código de proyecto:</strong> 
                            ${data.extracted_info.project_code ? data.extracted_info.project_code : '<span class="text-muted">No detectado</span>'}
                        </div>
                        <div class="col-md-4">
                            <strong>Número de caja:</strong> 
                            ${data.extracted_info.box_number ? data.extracted_info.box_number : '<span class="text-muted">No detectado</span>'}
                        </div>
                        <div class="col-md-4">
                            <strong>Observación:</strong> 
                            ${data.extracted_info.observation ? data.extracted_info.observation : '<span class="text-muted">No detectada</span>'}
                        </div>
                    </div>
                </div>`;
        }
        
        // Actualizar el contenido
        ocrResultsDiv.innerHTML = html;
        
        // Mostrar el contenedor de resultados
        ocrResultsDiv.style.display = 'block';
    }

    // Manejo del toggle de modo con persistencia
    const modeDigitalization = document.getElementById('mode-digitalization');
    const modeIndexation = document.getElementById('mode-indexation');

    if (modeDigitalization && modeIndexation) {
        // Recuperar el modo guardado (o usar 'indexation' como predeterminado)
        const savedMode = localStorage.getItem('viewMode') || 'indexation';
        
        // Establecer el modo según lo guardado
        if (savedMode === 'digitalization') {
            modeDigitalization.checked = true;
            // Aplicar la configuración del modo digitalización
            document.querySelector('.navbar').classList.add('mode-digitalization');
            document.querySelector('.navbar').classList.remove('mode-indexation');
            
            // Mostrar el botón "Generar carpeta" y ocultar controles de indexación
            const generateFolderBtn = document.getElementById('generateFolderBtn');
            const digitalizationControls = document.getElementById('digitalizationControls');
            
            if (generateFolderBtn) {
                generateFolderBtn.style.display = 'block';
            }
            
            if (digitalizationControls) {
                digitalizationControls.style.display = 'block';
            }
            
            // Ocultar elementos específicos del modo indexación
            document.getElementById('workflow-button').closest('.text-center').style.display = 'none';
            document.getElementById('projectCodeContainer').style.display = 'none';
            document.getElementById('boxNumberContainer').style.display = 'none';
            document.querySelector('label[for="documentPresent"]').closest('.mb-3').style.display = 'none';
            document.querySelector('label[for="observation"]').closest('.mb-3').style.display = 'none';
            
            // Ocultar navegación de carpetas
            const folderNavigation = document.getElementById('folderNavigation');
            if (folderNavigation) {
                folderNavigation.style.display = 'none';
            }
            
            // Refrescar las imágenes para mostrarlas en orden inverso
            refreshImages(true);
            
            console.log('Modo Digitalización activado (restaurado)');
        } else {
            modeIndexation.checked = true;
            // Aplicar la configuración del modo indexación
            document.querySelector('.navbar').classList.add('mode-indexation');
            document.querySelector('.navbar').classList.remove('mode-digitalization');
            
            // Mostrar elementos específicos del modo indexación
            document.getElementById('workflow-button').closest('.text-center').style.display = 'block';
            document.getElementById('projectCodeContainer').style.display = 'block';
            document.getElementById('boxNumberContainer').style.display = 'block';
            document.querySelector('label[for="documentPresent"]').closest('.mb-3').style.display = 'block';
            document.querySelector('label[for="observation"]').closest('.mb-3').style.display = 'block';
            
            // Mostrar la navegación de carpetas
            const folderNavigation = document.getElementById('folderNavigation');
            if (folderNavigation) {
                folderNavigation.style.display = 'block';
                
                // Cargar carpetas
                loadFolders();
            }
            
            console.log('Modo Indexación activado (restaurado)');
        }
        
        // Añadir el almacenamiento del modo en los event listeners
        modeDigitalization.addEventListener('change', function() {
            if (this.checked) {
                // Guardar el modo en localStorage
                localStorage.setItem('viewMode', 'digitalization');
                
                // Recargar la página para aplicar completamente el nuevo modo
                window.location.reload();
            }
        });
        
        modeIndexation.addEventListener('change', function() {
            if (this.checked) {
                // Guardar el modo en localStorage
                localStorage.setItem('viewMode', 'indexation');
                
                // Recargar la página para aplicar completamente el nuevo modo
                window.location.reload();
            }
        });
    }

    // Función para refrescar imágenes con opción de orden inverso
    function refreshImages(reverseOrder = false) {
        fetch('/refresh' + (reverseOrder ? '?reverse=true' : ''))
        .then(response => response.json())
        .then(data => {
            updateImagesUI(data);
        })
        .catch(error => {
            console.error('Error al actualizar imágenes:', error);
        });
    }

    // Función para manejar el botón "Generar carpeta"
    document.getElementById('generateFolderBtn')?.addEventListener('click', function() {
        // Verificar primero si hay imágenes para mover
        fetch('/refresh?reverse=true')
        .then(response => response.json())
        .then(data => {
            // Si no hay imágenes, mostrar alerta
            if (!data || data.length === 0 || !data[0].path) {
                alert('No hay imágenes para mover a una nueva carpeta.');
                return;
            }
            
            // Hay imágenes, preguntar confirmación
            if (confirm('¿Desea crear una nueva carpeta y mover las imágenes actuales?')) {
                fetch('/generar_carpeta')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(`Carpeta ${data.folder} creada con éxito. Se movieron ${data.files_moved} imágenes.`);
                        
                        // Actualizar la vista después de mover las imágenes
                        refreshImages(true);
                        
                        // Liberar memoria explícitamente
                        // 1. Vaciar arreglos grandes que ya no se necesiten
                        imageOrder = [];
                        
                        // 2. Eliminar referencias a objetos DOM si hay alguna almacenada
                        const documentContainer = document.getElementById('documentContainer');
                        if (documentContainer) {
                            documentContainer.innerHTML = '';
                        }
                        
                        // 3. Limpiar cualquier caché de imágenes que hayamos creado
                        if (window.cachedImages) {
                            window.cachedImages = {};
                        }
                        
                        // 4. Forzar una recolección de basura si el navegador lo permite
                        if (window.gc) {
                            window.gc();
                        } else if (window.opera && window.opera.collect) {
                            window.opera.collect();
                        } else {
                            // En navegadores modernos, también podemos intentar
                            // una pequeña "pista" para el recolector de basura
                            const canvasTemp = document.createElement('canvas');
                            for (let i = 0; i < 50; i++) {
                                canvasTemp.width = 1000 + i;
                                canvasTemp.height = 1000 + i;
                                canvasTemp.getContext('2d');
                            }
                        }
                        
                        // 5. Opcional: Recargar la página completamente para un reinicio limpio
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000); // Recargar después de 1 segundo
                    } else {
                        alert('Error al crear carpeta: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error al crear carpeta');
                });
            }
        })
        .catch(error => {
            console.error('Error al verificar imágenes:', error);
            alert('Error al verificar si hay imágenes disponibles');
        });
    });

    // Agregar esta función para cargar carpetas en modo indexación
    function loadFolders(folderId = null) {
        let url = '/get_folders';
        if (folderId) {
            url += `?folder=${folderId}`;
        }
        
        // Mostrar indicador de carga
        const documentContainer = document.getElementById('documentContainer');
        if (documentContainer) {
            documentContainer.innerHTML = `
                <div class="col-12 text-center mt-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                    <p class="mt-2">Cargando carpetas...</p>
                </div>`;
        }
        
        fetch(url)
        .then(response => {
            // Verificar si la respuesta es exitosa (status 200-299)
            if (!response.ok) {
                throw new Error(`Error de servidor: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Datos recibidos:", data);
            
            // Verificar si hay error en la respuesta
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Actualizar el selector de carpetas
            const folderSelector = document.getElementById('folderSelector');
            
            // Verificar si hay carpetas
            if (!data.folders || data.folders.length === 0) {
                // No hay carpetas, mostrar mensaje
                if (folderSelector) {
                    folderSelector.innerHTML = '<option value="">No hay carpetas</option>';
                    folderSelector.disabled = true;
                }
                
                // Actualizar el título para indicar que no hay carpetas
                const folderTitle = document.getElementById('currentFolderTitle');
                if (folderTitle) {
                    folderTitle.textContent = 'No hay carpetas disponibles';
                    folderTitle.style.display = 'block';
                }
                
                // Limpiar el contenedor de imágenes
                if (documentContainer) {
                    documentContainer.innerHTML = `
                        <div class="col-12 text-center mt-5">
                            <div class="alert alert-info">
                                <i class="fas fa-folder-open fa-3x mb-3"></i>
                                <h4>No hay carpetas disponibles</h4>
                                <p>Primero debe crear carpetas en modo Digitalización.</p>
                            </div>
                        </div>`;
                }
                
                return;
            }
            
            // Si hay carpetas, continuar con el proceso normal
            if (folderSelector) {
                // Habilitar el selector
                folderSelector.disabled = false;
                
                // Guardar la selección actual
                const currentSelection = folderSelector.value;
                
                // Limpiar el selector
                folderSelector.innerHTML = '';
                
                // Agregar las carpetas al selector
                data.folders.forEach(folder => {
                    const option = document.createElement('option');
                    option.value = folder;
                    option.textContent = `Carpeta ${folder}`;
                    folderSelector.appendChild(option);
                });
                
                // Restaurar la selección si existe, o usar la actual
                if (data.current_folder) {
                    folderSelector.value = data.current_folder;
                } else if (currentSelection && data.folders.includes(currentSelection)) {
                    folderSelector.value = currentSelection;
                }
                
                // Actualizar el título de la carpeta actual
                const folderTitle = document.getElementById('currentFolderTitle');
                if (folderTitle && data.current_folder) {
                    folderTitle.textContent = `Estás viendo la carpeta ${data.current_folder}`;
                    folderTitle.style.display = 'block';
                } else if (folderTitle) {
                    folderTitle.style.display = 'none';
                }
            }
            
            // Actualizar las imágenes de la carpeta
            if (data.images) {
                if (data.images.length > 0) {
                    updateImagesUI(data.images);
                } else {
                    // Carpeta vacía
                    if (documentContainer) {
                        documentContainer.innerHTML = `
                            <div class="col-12 text-center mt-5">
                                <div class="alert alert-warning">
                                    <i class="fas fa-folder fa-3x mb-3"></i>
                                    <h4>Carpeta vacía</h4>
                                    <p>La carpeta ${data.current_folder} no contiene imágenes.</p>
                                </div>
                            </div>`;
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error al cargar carpetas:', error);
            
            // Mostrar mensaje de error detallado
            const documentContainer = document.getElementById('documentContainer');
            if (documentContainer) {
                documentContainer.innerHTML = `
                    <div class="col-12 text-center mt-5">
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                            <h4>Error al cargar carpetas</h4>
                            <p>${error.message || 'Ocurrió un error al intentar cargar las carpetas.'}</p>
                            <button class="btn btn-outline-danger mt-3" onclick="loadFolders()">
                                <i class="fas fa-sync me-2"></i> Reintentar
                            </button>
                        </div>
                    </div>`;
            }
            
            // Actualizar el selector de carpetas para mostrar error
            const folderSelector = document.getElementById('folderSelector');
            if (folderSelector) {
                folderSelector.innerHTML = '<option value="">Error</option>';
                folderSelector.disabled = true;
            }
        });
    }

    // Función para cambiar de carpeta cuando se selecciona una nueva
    document.getElementById('folderSelector')?.addEventListener('change', function() {
        loadFolders(this.value);
    });

    // Función para actualizar la interfaz con las imágenes
    function updateImagesUI(images) {
        const documentContainer = document.getElementById('documentContainer');
        if (!documentContainer) return;
        
        // Determinar el modo actual
        const isDigitalizationMode = document.getElementById('mode-digitalization').checked;
        
        // Si no hay imágenes, mostrar mensaje
        if (!images || images.length === 0) {
            documentContainer.innerHTML = `
                <div class="col-12 text-center mt-5">
                    <div class="alert alert-info">
                        <i class="fas fa-images fa-3x mb-3"></i>
                        <h4>No hay imágenes disponibles</h4>
                    </div>
                </div>`;
            return;
        }
        
        // Construir el HTML para las imágenes
        let imagesHTML = '';
        
        images.forEach(image => {
            // Verificar si la imagen tiene datos (podría ser null)
            const imageHtml = image.data ? 
                `<img src="${image.data}" class="card-img-top" alt="${image.name}">` : 
                `<div class="alert alert-danger text-center p-5">
                    <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                    <h5>Error al cargar imagen</h5>
                    <p class="mb-0">${image.name}</p>
                 </div>`;
            
            imagesHTML += `
            <div class="col-md-6 mb-4">
                <div class="card h-100">
                    <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                        <h5 class="card-title mb-0">${image.name}</h5>
                        <div class="document-tools">
                            ${image.path ? `
                            <button class="btn btn-sm btn-secondary move-up-btn" data-filename="${image.name}" title="Mover arriba">
                                <i class="fas fa-arrow-up"></i>
                            </button>
                            <button class="btn btn-sm btn-secondary move-down-btn" data-filename="${image.name}" title="Mover abajo">
                                <i class="fas fa-arrow-down"></i>
                            </button>
                            <button class="btn btn-sm btn-secondary move-to-first" data-filename="${image.name}" title="Mover al inicio">
                                <i class="fas fa-angle-double-up"></i>
                            </button>
                            <button class="btn btn-sm btn-secondary rotate-left" data-filename="${image.name}" title="Rotar izquierda">
                                <i class="fas fa-undo"></i>
                            </button>
                            <button class="btn btn-sm btn-secondary rotate-right" data-filename="${image.name}" title="Rotar derecha">
                                <i class="fas fa-redo"></i>
                            </button>
                            <button class="btn btn-sm btn-danger delete-image" data-filename="${image.name}" title="Eliminar">
                                <i class="fas fa-trash"></i>
                            </button>
                            ` : ''}
                        </div>
                    </div>
                    <div class="card-body d-flex flex-column">
                        <div class="flex-grow-1 overflow-hidden">
                            ${imageHtml}
                        </div>
                        <div class="mt-3">
                            ${isDigitalizationMode ? `
                            <div class="form-check mb-2">
                                <input class="form-check-input image-checkbox" type="checkbox" value="${image.name}" id="check-${image.name}">
                                <label class="form-check-label" for="check-${image.name}">
                                    Seleccionar para OCR
                                </label>
                            </div>
                            ` : ''}
                            <p class="card-text text-muted small">Modificado: ${image.modified}</p>
                        </div>
                    </div>
                </div>
            </div>`;
        });
        
        // Actualizar el contenedor de documentos
        documentContainer.innerHTML = imagesHTML;
        
        // Conectar eventos a los botones
        connectImageButtons();
    }

    // Reordenar elementos para colocar los resultados OCR debajo de los campos de entrada
    const formElement = document.getElementById('documentForm') || document.querySelector('form');
    const formContainer = formElement ? formElement.closest('.card') : null;
    
    if (formContainer) {
        // Buscar o crear el div de resultados OCR
        let ocrResultsDiv = document.getElementById('ocr-results');
        
        if (!ocrResultsDiv) {
            // Si no existe, crear el div
            ocrResultsDiv = document.createElement('div');
            ocrResultsDiv.id = 'ocr-results';
            ocrResultsDiv.style.display = 'none';
            
            // Insertar después del contenedor del formulario
            formContainer.parentNode.insertBefore(ocrResultsDiv, formContainer.nextSibling);
        } else {
            // Si ya existe, moverlo después del contenedor del formulario
            formContainer.parentNode.insertBefore(ocrResultsDiv, formContainer.nextSibling);
        }
    }

    // Función para conectar los eventos a los botones de las imágenes
    function connectImageButtons() {
        // Botones para eliminar imágenes
        document.querySelectorAll('.delete-image').forEach(button => {
            button.addEventListener('click', function() {
                const filename = this.getAttribute('data-filename');
                if (confirm(`¿Está seguro que desea eliminar la imagen ${filename}?`)) {
                    deleteImage(filename);
                }
            });
        });
        
        // Botones para rotar imágenes
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
        
        // Botones para mover imágenes
        document.querySelectorAll('.move-up-btn').forEach(button => {
            button.addEventListener('click', function() {
                const filename = this.getAttribute('data-filename');
                moveImage(filename, 'up');
            });
        });
        
        document.querySelectorAll('.move-down-btn').forEach(button => {
            button.addEventListener('click', function() {
                const filename = this.getAttribute('data-filename');
                moveImage(filename, 'down');
            });
        });
        
        document.querySelectorAll('.move-to-first').forEach(button => {
            button.addEventListener('click', function() {
                const filename = this.getAttribute('data-filename');
                moveImage(filename, 'first');
            });
        });
    }

    // Estas funciones implementan las acciones de los botones
    function deleteImage(filename) {
        fetch(`/delete/${encodeURIComponent(filename)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Determinar modo actual
                const isDigitalizationMode = document.getElementById('mode-digitalization').checked;
                if (isDigitalizationMode) {
                    refreshImages(true);
                } else {
                    // En modo indexación, recargar la carpeta actual
                    const folderSelector = document.getElementById('folderSelector');
                    if (folderSelector) {
                        loadFolders(folderSelector.value);
                    }
                }
            } else {
                alert('Error al eliminar la imagen: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al eliminar la imagen');
        });
    }

    function rotateImage(filename, direction) {
        fetch(`/rotate_image?filename=${encodeURIComponent(filename)}&direction=${direction}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Determinar modo actual
                const isDigitalizationMode = document.getElementById('mode-digitalization').checked;
                if (isDigitalizationMode) {
                    refreshImages(true);
                } else {
                    // En modo indexación, recargar la carpeta actual
                    const folderSelector = document.getElementById('folderSelector');
                    if (folderSelector) {
                        loadFolders(folderSelector.value);
                    }
                }
            } else {
                alert('Error al rotar la imagen: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al rotar la imagen');
        });
    }

    function moveImage(filename, direction) {
        fetch(`/move_image?filename=${encodeURIComponent(filename)}&direction=${direction}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Determinar modo actual
                const isDigitalizationMode = document.getElementById('mode-digitalization').checked;
                if (isDigitalizationMode) {
                    refreshImages(true);
                } else {
                    // En modo indexación, recargar la carpeta actual
                    const folderSelector = document.getElementById('folderSelector');
                    if (folderSelector) {
                        loadFolders(folderSelector.value);
                    }
                }
            } else {
                alert('Error al mover la imagen: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al mover la imagen');
        });
    }

    // Función para restablecer el flujo de trabajo
    function resetWorkflow() {
        // Limpiar los resultados OCR
        const ocrResults = document.getElementById('ocr-results');
        if (ocrResults) {
            ocrResults.style.display = 'none';
            ocrResults.innerHTML = '';
        }
        
        // Limpiar formulario
        const projectCodeInput = document.getElementById('projectCode');
        const boxNumberInput = document.getElementById('boxNumber');
        const documentPresentSelect = document.getElementById('documentPresent');
        const observationInput = document.getElementById('observation');
        
        if (projectCodeInput) projectCodeInput.value = '';
        if (boxNumberInput) boxNumberInput.value = '';
        if (documentPresentSelect) documentPresentSelect.value = 'SI';
        if (observationInput) observationInput.value = '';
        
        // Volver al estado inicial
        currentState = WORKFLOW_STATES.OCR;
        updateButtonState();
        
        // Recargar las imágenes
        refreshImages();
    }

    // Buscar el botón de actualizar (puede tener diferentes IDs según la página)
    const refreshButton = document.getElementById('refreshBtn') || 
                           document.querySelector('.refresh-btn') ||
                           document.querySelector('button[data-action="refresh"]');
    
    if (refreshButton) {
        // Sobrescribir cualquier manejador de eventos existente
        refreshButton.replaceWith(refreshButton.cloneNode(true));
        
        // Obtener la referencia actualizada del botón
        const newRefreshButton = document.getElementById('refreshBtn') || 
                                 document.querySelector('.refresh-btn') ||
                                 document.querySelector('button[data-action="refresh"]');
        
        // Añadir nuevo manejador de evento que recargue la página
        newRefreshButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Opcional: añadir un indicador visual de que se está recargando
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Actualizando...';
            this.disabled = true;
            
            // Liberar memoria antes de recargar
            clearMemoryBeforeReload();
            
            // Recargar la página
            setTimeout(function() {
                window.location.reload(true); // true para forzar recarga desde el servidor
            }, 300); // pequeño retraso para mostrar el spinner
        });
        
        console.log('Configurado botón de actualización para recargar página completa');
    }
    
    // Función para limpiar memoria antes de recargar
    function clearMemoryBeforeReload() {
        // Vaciar arreglos grandes
        if (window.imageOrder) window.imageOrder = [];
        
        // Limpiar elementos DOM innecesarios
        const documentContainer = document.getElementById('documentContainer');
        if (documentContainer) documentContainer.innerHTML = '';
        
        // Eliminar referencias a objetos grandes
        if (window.cachedImages) window.cachedImages = {};
        
        // Forzar recolección de basura si es posible
        if (window.gc) window.gc();
        
        // En todos los navegadores, esta técnica puede ayudar a liberar memoria
        const tempCanvas = document.createElement('canvas');
        for (let i = 0; i < 20; i++) {
            tempCanvas.width = 1000 + i;
            tempCanvas.height = 1000 + i;
            const ctx = tempCanvas.getContext('2d');
            ctx.fillRect(0, 0, 1, 1);
        }
    }
});