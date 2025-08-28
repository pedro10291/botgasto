import os
import sqlite3
import re
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import easyocr

# Inicializa banco de dados
conn = sqlite3.connect("financeiro.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS financeiro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria TEXT,
    valor REAL,
    tipo TEXT
)
""")
conn.commit()

# Funções auxiliares
def registrar(tipo, categoria, valor):
    cursor.execute(
        "INSERT INTO financeiro (categoria, valor, tipo) VALUES (?, ?, ?)",
        (categoria, valor, tipo)
    )
    conn.commit()

def somar(tipo):
    cursor.execute("SELECT SUM(valor) FROM financeiro WHERE tipo = ?", (tipo,))
    resultado = cursor.fetchone()[0]
    return resultado or 0

def listar_gastos():
    cursor.execute("SELECT categoria, valor FROM financeiro WHERE tipo = 'gasto'")
    return cursor.fetchall()

# Comandos
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Me diga seu salário com /salario 3000")

async def salario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(context.args[0])
        registrar("salario", "salario", valor)
        await update.message.reply_text(f"Salário registrado: R$ {valor:.2f}")
    except (IndexError, ValueError):
        await update.message.reply_text("Use: /salario valor")

async def fixos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(context.args[0])
        registrar("fixos", "fixos", valor)
        await update.message.reply_text(f"Gastos fixos registrados: R$ {valor:.2f}")
    except (IndexError, ValueError):
        await update.message.reply_text("Use: /fixos valor")

async def lazer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(context.args[0])
        registrar("lazer", "lazer", valor)
        await update.message.reply_text(f"Limite de lazer: R$ {valor:.2f}")
    except (IndexError, ValueError):
        await update.message.reply_text("Use: /lazer valor")

async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        categoria = context.args[0]
        valor = float(context.args[1])
        registrar("gasto", categoria, valor)
        await update.message.reply_text(f"Gasto registrado: {categoria} - R$ {valor:.2f}")
    except (IndexError, ValueError):
        await update.message.reply_text("Formato inválido. Use: /gasto categoria valor")

async def resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    salario_total = somar("salario")
    fixos_total = somar("fixos")
    gastos_total = somar("gasto")
    saldo = salario_total - fixos_total - gastos_total
    await update.message.reply_text(
        f"Gastos: R$ {gastos_total:.2f}\nSaldo restante: R$ {saldo:.2f}"
    )

async def relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gastos = listar_gastos()
    if not gastos:
        await update.message.reply_text("Nenhum gasto registrado ainda.")
        return

    categorias = {}
    for cat, val in gastos:
        categorias[cat] = categorias.get(cat, 0) + val

    texto = "📊 *Relatório de Gastos por Categoria:*\n"
    total = 0
    for cat, val in categorias.items():
        texto += f"• {cat.capitalize()}: R$ {val:.2f}\n"
        total += val

    texto += f"\n💰 *Total:* R$ {total:.2f}"
    await update.message.reply_text(texto, parse_mode="Markdown")

async def receber_imagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    foto = await update.message.photo[-1].get_file()
    caminho = "comprovante.jpg"
    await foto.download_to_drive(caminho)

    leitor = easyocr.Reader(['pt'])
    resultado = leitor.readtext(caminho)

    for linha in resultado:
        texto = linha[1]
        match = re.search(r"R?\$?\s?(\d+[.,]?\d*)", texto)
        if match:
            try:
                valor = float(match.group(1).replace(",", "."))
                registrar("gasto", "imagem", valor)
                await update.message.reply_text(f"Gasto registrado via imagem: R$ {valor:.2f}")
                return
            except ValueError:
                continue

    await update.message.reply_text("Não consegui identificar o valor no comprovante.")

# Inicialização do bot
token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    raise ValueError("Variável TELEGRAM_BOT_TOKEN não definida")

app = ApplicationBuilder().token(token).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("salario", salario))
app.add_handler(CommandHandler("fixos", fixos))
app.add_handler(CommandHandler("lazer", lazer))
app.add_handler(CommandHandler("gasto", gasto))
app.add_handler(CommandHandler("resumo", resumo))
app.add_handler(CommandHandler("relatorio", relatorio))
app.add_handler(MessageHandler(filters.PHOTO, receber_imagem))

try:
    app.run_polling()
except Exception as e:
    print(f"Erro ao iniciar o bot: {e}")
