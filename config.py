import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-temporal'
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'outputs'
    STATIC_FOLDER = 'static'
    STATIC_FOLDER_IMAGES = os.path.join(STATIC_FOLDER, 'images')  # Carpeta para imágenes
    ALLOWED_EXTENSIONS = {'txt', 'csv', 'xlsx'}

    @staticmethod
    def init_app(app):
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.OUTPUT_FOLDER, exist_ok=True)
        os.makedirs(Config.STATIC_FOLDER_IMAGES, exist_ok=True)  # Crear carpeta para imágenes