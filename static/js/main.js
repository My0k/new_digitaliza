// Evento para mover una imagen a la primera posición
$(document).on('click', '.move-to-first', function() {
    const filename = $(this).data('filename');
    const imageContainer = $(this).closest('.image-container');
    
    // Animación y efecto visual
    imageContainer.fadeOut(300, function() {
        // Mover al principio de la galería
        const gallery = $('.image-gallery');
        imageContainer.prependTo(gallery);
        
        // Mostrar nuevamente con animación
        imageContainer.fadeIn(300);
        
        // Notificación
        showToast('Imagen movida a la primera posición', 'success');
    });
    
    // Opcionalmente: si quieres mantener este orden en el servidor
    // Para implementaciones más complejas, puedes agregar un endpoint en Flask
    // $.get(`/move_to_first/${filename}`);
});

// Función auxiliar para mostrar notificaciones
function showToast(message, type = 'info') {
    const toast = $(`<div class="toast ${type}" role="alert">${message}</div>`);
    $('.toast-container').append(toast);
    toast.fadeIn();
    setTimeout(() => toast.fadeOut(() => toast.remove()), 3000);
}

// Asegúrate de que exista un contenedor para las notificaciones
$(document).ready(function() {
    if ($('.toast-container').length === 0) {
        $('body').append('<div class="toast-container"></div>');
    }
    
    // Añadir estilos para las notificaciones si no existen
    if ($('#toast-styles').length === 0) {
        $('head').append(`
            <style id="toast-styles">
                .toast-container {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    z-index: 1050;
                }
                .toast {
                    min-width: 250px;
                    margin-top: 10px;
                    padding: 15px;
                    border-radius: 4px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.2);
                    display: none;
                }
                .toast.success {
                    background-color: #d4edda;
                    color: #155724;
                }
                .toast.info {
                    background-color: #d1ecf1;
                    color: #0c5460;
                }
                .toast.warning {
                    background-color: #fff3cd;
                    color: #856404;
                }
                .toast.error {
                    background-color: #f8d7da;
                    color: #721c24;
                }
            </style>
        `);
    }
}); 