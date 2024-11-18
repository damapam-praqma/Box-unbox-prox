import sqlite3
import shutil
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

# Konfigurasi
BOT_TOKEN = "7501545495:AAHto8clABYt63aPlj5rUehxh6RIIBr8jjQ"
ADMIN_ID = 6950646781  # Ganti dengan Telegram ID admin
DEFAULT_LIMIT = 5
DB_FILE = "tempmail.db"
API_BASE_URL = "https://www.1secmail.com/api/v1/"

# Inisialisasi Database
def init_db():
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

    # Tabel log aktivitas
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

# Fungsi API 1secmail
def create_temp_email():
    try:
        response = requests.get(API_BASE_URL + "?action=genRandomMailbox&count=1")
        response.raise_for_status()
        return response.json()[0]
    except Exception as e:
        return None

def fetch_messages(email):
    try:
        username, domain = email.split("@")
        response = requests.get(API_BASE_URL + f"?action=getMessages&login={username}&domain={domain}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None

# Fungsi Pendukung
def log_activity(user_id, action, detail):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs (user_id, action, detail) VALUES (?, ?, ?)
    """, (user_id, action, detail))
    conn.commit()
    conn.close()

def reset_users():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM emails")
    deleted_emails = cursor.rowcount

    cursor.execute("DELETE FROM users")
    deleted_users = cursor.rowcount

    conn.commit()
    conn.close()
    return deleted_users, deleted_emails

def notify_admin(updater, message):
    updater.bot.send_message(chat_id=ADMIN_ID, text=message)

# Handler
def start(update, context):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, limit) VALUES (?, ?)
    """, (user_id, DEFAULT_LIMIT))
    conn.commit()
    conn.close()

    update.message.reply_text("Selamat datang di bot Temp Mail! Gunakan /create_email untuk membuat email.")

def create_email(update, context):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT email_count, limit FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        update.message.reply_text("Terjadi kesalahan. Silakan coba lagi.")
        return

    email_count, limit = user_data
    if user_id == ADMIN_ID or email_count < limit:
        new_email = create_temp_email()
        if not new_email:
            update.message.reply_text("Terjadi kesalahan saat membuat email. Silakan coba lagi.")
            return

        cursor.execute("INSERT INTO emails (user_id, email) VALUES (?, ?)", (user_id, new_email))
        cursor.execute("UPDATE users SET email_count = email_count + 1 WHERE user_id = ?", (user_id,))
        conn.commit()

        log_activity(user_id, "CREATE_EMAIL", f"Email created: {new_email}")
        update.message.reply_text(f"Email berhasil dibuat: {new_email}")

        if user_id != ADMIN_ID:
            notify_admin(context, f"Pengguna @{username} (ID: {user_id}) telah membuat email baru: {new_email}")
    else:
        update.message.reply_text("Anda telah mencapai batas pembuatan email.")
    conn.close()

def reset_users_handler(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("Perintah ini hanya untuk admin.")
        return

    keyboard = [
        [InlineKeyboardButton("Yes", callback_data="confirm_reset"), InlineKeyboardButton("No", callback_data="cancel_reset")]
    ]
    update.message.reply_text(
        "Apakah Anda yakin ingin mereset semua data pengguna dan email?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def reset_users_confirmation(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    if query.data == "confirm_reset":
        deleted_users, deleted_emails = reset_users()
        query.edit_message_text(
            f"Semua data pengguna dan email berhasil direset.\nJumlah pengguna yang dihapus: {deleted_users}\nJumlah email yang dihapus: {deleted_emails}."
        )
        notify_admin(context, f"Data pengguna dan email telah direset.\nPengguna dihapus: {deleted_users}\nEmail dihapus: {deleted_emails}.")
    else:
        query.edit_message_text("Reset data dibatalkan.")

def backup_db(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("Perintah ini hanya untuk admin.")
        return

    try:
        shutil.copy(DB_FILE, "tempmail_backup.db")
        update.message.reply_text("Backup database berhasil dibuat: tempmail_backup.db")
        notify_admin(context, "Backup database berhasil diselesaikan: tempmail_backup.db")
    except Exception as e:
        update.message.reply_text("Terjadi kesalahan saat membuat backup. Silakan coba lagi.")
        notify_admin(context, f"Error during backup: {e}")

def user_list(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("Perintah ini hanya untuk admin.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    if not users:
        update.message.reply_text("Tidak ada pengguna yang terdaftar.")
        return

    user_list = "\n".join([f"- {user[0]}" for user in users])
    update.message.reply_text(f"Total Pengguna: {len(users)}\n\nDaftar ID:\n{user_list}")

# Main
def main():
    init_db()
    updater = Updater(BOT_TOKEN, use_context=True)

    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CommandHandler("create_email", create_email))
    updater.dispatcher.add_handler(CommandHandler("backup_db", backup_db))
    updater.dispatcher.add_handler(CommandHandler("reset_users", reset_users_handler))
    updater.dispatcher.add_handler(CommandHandler("user_list", user_list))
    updater.dispatcher.add_handler(CallbackQueryHandler(reset_users_confirmation))

    print("Bot sedang berjalan...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
