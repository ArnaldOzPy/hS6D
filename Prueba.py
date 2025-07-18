import numpy as np
from scipy.optimize import minimize

def rotar_cubit(cubit, eje, rotaciones=1):
    """
    Rota un CUBIT en uno de sus 3 ejes posibles (0: X, 1: Y, 2: Z)
    Cada rotación cíclica cambia el orden de las caras
    """
    # Mapeo de ejes a caras:
    # Eje 0 (X): [0,1,2,3] -> rotación: [1,2,3,0]
    # Eje 1 (Y): [0,4,2,5] -> rotación: [4,2,5,0]
    # Eje 2 (Z): [1,4,3,5] -> rotación: [4,3,5,1]
    ejes_map = {
        0: [0, 1, 2, 3],  # Cara frontal, superior, trasera, inferior
        1: [0, 4, 2, 5],  # Cara frontal, derecha, trasera, izquierda
        2: [1, 4, 3, 5]   # Cara superior, derecha, inferior, izquierda
    }
    
    caras = cubit.copy()
    indices = ejes_map[eje]
    for _ in range(rotaciones % 4):
        # Rotación cíclica
        caras[indices] = np.roll(caras[indices], -1)
    return caras

def funcion_costo(rotaciones, columnas):
    """
    Calcula la 'energía' del sistema para evaluar la continuidad
    """
    costo = 0
    for i in range(8):  # Para cada CUBIT
        cubit = columnas[:, i]
        # Aplicar rotaciones (eje_x, eje_y, eje_z)
        cubit_rotado = rotar_cubit(cubit, 0, rotaciones[i*3])
        cubit_rotado = rotar_cubit(cubit_rotado, 1, rotaciones[i*3+1])
        cubit_rotado = rotar_cubit(cubit_rotado, 2, rotaciones[i*3+2])
        
        # Penalizar discontinuidades con CUBIT adyacente
        if i < 7:
            next_cubit = columnas[:, i+1]
            # Diferencia en caras adyacentes
            costo += np.sum(cubit_rotado[[1,4,5]] != next_cubit[[0,3,2]])
    return costo

def descomprimir_cubit_rubik(nuevos_bytes):
    # Reorganizar bytes en matriz 6x8 (caras x cubits)
    columnas = np.zeros((6, 8), dtype=int)
    for i, byte in enumerate(nuevos_bytes):
        bits = [(byte >> j) & 1 for j in range(7, -1, -1)]
        columnas[i] = bits
    
    # Inicializar rotaciones aleatorias (8 cubits * 3 ejes = 24 parámetros)
    x0 = np.random.randint(0, 4, 24)
    
    # Optimizar rotaciones para minimizar discontinuidades
    res = minimize(funcion_costo, x0, args=(columnas), 
                   method='Powell', options={'maxiter': 1000})
    
    # Aplicar rotaciones óptimas
    raices = []
    for i in range(8):
        cubit = columnas[:, i]
        for j in range(3):
            cubit = rotar_cubit(cubit, j, res.x[i*3 + j])
        raices.append(cubit[0])  # La cara frontal es la raíz
    
    # Convertir raices a byte
    byte_original = 0
    for bit in raices:
        byte_original = (byte_original << 1) | bit
    
    return byte_original

# Ejemplo de uso
nuevos_bytes = [0b11010100, 0b10101011, 0b01010101, 
                0b10101010, 0b01010101, 0b10101010]  # 6 bytes de entrada

byte_recuperado = descomprimir_cubit_rubik(nuevos_bytes)
print(f"Byte reconstruido: {bin(byte_recuperado)}")
