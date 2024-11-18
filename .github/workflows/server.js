const express = require('express');
const { exec } = require('child_process');

// Inisialisasi aplikasi Express
const app = express();
const port = 3000;

// Endpoint untuk memulai `gbut.js` atau kode lainnya
app.get('/start-bot', (req, res) => {
    // Menjalankan gbut.js (atau bot Telegram) di dalam server.js
    exec('node gbut.js', (err, stdout, stderr) => {
        if (err) {
            console.error(`Error: ${err}`);
            return res.status(500).send('Terjadi kesalahan saat menjalankan bot.');
        }
        console.log(`Output: ${stdout}`);
        res.send('Bot Telegram berhasil dijalankan.');
    });
});

// Menjalankan server di port 3000
app.listen(port, () => {
    console.log(`Server berjalan di http://localhost:${port}`);
});
