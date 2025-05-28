import tkinter as tk
import pyautogui
import time
import win32gui
import re
import win32con

def find_window_with_title(title_pattern):
    """Encuentra ventanas que coinciden con un patrón en su título"""
    result = []
    
    def callback(hwnd, pattern):
        window_title = win32gui.GetWindowText(hwnd)
        if re.search(pattern, window_title, re.IGNORECASE) and win32gui.IsWindowVisible(hwnd):
            result.append((hwnd, window_title))
        return True
    
    win32gui.EnumWindows(callback, title_pattern)
    return result

class MouseCoordinatesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Coordenadas del Mouse")
        self.root.geometry("300x200")
        self.root.attributes('-topmost', True)  # Mantener ventana siempre al frente
        
        # Frame principal
        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Etiqueta para mostrar coordenadas
        self.coords_label = tk.Label(
            main_frame, 
            text="Coordenadas: (0, 0)", 
            font=("Arial", 14)
        )
        self.coords_label.pack(pady=20)
        
        # Botón para activar ventana "Scan Validation"
        self.activate_button = tk.Button(
            main_frame, 
            text="Activar ventana y hacer clic",
            command=self.activate_and_click
        )
        self.activate_button.pack(pady=10)
        
        # Etiqueta de estado
        self.status_label = tk.Label(main_frame, text="", fg="blue")
        self.status_label.pack(pady=5)
        
        # Iniciar actualización de coordenadas
        self.update_coordinates()
    
    def activate_and_click(self):
        """Activa una ventana que contenga 'Scan Validation' y hace clic en coordenadas relativas"""
        windows = find_window_with_title("Scan Validation")
        
        if windows:
            hwnd, title = windows[0]  # Tomar la primera ventana encontrada
            try:
                # Activar la ventana encontrada
                win32gui.SetForegroundWindow(hwnd)
                
                # Obtener la posición y tamaño de la ventana
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                
                # Calcular las coordenadas absolutas a partir de las relativas
                # Añadir un pequeño retraso para asegurar que la ventana está activa
                time.sleep(0.5)
                
                # Las coordenadas que queremos hacer clic (47, 61) relativas a la ventana
                x_rel, y_rel = 47, 61
                
                # Convertir a coordenadas absolutas
                x_abs = left + x_rel
                y_abs = top + y_rel
                
                # Hacer clic en las coordenadas calculadas
                pyautogui.click(x_abs, y_abs)
                
                self.status_label.config(
                    text=f"Ventana activada y clic en ({x_rel}, {y_rel})", 
                    fg="green"
                )
            except Exception as e:
                self.status_label.config(
                    text=f"Error: {str(e)}", 
                    fg="red"
                )
        else:
            self.status_label.config(
                text="No se encontró ventana 'Scan Validation'", 
                fg="red"
            )
    
    def update_coordinates(self):
        """Actualiza las coordenadas del mouse cada 100ms"""
        x, y = pyautogui.position()
        self.coords_label.config(text=f"Coordenadas: ({x}, {y})")
        self.root.after(100, self.update_coordinates)  # Actualizar cada 100ms

if __name__ == "__main__":
    root = tk.Tk()
    app = MouseCoordinatesApp(root)
    root.mainloop()
