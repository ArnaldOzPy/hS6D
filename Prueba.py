import numpy as np
import os
import struct
import zlib
import logging

# Configurar logging para depuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CubitCompressor:
    def __init__(self):
        self.metadata_symbols = {
            'R': "Rotación Derecha",
            'L': "Rotación Izquierda",
            'U': "Uniforme",
            'A': "Alternante",
            'C': "Central"
        }
        # No necesitamos guardar metadata en archivo para compresión
        self.pattern_visualizations = []
    
    def bytes_to_cubit_grid(self, data_bytes):
        """Convierte 6 bytes en una cuadrícula CUBIT 6x8, con padding si es necesario"""
        padding = 0
        if len(data_bytes) < 6:
            padding = 6 - len(data_bytes)
            data_bytes = data_bytes + bytes([0] * padding)
        
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
        for row in range(6 - padding):  # Remover filas de padding
            byte_val = 0
            for col in range(8):
                byte_val = (byte_val << 1) | grid[row, col]
            bytes_output.append(byte_val)
        return bytes(bytes_output)
    
    def find_optimal_visual_pattern(self, grid):
        """Encuentra el mejor patrón visual mediante desplazamientos"""
        best_byte = 0
        best_shifts = [0] * 6
        best_score = -1
        best_shifted_grid = None
        
        # Probar combinaciones de desplazamientos
        for _ in range(100):  # Muestreo de 100 configuraciones
            shifts = [np.random.randint(0, 8) for _ in range(6)]
            shifted_grid = grid.copy()
            
            # Aplicar desplazamientos
            for i in range(6):
                shifted_grid[i] = np.roll(shifted_grid[i], shifts[i])
            
            # Calcular puntaje basado en patrones visuales
            score = self.calculate_visual_score(shifted_grid)
            
            if score > best_score:
                best_score = score
                best_shifts = shifts
                best_shifted_grid = shifted_grid
        
        # Crear byte comprimido desde el mejor patrón
        compressed_byte = 0
        for col in range(8):
            col_data = best_shifted_grid[:, col]
            bit = self.get_representative_bit(col_data)
            compressed_byte = (compressed_byte << 1) | bit
        
        return compressed_byte, best_shifts, best_shifted_grid
    
    def calculate_visual_score(self, grid):
        """Calcula puntaje basado en patrones visuales reconocibles"""
        score = 0
        
        # Patrones de columnas
        for col in range(8):
            col_data = grid[:, col]
            
            # Patrón uniforme
            if np.all(col_data == col_data[0]):
                score += 10
                
            # Patrón alternante
            if self.is_alternating(col_data):
                score += 8
                
            # Patrón central
            if self.is_central_pattern(col_data):
                score += 6
        
        # Patrones de filas
        for row in range(6):
            row_data = grid[row, :]
            
            # Secuencias largas
            current_bit = row_data[0]
            run_length = 1
            max_run = 1
            for i in range(1, 8):
                if row_data[i] == current_bit:
                    run_length += 1
                    if run_length > max_run:
                        max_run = run_length
                else:
                    current_bit = row_data[i]
                    run_length = 1
            
            score += max_run
        
        return score
    
    def is_alternating(self, data):
        """Verifica si los datos tienen patrón alternante"""
        for i in range(1, len(data)):
            if data[i] == data[i-1]:
                return False
        return True
    
    def is_central_pattern(self, data):
        """Verifica si los datos tienen patrón central"""
        if len(data) < 5:
            return False
        return data[2] == data[3] and data[2] != data[0] and data[2] != data[-1]
    
    def get_representative_bit(self, col_data):
        """Obtiene el bit representativo de una columna"""
        # Estrategia: Valor dominante o central
        if np.sum(col_data) >= 4:  # Mayoría de 1s
            return 1
        elif np.sum(col_data) <= 2:  # Mayoría de 0s
            return 0
        else:  # Sin mayoría clara, usar valor central
            return col_data[3]
    
    def compress_block(self, grid):
        """Comprime un bloque de cuadrícula a 8 bits + metadatos"""
        compressed_byte, shifts, _ = self.find_optimal_visual_pattern(grid)
        
        # Codificar metadatos (desplazamientos)
        metadata = 0
        for shift in shifts:
            metadata = (metadata << 3) | shift  # 3 bits por desplazamiento
        
        return compressed_byte, metadata
    
    def decompress_block(self, compressed_byte, metadata):
        """Reconstruye un bloque desde 8 bits comprimidos y metadatos"""
        # Decodificar desplazamientos
        shifts = []
        for _ in range(6):
            shift = metadata & 0b111
            shifts.insert(0, shift)
            metadata >>= 3
        
        # Crear cuadrícula desde el byte comprimido
        grid = np.zeros((6, 8), dtype=np.uint8)
        bits = [(compressed_byte >> i) & 1 for i in range(7, -1, -1)]
        
        # Construir columnas basadas en el bit representativo
        for col in range(8):
            bit = bits[col]
            
            # Crear patrón más probable (ajustable)
            if col % 2 == 0:
                # Patrón uniforme
                grid[:, col] = bit
            else:
                # Patrón central
                grid[2:4, col] = bit
                grid[0:2, col] = 1 - bit
                grid[4:6, col] = 1 - bit
        
        # Revertir desplazamientos
        for i in range(6):
            grid[i] = np.roll(grid[i], -shifts[i])
        
        return grid
    
    def compress_file(self, input_file, output_file):
        """Comprime archivos con manejo robusto de cualquier tipo de dato"""
        try:
            original_size = os.path.getsize(input_file)
            total_blocks = (original_size + 5) // 6  # Bloques necesarios
            
            with open(input_file, 'rb') as f_in, open(output_file, 'wb') as f_out:
                compressed_data = bytearray()
                metadata_list = bytearray()
                padding_info = bytearray()  # Almacenar padding por bloque
                
                for _ in range(total_blocks):
                    data_bytes = f_in.read(6)
                    grid, padding = self.bytes_to_cubit_grid(data_bytes)
                    padding_info.append(padding)
                    
                    # Comprimir bloque
                    compressed_byte, metadata = self.compress_block(grid)
                    compressed_data.append(compressed_byte)
                    
                    # Empaquetar metadatos
                    metadata_list.extend([
                        (metadata >> 16) & 0xFF,
                        (metadata >> 8) & 0xFF,
                        metadata & 0xFF
                    ])
                
                # Comprimir metadatos y padding
                compressed_metadata = zlib.compress(bytes(metadata_list))
                compressed_padding = zlib.compress(bytes(padding_info))
                
                # Cabecera mejorada
                header = struct.pack('!III', 
                                    original_size,
                                    len(compressed_metadata),
                                    len(compressed_padding))
                
                f_out.write(header)
                f_out.write(compressed_metadata)
                f_out.write(compressed_padding)
                f_out.write(compressed_data)
            
            logging.info(f"Compresión exitosa: {input_file} -> {output_file}")
            compression_ratio = os.path.getsize(output_file) / original_size
            logging.info(f"Ratio de compresión: {compression_ratio:.2%}")
            return True
        
        except Exception as e:
            logging.error(f"Error en compresión: {str(e)}", exc_info=True)
            return False
    
    def decompress_file(self, input_file, output_file):
        """Descomprime archivos con manejo preciso de padding y metadatos"""
        try:
            with open(input_file, 'rb') as f_in, open(output_file, 'wb') as f_out:
                # Leer cabecera
                header = f_in.read(12)
                if len(header) != 12:
                    raise ValueError("Cabecera incompleta")
                
                original_size, meta_size, padding_size = struct.unpack('!III', header)
                
                # Leer secciones comprimidas
                compressed_metadata = f_in.read(meta_size)
                compressed_padding = f_in.read(padding_size)
                compressed_data = f_in.read()
                
                # Descomprimir metadatos y padding
                metadata_list = zlib.decompress(compressed_metadata)
                padding_info = zlib.decompress(compressed_padding)
                
                total_blocks = len(compressed_data)
                
                for i in range(total_blocks):
                    # Obtener metadatos del bloque
                    meta_start = i * 3
                    if meta_start + 3 > len(metadata_list):
                        break
                    
                    metadata_bytes = metadata_list[meta_start:meta_start+3]
                    metadata = (metadata_bytes[0] << 16) | (metadata_bytes[1] << 8) | metadata_bytes[2]
                    
                    # Descomprimir bloque
                    grid = self.decompress_block(compressed_data[i], metadata)
                    
                    # Convertir a bytes (manejar padding)
                    padding = padding_info[i] if i < len(padding_info) else 0
                    decompressed_bytes = self.cubit_grid_to_bytes(grid, padding)
                    
                    # Escribir datos descomprimidos
                    f_out.write(decompressed_bytes)
                
                # Asegurar tamaño exacto
                f_out.truncate(original_size)
            
            logging.info(f"Descompresión exitosa: {input_file} -> {output_file}")
            return True
        
        except Exception as e:
            logging.error(f"Error en descompresión: {str(e)}", exc_info=True)
            return False

# Prueba de integridad
if __name__ == "__main__":
    compressor = CubitCompressor()
    
    # Crear archivo de prueba
    TEST_FILE = "test_data.bin"
    with open(TEST_FILE, "wb") as f:
        f.write(b"\xAA\x55\xAA\x55\xAA\x55")  # Patrón alternante
        f.write(b"\xFF\x00\xFF\x00\xFF\x00")  # Alto contraste
        f.write(os.urandom(1024))  # 1KB de datos aleatorios
    
    # Prueba de compresión/descompresión
    COMPRESSED_FILE = "test_compressed.cubit"
    DECOMPRESSED_FILE = "test_decompressed.bin"
    
    # Comprimir
    if compressor.compress_file(TEST_FILE, COMPRESSED_FILE):
        # Descomprimir
        if compressor.decompress_file(COMPRESSED_FILE, DECOMPRESSED_FILE):
            # Verificar integridad
            with open(TEST_FILE, "rb") as orig, open(DECOMPRESSED_FILE, "rb") as dec:
                original = orig.read()
                decompressed = dec.read()
                if original == decompressed:
                    print("✓ Integridad verificada: Los archivos son idénticos")
                    print(f"Tamaño original: {len(original)} bytes")
                    print(f"Tamaño comprimido: {os.path.getsize(COMPRESSED_FILE)} bytes")
                    print(f"Ratio: {os.path.getsize(COMPRESSED_FILE)/len(original):.2%}")
                else:
                    print("✗ Error: Los archivos son diferentes")
                    # Encontrar primera diferencia
                    for i in range(min(len(original), len(decompressed))):
                        if original[i] != decompressed[i]:
                            print(f"Primera diferencia en byte {i}: {original[i]} vs {decompressed[i]}")
                            break
