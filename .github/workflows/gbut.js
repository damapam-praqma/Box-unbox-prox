const TelegramBot = require('node-telegram-bot-api');
const fs = require('fs');
const axios = require('axios');

// Ganti dengan token bot Telegram Anda
const token = '7501545495:AAHto8clABYt63aPlj5rUehxh6RIIBr8jjQ';
const bot = new TelegramBot(token, { polling: true });

// ID Admin yang memiliki akses penuh
const ADMIN_ID = 6950646781; // Ganti dengan ID admin yang sesuai

// Simpan data email sementara di file (atau bisa gunakan database)
let userEmails = {}; // { userId: { email: 'email@example.com', createdAt: timestamp } }
let emailList = []; // Simpan email yang dibuat

// Fungsi untuk mengirim notifikasi ke admin
function notifyAdmin(message) {
    bot.sendMessage(ADMIN_ID, message);
}

// Fungsi untuk membuat email sementara
function createTempEmail(userId) {
    const email = `user${Math.floor(Math.random() * 1000)}@tempmail.com`;
    const timestamp = Date.now();

    // Simpan email dan waktu pembuatan
    userEmails[userId] = { email, createdAt: timestamp };
    emailList.push(email);

    return email;
}

// Fungsi untuk menghapus email berdasarkan ID pengguna
function deleteEmail(userId) {
    if (userEmails[userId]) {
        const email = userEmails[userId].email;
        delete userEmails[userId];
        emailList = emailList.filter(emailItem => emailItem !== email);
        return `Email ${email} berhasil dihapus.`;
    }
    return 'Email tidak ditemukan.';
}

// Fungsi untuk mengecek pesan email berdasarkan ID
async function checkMessages(email) {
    try {
        const response = await axios.get(`https://www.1secmail.com/api/v1/?action=getMessages&login=${email.split('@')[0]}&domain=tempmail.com`);
        return response.data;
    } catch (error) {
        return 'Gagal mengambil pesan. Pastikan email valid.';
    }
}

// Fungsi untuk membaca pesan tertentu
async function readMessage(email, messageId) {
    try {
        const response = await axios.get(`https://www.1secmail.com/api/v1/?action=readMessage&login=${email.split('@')[0]}&domain=tempmail.com&id=${messageId}`);
        const message = response.data;
        return {
            from: message.from,
            subject: message.subject,
            date: message.date,
            body: message.text
        };
    } catch (error) {
        return 'Gagal membaca pesan.';
    }
}

// Fungsi untuk mengatur limit pembuatan email pengguna
function setUserLimit(userId) {
    // Cek apakah pengguna telah membuat lebih dari 5 email
    if (!userEmails[userId]) {
        userEmails[userId] = { emailCount: 0 };
    }

    userEmails[userId].emailCount += 1;

    if (userEmails[userId].emailCount > 5) {
        return 'Limit pembuatan email sudah tercapai. Silakan coba lagi nanti.';
    }
    return createTempEmail(userId);
}

// Menangani pesan dari pengguna
bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const userId = msg.from.id;

    // Cek apakah pesan berasal dari admin
    if (userId === ADMIN_ID) {
        if (msg.text === '/admin') {
            bot.sendMessage(chatId, 'Halo Admin! Pilih perintah yang diinginkan.');
            bot.sendMessage(chatId, '1. /create-email - Membuat email sementara\n2. /delete-email - Menghapus email pengguna\n3. /check-email - Cek email pengguna\n4. /reset-limit - Reset limit pengguna');
        } else if (msg.text === '/create-email') {
            const email = createTempEmail(userId);
            bot.sendMessage(chatId, `Email sementara Anda: ${email}`);
        } else if (msg.text.startsWith('/delete-email')) {
            const userToDelete = msg.text.split(' ')[1]; // Ambil userId dari perintah
            const result = deleteEmail(userToDelete);
            bot.sendMessage(chatId, result);
        } else if (msg.text.startsWith('/check-email')) {
            const email = msg.text.split(' ')[1]; // Ambil email dari perintah
            const messages = await checkMessages(email);
            bot.sendMessage(chatId, `Pesan untuk ${email}:\n${JSON.stringify(messages, null, 2)}`);
        } else if (msg.text.startsWith('/reset-limit')) {
            const userToReset = msg.text.split(' ')[1]; // Ambil userId dari perintah
            if (userEmails[userToReset]) {
                userEmails[userToReset].emailCount = 0;
                bot.sendMessage(chatId, `Limit pengguna ${userToReset} telah direset.`);
            } else {
                bot.sendMessage(chatId, `Pengguna ${userToReset} tidak ditemukan.`);
            }
        }
    } else {
        // Pengguna biasa: Membuat email jika belum mencapai limit
        const limitResponse = setUserLimit(userId);
        if (limitResponse.includes('Limit')) {
            bot.sendMessage(chatId, limitResponse);
        } else {
            bot.sendMessage(chatId, `Email sementara Anda: ${limitResponse}`);
        }
    }
});

// Perintah /start untuk memulai interaksi dengan bot
bot.onText(/\/start/, (msg) => {
    const chatId = msg.chat.id;
    bot.sendMessage(chatId, 'Selamat datang! Ketik /help untuk melihat daftar perintah.');
});

// Perintah /help untuk menampilkan petunjuk
bot.onText(/\/help/, (msg) => {
    const chatId = msg.chat.id;
    bot.sendMessage(chatId, 'Perintah yang tersedia:\n- /create-email: Membuat email sementara\n- /check-email: Cek pesan email\n- /delete-email: Hapus email\n- /reset-limit: Reset limit pengguna');
});
