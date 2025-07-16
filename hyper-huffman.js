
export function compressHuffman(data) {
  const compressed = data.slice(0, data.length / 2); // Simulación
  const rate = 100 * (1 - compressed.length / data.length);
  return { compressed, rate };
}

export function decompressHuffman(data) {
  const restored = new Uint8Array(data.length * 2); // Simulación
  restored.set(data);
  return restored;
}

document.getElementById('compressInput').addEventListener('change', (e) => {
  const file = e.target.files[0];
  const reader = new FileReader();
  reader.onload = () => {
    const original = new Uint8Array(reader.result);
    const { compressed, rate } = compressHuffman(original);
    document.getElementById('originalSize').textContent = (original.length / 1024).toFixed(2) + ' KB';
    document.getElementById('compressedSize').textContent = (compressed.length / 1024).toFixed(2) + ' KB';
    document.getElementById('compressionRate').textContent = rate.toFixed(2) + ' %';
    const blob = new Blob([compressed]);
    const url = URL.createObjectURL(blob);
    const a = document.getElementById('downloadCompressed');
    a.href = url;
    a.download = file.name + '.h6d';
    a.style.display = 'block';
  };
  reader.readAsArrayBuffer(file);
});

document.getElementById('decompressInput').addEventListener('change', (e) => {
  const file = e.target.files[0];
  const reader = new FileReader();
  reader.onload = () => {
    const compressed = new Uint8Array(reader.result);
    const restored = decompressHuffman(compressed);
    document.getElementById('compressedSizeIn').textContent = (compressed.length / 1024).toFixed(2) + ' KB';
    document.getElementById('decompressedSize').textContent = (restored.length / 1024).toFixed(2) + ' KB';
    const blob = new Blob([restored]);
    const url = URL.createObjectURL(blob);
    const a = document.getElementById('downloadOriginal');
    a.href = url;
    a.download = file.name.replace('.h6d', '');
    a.style.display = 'block';
  };
  reader.readAsArrayBuffer(file);
});
