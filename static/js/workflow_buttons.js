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
}); 