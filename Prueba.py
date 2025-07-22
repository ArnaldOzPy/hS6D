import numpy as np
import os
import matplotlib.pyplot as plt
import zlib
import struct  # Import faltante - esencial para compresión/descompresión

class CubitCompressor:
    def __init__(self):
        self.metadata_symbols = {
            'R': "Rotación Derecha",
            'L': "Rotación Izquierda",
            'U': "Uniforme",
            'A': "Alternante",
            'C': "Central"
        }
        self.save_metadata_symbols()
        self.pattern_visualizations = []
    
    def save_metadata_symbols(self, filename="CUBIT_METADATA.sis"):
        with open(filename, 'w') as f:
            for symbol, meaning in self.metadata_symbols.items():
                f.write(f"{symbol}={meaning}\n")
    
    def bytes_to_cubit_grid(self, data_bytes):
        """Convierte 6 bytes en una cuadrícula CUBIT 6x8"""
        if len(data_bytes) < 6:
            data_bytes = data_bytes + bytes([0] * (6 - len(data_bytes)))
        
        grid = np.zeros((6, 8), dtype=np.uint8)
        for row in range(6):
            byte = data_bytes[row]
            for col in range(8):
                bit = (byte >> (7 - col)) & 1
                grid[row, col] = bit
        return grid
    
    def cubit_grid_to_bytes(self, grid):
        """Convierte una cuadrícula CUBIT 6x8 en 6 bytes"""
        bytes_output = bytearray()
        for row in range(6):
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
    
    def compress_block(self, data_bytes):
        """Comprime un bloque de 6 bytes a 8 bits + metadatos"""
        grid = self.bytes_to_cubit_grid(data_bytes)
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
        
        return self.cubit_grid_to_bytes(grid)
    
    def compress_file(self, input_file, output_file):
        """Comprime un archivo usando patrones visuales CUBIT"""
        self.save_metadata_symbols()
        
        with open(input_file, 'rb') as f_in, open(output_file, 'wb') as f_out:
            compressed_data = bytearray()
            metadata_list = bytearray()
            
            while True:
                data_bytes = f_in.read(6)
                if not data_bytes:
                    break
                
                # Comprimir bloque
                compressed_byte, metadata = self.compress_block(data_bytes)
                compressed_data.append(compressed_byte)
                
                # Empaquetar metadatos en 3 bytes (18 bits)
                metadata_list.extend([
                    (metadata >> 16) & 0xFF,
                    (metadata >> 8) & 0xFF,
                    metadata & 0xFF
                ])
            
            # Comprimir metadatos adicionalmente
            compressed_metadata = zlib.compress(bytes(metadata_list))
            
            # Escribir cabecera con información de compresión
            header = struct.pack('!III', 
                                len(compressed_data), 
                                len(compressed_metadata),
                                os.path.getsize(input_file))
            f_out.write(header)
            f_out.write(compressed_data)
            f_out.write(compressed_metadata)
    
    def decompress_file(self, input_file, output_file):
        """Descomprime un archivo comprimido con CUBIT"""
        with open(input_file, 'rb') as f_in, open(output_file, 'wb') as f_out:
            # Leer cabecera
            header = f_in.read(12)
            if len(header) != 12:
                raise ValueError("Archivo corrupto: cabecera incompleta")
                
            data_size, meta_size, original_size = struct.unpack('!III', header)
            
            # Leer datos comprimidos
            compressed_data = f_in.read(data_size)
            compressed_metadata = f_in.read(meta_size)
            
            # Descomprimir metadatos
            metadata_list = zlib.decompress(compressed_metadata)
            
            # Procesar cada bloque
            for i in range(0, len(compressed_data)):
                # Cada bloque de metadatos ocupa 3 bytes
                meta_start = i * 3
                if meta_start + 3 > len(metadata_list):
                    break
                
                metadata_bytes = metadata_list[meta_start:meta_start+3]
                metadata = (metadata_bytes[0] << 16) | (metadata_bytes[1] << 8) | metadata_bytes[2]
                
                # Descomprimir bloque
                decompressed_block = self.decompress_block(compressed_data[i], metadata)
                f_out.write(decompressed_block)
            
            # Truncar al tamaño original
            f_out.truncate(original_size)
    
    def visualize_compression(self, input_file, output_dir="cubit_visuals"):
        """Genera visualizaciones de los patrones CUBIT"""
        os.makedirs(output_dir, exist_ok=True)
        
        with open(input_file, 'rb') as f:
            index = 0
            while True:
                data_bytes = f.read(6)
                if not data_bytes:
                    break
                
                grid = self.bytes_to_cubit_grid(data_bytes)
                self.save_grid_visualization(grid, f"{output_dir}/original_{index:04d}.png")
                
                # Comprimir y visualizar resultado
                compressed_byte, shifts, shifted_grid = self.find_optimal_visual_pattern(grid)
                self.save_grid_visualization(shifted_grid, f"{output_dir}/shifted_{index:04d}.png")
                
                # Reconstruir
                decompressed_bytes = self.decompress_block(compressed_byte, 
                                                          self.encode_shifts(shifts))
                decompressed_grid = self.bytes_to_cubit_grid(decompressed_bytes)
                self.save_grid_visualization(decompressed_grid, f"{output_dir}/reconstructed_{index:04d}.png")
                
                index += 1
    
    def encode_shifts(self, shifts):
        """Codifica desplazamientos en entero"""
        metadata = 0
        for shift in shifts:
            metadata = (metadata << 3) | shift
        return metadata
    
    def save_grid_visualization(self, grid, filename):
        """Guarda una visualización de la cuadrícula"""
        plt.figure(figsize=(10, 8))
        plt.imshow(grid, cmap='viridis', interpolation='nearest')
        plt.colorbar()
        
        # Añadir valores de bits
        for i in range(6):
            for j in range(8):
                plt.text(j, i, str(grid[i, j]), 
                         ha='center', va='center', 
                         color='white' if grid[i, j] == 0 else 'black',
                         fontsize=12, fontweight='bold')
        
        plt.title("Patrón CUBIT")
        plt.xlabel("Columnas")
        plt.ylabel("Filas")
        plt.savefig(filename)
        plt.close()

# Ejemplo de uso
if __name__ == "__main__":
    compressor = CubitCompressor()
    
    # Crear archivo de prueba
    with open("test.bin", "wb") as f:
        # Datos con patrones reconocibles
        f.write(b"\xAA\x55\xAA\x55\xAA\x55")  # Patrón alternante
        f.write(b"\xFF\x00\xFF\x00\xFF\x00")  # Alto contraste
        f.write(b"\x18\x3C\x7E\x7E\x3C\x18")  # Patrón simétrico
        f.write(os.urandom(1024))  # Datos aleatorios
    
    # Comprimir
    compressor.compress_file("test.bin", "test.cubit")
    
    # Descomprimir
    compressor.decompress_file("test.cubit", "test_decompressed.bin")
    
    # Verificar integridad
    with open("test.bin", "rb") as f1, open("test_decompressed.bin", "rb") as f2:
        original = f1.read()
        decompressed = f2.read()
        print("Recuperación perfecta:", original == decompressed)
    
    # Generar visualizaciones
    # compressor.visualize_compression("test.bin")  # Descomentar si se necesitan visualizaciones
