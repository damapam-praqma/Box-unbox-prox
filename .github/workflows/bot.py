import subprocess
import time

# Fungsi untuk menjalankan server.js
def run_node_server():
    # Jalankan server Node.js
    try:
        subprocess.Popen(['node', 'server.js'])  # Jalankan server.js dengan Node.js
        print("Server Node.js berjalan dengan sukses.")
    except Exception as e:
        print(f"Terjadi kesalahan saat menjalankan server Node.js: {e}")

# Fungsi untuk memulai aplikasi utama Python
def main():
    # Jalankan server Node.js
    run_node_server()

    # Loop utama Python untuk terus berjalan (misalnya melakukan tugas lain)
    try:
        while True:
            time.sleep(10)  # Biarkan program berjalan terus
    except KeyboardInterrupt:
        print("Program Python dihentikan.")

if __name__ == "__main__":
    main()
