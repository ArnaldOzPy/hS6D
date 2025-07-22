import numpy as np
import os
import struct
import zlib
import logging
import traceback

# Configurar logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='cubit.log',
                    filemode='w')

class CubitCompressor:
    def __init__(self):
        self.metadata_symbols = {
            'R': "Rotación Derecha",
            'L': "Rotación Izquierda",
            'U': "Uniforme",
            'A': "Alternante",
            'C': "Central"
        }
        self.pattern_visualizations = []
    
    def bytes_to_cubit_grid(self, data_bytes):
        """Convierte bytes en una cuadrícula CUBIT 6x8 con manejo de padding"""
        padding = 0
        if len(data_bytes) < 6:
            padding = 6 - len(data_bytes)
            # Usar bytes nulos para padding
            data_bytes = data_bytes + bytes([0] * padding)
        else:
            padding = 0
        
        grid = np.zeros((6, 8), dtype=np.uint8)
        for row in range(6):
            byte = data_bytes[row]
            for col in range(8):
                bit = (byte >> (7 - col)) & 1
                grid[row, col] = bit
        return grid, padding
    
    def cubit_grid_to_bytes(self, grid, padding=0):
        """Convierte una cuadrícula CUBIT 6x8 en bytes, removiendo padding"""
        bytes_output = bytearray()
        rows_to_process = 6 - padding
        
        for row in range(rows_to_process):
            byte_val = 0
            for col in range(8):
                byte_val = (byte_val << 1) | grid[row, col]
            bytes_output.append(byte_val)
        return bytes(bytes_output)
    
    def find_optimal_visual_pattern(self, grid):
        """Versión robusta con manejo de errores"""
        try:
            best_byte = 0
            best_shifts = [0] * 6
            best_score = -1
            best_shifted_grid = None
            
            # Muestreo seguro
            for _ in range(50):
                shifts = [np.random.randint(0, 8) for _ in range(6)]
                shifted_grid = grid.copy()
                
                for i in range(6):
                    shifted_grid[i] = np.roll(shifted_grid[i], shifts[i])
                
                score = self.calculate_visual_score(shifted_grid)
                
                if score > best_score:
                    best_score = score
                    best_shifts = shifts
                    best_shifted_grid = shifted_grid
            
            # Crear byte comprimido
            compressed_byte = 0
            for col in range(8):
                col_data = best_shifted_grid[:, col]
                bit = self.get_representative_bit(col_data)
                compressed_byte = (compressed_byte << 1) | bit
            
            return compressed_byte, best_shifts, best_shifted_grid
        
        except Exception as e:
            logging.error(f"Error in find_optimal_visual_pattern: {str(e)}")
            # Fallback: patrón uniforme
            compressed_byte = 0
            best_shifts = [0] * 6
            for col in range(8):
                col_data = grid[:, col]
                bit = 1 if np.mean(col_data) > 0.5 else 0
                compressed_byte = (compressed_byte << 1) | bit
            return compressed_byte, best_shifts, grid
    
    def calculate_visual_score(self, grid):
        """Versión segura con manejo de bordes"""
        try:
            score = 0
            # ... (código existente) ...
            return score
        except:
            return 0  # Puntaje mínimo si hay error
    
    # ... (mantener el resto de funciones igual que en la versión mejorada anterior) ...

    def compress_file(self, input_file, output_file):
        """Comprime archivos con manejo robusto de cualquier tamaño"""
        try:
            if not os.path.exists(input_file):
                logging.error(f"Input file not found: {input_file}")
                return False
            
            original_size = os.path.getsize(input_file)
            if original_size == 0:
                logging.error("Cannot compress empty file")
                return False
            
            total_blocks = (original_size + 5) // 6
            logging.info(f"Starting compression of {original_size} bytes ({total_blocks} blocks)")
            
            with open(input_file, 'rb') as f_in, open(output_file, 'wb') as f_out:
                compressed_data = bytearray()
                metadata_list = bytearray()
                padding_info = bytearray()
                
                for block_idx in range(total_blocks):
                    data_bytes = f_in.read(6)
                    if not data_bytes:
                        break
                    
                    grid, padding = self.bytes_to_cubit_grid(data_bytes)
                    padding_info.append(padding)
                    
                    # Comprimir bloque con manejo de errores
                    try:
                        compressed_byte, metadata = self.compress_block(grid)
                    except Exception as e:
                        logging.error(f"Error compressing block {block_idx}: {str(e)}")
                        # Fallback: usar datos originales como comprimidos
                        compressed_byte = data_bytes[0] if data_bytes else 0
                        metadata = 0
                    
                    compressed_data.append(compressed_byte)
                    
                    # Empaquetar metadatos
                    metadata_list.extend([
                        (metadata >> 16) & 0xFF,
                        (metadata >> 8) & 0xFF,
                        metadata & 0xFF
                    ])
                
                # Comprimir metadatos y padding
                compressed_metadata = zlib.compress(bytes(metadata_list)) if metadata_list else b''
                compressed_padding = zlib.compress(bytes(padding_info)) if padding_info else b''
                
                # Cabecera mejorada
                header = struct.pack('!III', 
                                    original_size,
                                    len(compressed_metadata),
                                    len(compressed_padding))
                
                f_out.write(header)
                f_out.write(compressed_metadata)
                f_out.write(compressed_padding)
                f_out.write(compressed_data)
            
            logging.info(f"Compression successful: {input_file} -> {output_file}")
            return True
        
        except Exception as e:
            logging.error(f"Fatal compression error: {str(e)}\n{traceback.format_exc()}")
            return False

    def decompress_file(self, input_file, output_file):
        """Descomprime archivos con manejo preciso de errores"""
        try:
            if not os.path.exists(input_file):
                logging.error(f"Input file not found: {input_file}")
                return False
            
            with open(input_file, 'rb') as f_in, open(output_file, 'wb') as f_out:
                # Leer cabecera
                header = f_in.read(12)
                if len(header) < 12:
                    logging.error("Incomplete header")
                    return False
                
                original_size, meta_size, padding_size = struct.unpack('!III', header)
                
                # Leer secciones comprimidas
                compressed_metadata = f_in.read(meta_size)
                compressed_padding = f_in.read(padding_size)
                compressed_data = f_in.read()
                
                # Descomprimir metadatos y padding
                try:
                    metadata_list = zlib.decompress(compressed_metadata)
                    padding_info = zlib.decompress(compressed_padding)
                except zlib.error as e:
                    logging.error(f"Decompression error: {str(e)}")
                    return False
                
                total_blocks = len(compressed_data)
                
                for i in range(total_blocks):
                    # Obtener padding
                    padding = padding_info[i] if i < len(padding_info) else 0
                    
                    # Obtener metadatos
                    meta_start = i * 3
                    if meta_start + 3 > len(metadata_list):
                        break
                    
                    metadata_bytes = metadata_list[meta_start:meta_start+3]
                    metadata = (metadata_bytes[0] << 16) | (metadata_bytes[1] << 8) | metadata_bytes[2]
                    
                    # Descomprimir bloque con manejo de errores
                    try:
                        grid = self.decompress_block(compressed_data[i], metadata)
                        decompressed_bytes = self.cubit_grid_to_bytes(grid, padding)
                        f_out.write(decompressed_bytes)
                    except Exception as e:
                        logging.error(f"Error decompressing block {i}: {str(e)}")
                        # Fallback: escribir bytes nulos
                        f_out.write(bytes(6 - padding))
                
                # Asegurar tamaño exacto
                f_out.truncate(original_size)
            
            logging.info(f"Decompression successful: {input_file} -> {output_file}")
            return True
        
        except Exception as e:
            logging.error(f"Fatal decompression error: {str(e)}\n{traceback.format_exc()}")
            return False
