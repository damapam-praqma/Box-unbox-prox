import sqlite3
import requests
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, CallbackContext

BOT_TOKEN = "7501545495:AAHto8clABYt63aPlj5rUehxh6RIIBr8jjQ"
ADMIN_ID = 6950646781  # Ganti dengan ID Admin
DB_FILE = "tempmail.db"
API_BASE_URL = "https://www.1secmail.com/api/v1/"

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Tabel untuk pengguna
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        email_limit INTEGER DEFAULT 5,
        last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabel untuk email pengguna
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emails (
        user_id INTEGER,
        email TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """)
    
    conn.commit()
    conn.close()

# Reset limit email jika lebih dari 5 jam
def reset_user_limit(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT email_limit, last_reset FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    
    if user_data:
        email_limit, last_reset = user_data
        last_reset_time = datetime.datetime.strptime(last_reset, "%Y-%m-%d %H:%M:%S")
        elapsed_time = datetime.datetime.now() - last_reset_time
        
        if elapsed_time.total_seconds() > 5 * 3600:  # Jika lebih dari 5 jam
            cursor.execute("""
                UPDATE users
                SET email_limit = 5, last_reset = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
    
    conn.commit()
    conn.close()

# Ambil email dari API 1secmail
def get_temp_email_address():
    try:
        response = requests.get(f"{API_BASE_URL}?action=genRandomMailbox&count=1")
        if response.status_code == 200:
            email = response.json()[0]
            return email
    except Exception as e:
        print(f"Error generating email: {e}")
    return None

# Buat email baru untuk pengguna
async def create_email(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    reset_user_limit(user_id)  # Reset otomatis jika sudah lebih dari 5 jam
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT email_limit FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    
    if not user_data:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        email_limit = 5
    else:
        email_limit = user_data[0]

    if email_limit <= 0:
        await update.message.reply_text("Batas pembuatan email tercapai. Tunggu hingga limit reset otomatis setelah 5 jam.")
        conn.close()
        return

    email_address = get_temp_email_address()
    if not email_address:
        await update.message.reply_text("Gagal membuat email. Coba lagi nanti.")
        conn.close()
        return

    cursor.execute("INSERT INTO emails (user_id, email) VALUES (?, ?)", (user_id, email_address))
    cursor.execute("UPDATE users SET email_limit = email_limit - 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"Email berhasil dibuat: {email_address}")
    if user_id != ADMIN_ID:
        await context.bot.send_message(ADMIN_ID, f"Pengguna {user_id} membuat email baru: {email_address}")

# Periksa pesan di email tertentu
async def check_messages(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT email FROM emails WHERE user_id = ?", (user_id,))
    emails = cursor.fetchall()
    
    if not emails:
        await update.message.reply_text("Anda belum memiliki email yang terdaftar.")
        conn.close()
        return

    # Tampilkan daftar email
    keyboard = [
        [InlineKeyboardButton(email[0], callback_data=f"check_{email[0]}")]
        for email in emails
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Pilih email untuk diperiksa:", reply_markup=reply_markup)
    conn.close()

# Callback untuk melihat pesan di email tertentu
async def view_messages(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    email = query.data.split("_", 1)[1]
    domain = email.split("@")[1]
    username = email.split("@")[0]

    try:
        response = requests.get(f"{API_BASE_URL}?action=getMessages&login={username}&domain={domain}")
        if response.status_code != 200 or not response.json():
            await query.edit_message_text(f"Tidak ada pesan masuk untuk email: {email}")
            return

        messages = response.json()
        keyboard = [
            [InlineKeyboardButton(f"{msg['subject'][:30]}...", callback_data=f"msg_{email}_{msg['id']}")]
            for msg in messages
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Pilih pesan untuk melihat detailnya:", reply_markup=reply_markup)
    except Exception as e:
        await query.edit_message_text("Gagal mengambil pesan. Coba lagi nanti.")
        print(f"Error fetching messages: {e}")

# Callback untuk melihat detail pesan
async def view_message_detail(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    _, email, msg_id = query.data.split("_")
    domain = email.split("@")[1]
    username = email.split("@")[0]

    try:
        response = requests.get(f"{API_BASE_URL}?action=readMessage&login={username}&domain={domain}&id={msg_id}")
        if response.status_code != 200 or not response.json():
            await query.edit_message_text("Gagal mengambil detail pesan.")
            return

        message = response.json()
        detail = f"""
Pengirim: {message['from']}
Subjek: {message['subject']}
Isi Pesan:
{message['textBody']}
"""
        await query.edit_message_text(detail)
    except Exception as e:
        await query.edit_message_text("Gagal mengambil detail pesan. Coba lagi nanti.")
        print(f"Error fetching message detail: {e}")

# Main program
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Selamat datang di bot TempMail! Gunakan /create_email untuk membuat email.")

if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("create_email", create_email))
    app.add_handler(CommandHandler("check_messages", check_messages))
    app.add_handler(CallbackQueryHandler(view_messages, pattern=r"^check_"))
    app.add_handler(CallbackQueryHandler(view_message_detail, pattern=r"^msg_"))
    app.run_polling()
