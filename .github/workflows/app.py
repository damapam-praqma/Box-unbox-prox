import sqlite3
import shutil
import requests
from functools import lru_cache
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Konfigurasi
BOT_TOKEN = "7501545495:AAHto8clABYt63aPlj5rUehxh6RIIBr8jjQ"
ADMIN_ID = 6950646781  # Ganti dengan Telegram ID admin
DEFAULT_LIMIT = 5
DB_FILE = "tempmail.db"
API_BASE_URL = "https://www.1secmail.com/api/v1/"

# Fungsi Database
def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Tabel pengguna
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                limit INTEGER DEFAULT ?,
                email_count INTEGER DEFAULT 0
            )
        """, (DEFAULT_LIMIT,))

        # Tabel email
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email TEXT UNIQUE,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        # Log aktivitas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                detail TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        notify_admin(f"Error initializing database: {e}")


def notify_admin(message):
    """Mengirim pesan error ke admin."""
    try:
        context.bot.send_message(chat_id=ADMIN_ID, text=f"Error Notification:\n{message}")
    except Exception as e:
        print(f"Gagal mengirim notifikasi ke admin: {e}")


def reset_users():
    """Menghapus semua data pengguna dan email dari database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM emails")
        cursor.execute("DELETE FROM users")

        deleted_emails = cursor.rowcount
        conn.commit()
        conn.close()

        return {"deleted_emails": deleted_emails}
    except Exception as e:
        notify_admin(f"Error resetting users: {e}")
        return None


def get_total_users():
    """Mengambil total jumlah pengguna dan ID mereka."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()

        return [user[0] for user in users]
    except Exception as e:
        notify_admin(f"Error fetching user list: {e}")
        return None


# Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, limit) VALUES (?, ?)", (user_id, DEFAULT_LIMIT))
        conn.commit()
        conn.close()
        await update.message.reply_text("Selamat datang di bot Temp Mail! Gunakan /create_email untuk membuat email.")
    except Exception as e:
        notify_admin(f"Error starting bot for user {user_id}: {e}")
        await update.message.reply_text("Terjadi kesalahan. Silakan coba lagi.")


async def user_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Perintah ini hanya untuk admin.")
        return

    users = get_total_users()
    if users is None:
        await update.message.reply_text("Terjadi kesalahan saat mengambil daftar pengguna.")
        return

    user_text = "\n".join([f"- {user_id}" for user_id in users])
    await update.message.reply_text(f"Total Pengguna: {len(users)}\n\nDaftar ID:\n{user_text}")


async def reset_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Perintah ini hanya untuk admin.")
        return

    # Konfirmasi dengan tombol
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data="confirm_reset"), InlineKeyboardButton("No", callback_data="cancel_reset")]
    ]
    await update.message.reply_text("Apakah Anda yakin ingin mereset semua data pengguna dan email?", reply_markup=InlineKeyboardMarkup(keyboard))


async def reset_users_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_reset":
        result = reset_users()
        if result:
            deleted_emails = result.get("deleted_emails", 0)
            await query.edit_message_text(f"Semua data pengguna dan email berhasil direset.\nJumlah email yang dihapus: {deleted_emails}.")
            notify_admin(f"Data pengguna dan email telah direset.\nJumlah email yang dihapus: {deleted_emails}.")
        else:
            await query.edit_message_text("Terjadi kesalahan saat mereset data.")
    else:
        await query.edit_message_text("Reset data dibatalkan.")


async def backup_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Perintah ini hanya untuk admin.")
        return

    try:
        shutil.copy(DB_FILE, "tempmail_backup.db")
        await update.message.reply_text("Backup database berhasil dibuat: tempmail_backup.db")

        # Notifikasi otomatis ke admin
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="Backup database berhasil diselesaikan: tempmail_backup.db"
        )
    except Exception as e:
        notify_admin(f"Error creating database backup: {e}")
        await update.message.reply_text("Terjadi kesalahan saat membuat backup. Silakan coba lagi.")


def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("user_list", user_list))
    app.add_handler(CommandHandler("backup_db", backup_db))
    app.add_handler(CommandHandler("reset_users", reset_users_handler))
    app.add_handler(CallbackQueryHandler(reset_users_confirmation))

    print("Bot sedang berjalan...")
    app.run_polling()


if __name__ == "__main__":
    main()
