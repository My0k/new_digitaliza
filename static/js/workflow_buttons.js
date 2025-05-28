// Maneja la lógica de los botones de flujo de trabajo
document.addEventListener('DOMContentLoaded', function() {
    // Definir los estados del flujo de trabajo
    const WORKFLOW_STATES = {
        OCR: 1,
        PROCESS: 2,
        FINALIZE: 3
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
                        currentState = WORKFLOW_STATES.PROCESS;
                        updateButtonState();
                    }
                });
                break;
                
            case WORKFLOW_STATES.PROCESS:
                // Procesar documento
                processDocument().then(function(success) {
                    if (success) {
                        // Avanzar al siguiente estado
                        currentState = WORKFLOW_STATES.FINALIZE;
                        updateButtonState();
                    }
                });
                break;
                
            case WORKFLOW_STATES.FINALIZE:
                // Finalizar procesado (generar cuadratura)
                generateCuadratura();
                // Reiniciar al estado inicial después de finalizar
                currentState = WORKFLOW_STATES.OCR;
                updateButtonState();
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
                break;
                
            case WORKFLOW_STATES.PROCESS:
                workflowButton.innerHTML = '<i class="fas fa-cogs me-2"></i> Procesar Documento';
                workflowButton.className = 'btn btn-success btn-lg w-100';
                break;
                
            case WORKFLOW_STATES.FINALIZE:
                workflowButton.innerHTML = '<i class="fas fa-check-circle me-2"></i> Finalizar Procesado';
                workflowButton.className = 'btn btn-warning btn-lg w-100';
                break;
        }
    }
    
    // Función para ejecutar OCR
    async function executeOCR() {
        try {
            // Recopilar los nombres de archivos seleccionados
            const selectedImages = Array.from(document.querySelectorAll('.image-checkbox:checked'))
                .map(checkbox => checkbox.value);
            
            let url = '/ocr';
            if (selectedImages.length === 1) {
                url += '?filename=' + selectedImages[0];
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success) {
                // Mostrar resultados del OCR
                showOCRResults(data);
                return true;
            } else {
                alert('Error en OCR: ' + data.error);
                return false;
            }
        } catch (error) {
            console.error('Error ejecutando OCR:', error);
            alert('Error al ejecutar OCR');
            return false;
        }
    }
    
    // Función para procesar documento
    async function processDocument() {
        try {
            // Obtener datos del formulario
            const codigo = document.getElementById('codigo').value;
            if (!codigo) {
                alert('Por favor ingrese el código del proyecto');
                return false;
            }
            
            const documentoPresente = document.querySelector('input[name="documentoPresente"]:checked').value;
            const observacion = document.getElementById('observacion').value;
            const boxNumber = document.getElementById('boxNumber').value;
            
            // Recopilar los nombres de archivos seleccionados
            const selectedImages = Array.from(document.querySelectorAll('.image-checkbox:checked'))
                .map(checkbox => checkbox.value);
            
            // Preparar datos para enviar
            const requestData = {
                codigo: codigo,
                documentoPresente: documentoPresente,
                observacion: observacion,
                selectedImages: selectedImages,
                boxNumber: boxNumber
            };
            
            // Enviar solicitud
            const response = await fetch('/procesar_documento', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                alert('Documento procesado correctamente');
                // Actualizar interfaz para reflejar que se procesó
                refreshImages();
                return true;
            } else {
                alert('Error al procesar documento: ' + data.error);
                return false;
            }
        } catch (error) {
            console.error('Error procesando documento:', error);
            alert('Error al procesar documento');
            return false;
        }
    }
    
    // Función para generar cuadratura
    function generateCuadratura() {
        window.location.href = '/generar_cuadratura';
    }
    
    // Función para mostrar resultados del OCR
    function showOCRResults(data) {
        // Si hay un campo para el código, intentar llenarlo con la matrícula encontrada
        const codigoInput = document.getElementById('codigo');
        if (codigoInput && data.matriculas_encontradas && data.matriculas_encontradas.length > 0) {
            codigoInput.value = data.matriculas_encontradas[0];
        }
        
        // Mostrar otros datos relevantes
        const ocrResultsDiv = document.getElementById('ocr-results');
        if (ocrResultsDiv) {
            let resultsHTML = '<div class="alert alert-success">';
            
            if (data.matriculas_encontradas && data.matriculas_encontradas.length > 0) {
                resultsHTML += `<p><strong>Códigos encontrados:</strong> ${data.matriculas_encontradas.join(', ')}</p>`;
            } else {
                resultsHTML += '<p><strong>No se encontraron códigos</strong></p>';
            }
            
            if (data.student_data) {
                Object.entries(data.student_data).forEach(([key, value]) => {
                    if (key !== 'todas_matriculas' && value) {
                        resultsHTML += `<p><strong>${key}:</strong> ${value}</p>`;
                    }
                });
            }
            
            resultsHTML += '</div>';
            ocrResultsDiv.innerHTML = resultsHTML;
            ocrResultsDiv.style.display = 'block';
        }
        
        // Habilitar campos de entrada para el siguiente paso
        document.querySelectorAll('.process-fields').forEach(el => {
            el.style.display = 'block';
        });
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

    // Añadir esta función para actualizar la interfaz con las imágenes
    function updateImagesUI(images) {
        const documentContainer = document.getElementById('documentContainer');
        if (!documentContainer) return;
        
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
                            <button class="btn btn-sm btn-danger delete-btn" data-filename="${image.name}" title="Eliminar">
                                <i class="fas fa-trash"></i>
                            </button>
                            <button class="btn btn-sm btn-light rotate-left" data-filename="${image.name}" title="Rotar izquierda">
                                <i class="fas fa-undo"></i>
                            </button>
                            <button class="btn btn-sm btn-light rotate-right" data-filename="${image.name}" title="Rotar derecha">
                                <i class="fas fa-redo"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-primary move-to-first" data-filename="${image.name}">
                                <i class="fas fa-arrow-up"></i> Primera
                            </button>
                            ` : ''}
                        </div>
                    </div>
                    <div class="card-body document-container">
                        ${image.data ? `
                        <img src="${image.data}" class="img-fluid document-image" alt="${image.name}">
                        ` : `
                        <div class="d-flex align-items-center justify-content-center h-100">
                            <p class="text-muted">No hay imagen disponible</p>
                        </div>
                        `}
                    </div>
                    <div class="card-footer text-muted">
                        <small>Modificado: ${image.modified}</small>
                    </div>
                </div>
            </div>
            `;
        });
        
        documentContainer.innerHTML = imagesHTML;
        
        // Conectar eventos a los botones de las imágenes
        connectImageButtons();
    }

    // Función para conectar los eventos a los botones de las imágenes
    function connectImageButtons() {
        // Botones para eliminar imágenes
        document.querySelectorAll('.delete-btn').forEach(button => {
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
    // Pueden estar definidas en otro archivo JS o aquí

    function deleteImage(filename) {
        fetch(`/delete_image?filename=${encodeURIComponent(filename)}`)
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
}); 