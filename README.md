# SINERGI Pi Client

Aplikasi layar sentuh Raspberry Pi untuk mengambil foto padi atau edamame dan mengirimkannya ke layanan inferensi SINERGI di Cloud Run.

## Kebutuhan

- Raspberry Pi dengan Raspberry Pi OS, kamera yang didukung Picamera2, dan sesi desktop aktif.
- Koneksi internet untuk mengirim foto ke Cloud Run.
- Layar: UI menggunakan resolusi tetap 1024 × 600.
- Python 3 dengan `pygame`, `requests`, `numpy`, Pillow, dan Picamera2.

Picamera2 dan dependensi kamera perlu tersedia melalui paket sistem Raspberry Pi OS. Jika menggunakan virtual environment, pastikan paket sistem tersebut dapat diakses. Kamera dan UI ini tidak dapat diuji sepenuhnya pada komputer tanpa perangkat Raspberry Pi.

## Menjalankan aplikasi

Dari folder repository, jalankan di terminal pada sesi desktop Raspberry Pi:

```bash
python3 ui.py
```

Pilih **Hasil Panen** atau **Deteksi HPT**, lalu pilih **Padi** atau **Edamame**. Atur kamera, tekan **FOTO**, periksa preview, lalu tekan **KIRIM**. Setiap sesi memiliki maksimal empat slot foto. Tekan **Esc** untuk keluar.

Foto sementara disimpan di `/tmp/sinergi_capture.jpg` dan ditimpa saat mengambil foto berikutnya. Respons cloud dapat menampilkan jumlah deteksi, gambar anotasi, dan indikator penyimpanan jika respons memuat `doc_id`. Kegagalan kamera atau permintaan cloud ditampilkan pada layar hasil.

## Pengaturan cloud dan kiosk

Alamat layanan cloud berada di `CLOUD_RUN_URL` pada `client.py`. Empat kombinasi mode dan tanaman dipetakan ke endpoint inferensi yang berbeda. Permintaan mengirim JPEG, `session_id`, dan `sample_slot`, dengan timeout 90 detik.

Untuk launcher kiosk, periksa terlebih dahulu `APP_DIR` dalam `kiosk_start.sh`: nilai saat ini adalah `/home/raspi1/sinergi-client`. Sesuaikan dengan lokasi checkout pada perangkat. Launcher menggunakan `DISPLAY=:0` dan driver SDL `x11`, sehingga sesi desktop dengan XWayland/X11 yang sesuai harus aktif.

```bash
bash kiosk_start.sh
```

Launcher menghentikan proses yang cocok dengan `python3 ui.py` sebelum menjalankan aplikasi kembali.

## Isi repository

| File | Fungsi |
| --- | --- |
| `ui.py` | UI PyGame, preview dan capture Picamera2, sesi foto, serta tampilan hasil |
| `client.py` | Mengirim foto dan metadata sesi ke Cloud Run |
| `camera.py` | Path foto bersama dan helper capture melalui `rpicam-still`; UI memakai Picamera2 secara langsung |
| `kiosk_start.sh` | Launcher untuk sesi desktop Raspberry Pi |
