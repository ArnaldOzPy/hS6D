from flask import Flask, request, send_file, after_this_request
from prueba import CubitCompressor  # Asumiendo que está en prueba.py
import os

app = Flask(__name__)
compressor = CubitCompressor()

@app.route('/')
def index():
    return send_file('index.html')  # Sirve tu interfaz HTML

@app.route('/compress', methods=['POST'])
def compress():
    if 'file' not in request.files:
        return {'error': 'No file provided'}, 400
    
    file = request.files['file']
    unique_id = os.urandom(4).hex()
    input_path = f"temp_compress_{unique_id}_{file.filename}"
    output_path = f"compressed_{unique_id}.cubit"
    
    file.save(input_path)
    
    try:
        if not compressor.compress_file(input_path, output_path):
            return {'error': 'Compression process failed'}, 500
        
        @after_this_request
        def cleanup(response):
            try:
                os.remove(input_path)
                os.remove(output_path)
            except OSError as e:
                app.logger.error(f"Cleanup error: {str(e)}")
            return response
        
        download_name = f"{os.path.splitext(file.filename)[0]}.cubit"
        return send_file(
            output_path,
            as_attachment=True,
            download_name=download_name
        )
    
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/decompress', methods=['POST'])
def decompress():
    if 'file' not in request.files:
        return {'error': 'No file provided'}, 400
    
    file = request.files['file']
    unique_id = os.urandom(4).hex()
    input_path = f"temp_decompress_{unique_id}_{file.filename}"
    output_path = f"decompressed_{unique_id}"
    
    file.save(input_path)
    
    try:
        if not compressor.decompress_file(input_path, output_path):
            return {'error': 'Decompression process failed'}, 500
        
        @after_this_request
        def cleanup(response):
            try:
                os.remove(input_path)
                os.remove(output_path)
            except OSError as e:
                app.logger.error(f"Cleanup error: {str(e)}")
            return response
        
        # Intenta mantener el nombre original sin extensión .cubit
        original_name = file.filename.replace('.cubit', '')
        return send_file(
            output_path,
            as_attachment=True,
            download_name=original_name
        )
    
    except Exception as e:
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
