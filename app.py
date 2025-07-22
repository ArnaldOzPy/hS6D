
from flask import Flask, request, send_file, after_this_request
from cubit_compressor import CubitCompressor  # Importa la clase mejorada
import os

app = Flask(__name__)
compressor = CubitCompressor()

@app.route('/compress', methods=['POST'])
def compress():
    if 'file' not in request.files:
        return {'error': 'No file provided'}, 400
    
    file = request.files['file']
    input_path = f"temp_{os.urandom(8).hex()}_{file.filename}"
    output_path = f"compressed_{input_path}.cubit"
    
    file.save(input_path)
    
    try:
        success = compressor.compress_file(input_path, output_path)
        if not success:
            return {'error': 'Compression failed'}, 500
        
        @after_this_request
        def cleanup(response):
            try:
                os.remove(input_path)
                os.remove(output_path)
            except:
                pass
            return response
        
        return send_file(output_path, as_attachment=True, download_name=f"{file.filename}.cubit")
    
    except Exception as e:
        return {'error': str(e)}, 500

# Implementar similar para /decompress
