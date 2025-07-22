# app.py
from flask import Flask, request, send_file, jsonify
from prueba import CubitCompressor
import os
import logging

app = Flask(__name__)
compressor = CubitCompressor()

# Configurar logging
logging.basicConfig(level=logging.INFO)

@app.route('/compress', methods=['POST'])
def compress():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Guardar en directorio temporal seguro
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    input_path = os.path.join(temp_dir, f"in_{os.urandom(4).hex()}_{file.filename}")
    output_path = os.path.join(temp_dir, f"out_{os.urandom(4).hex()}.cubit")
    
    file.save(input_path)
    
    try:
        if not compressor.compress_file(input_path, output_path):
            return jsonify({'error': 'Compression process failed'}), 500
        
        # Limpiar después de enviar
        @after_this_request
        def cleanup(response):
            try:
                os.remove(input_path)
                os.remove(output_path)
            except Exception as e:
                app.logger.error(f"Cleanup error: {str(e)}")
            return response
        
        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"{os.path.splitext(file.filename)[0]}.cubit",
            mimetype='application/octet-stream'
        )
    
    except Exception as e:
        return jsonify({'error': f"Server error: {str(e)}"}), 500

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
