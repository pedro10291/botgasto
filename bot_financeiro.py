import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import easyocr

# Dados financeiros
dados = {
    "salario": 0,
    "fixos": 0,
    "lazer": 0,
    "gastos": []  # Agora cada gasto é um dicionário: {"categoria": ..., "valor": ...}
}

# Função para salvar os dados em JSON
def salvar_dados():
    with open("gastos.json", "w") as f:
        json.dump(dados, f, indent=4)

# Função para carregar os dados ao iniciar
def carregar_dados():
    global dados
    try:
        with open("gastos.json", "r") as f:
            dados = json.load(f)
    except FileNotFoundError:
        pass

carregar_dados()

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Me diga seu salário com /salario 3000")

# Comando /salario
async def salario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valor = float(context.args[0])
    dados["salario"] = valor
    salvar_dados()
    await update.message.reply_text(f"Salário registrado: R$ {valor:.2f}")

# Comando /fixos
async def fixos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valor = float(context.args[0])
    dados["fixos"] = valor
    salvar_dados()
    await update.message.reply_text(f"Gastos fixos registrados: R$ {valor:.2f}")

# Comando /lazer
async def lazer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valor = float(context.args[0])
    dados["lazer"] = valor
    salvar_dados()
    await update.message.reply_text(f"Limite de lazer: R$ {valor:.2f}")

# Comando /gasto <categoria> <valor>
async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        categoria = context.args[0]
        valor = float(context.args[1])
        dados["gastos"].append({"categoria": categoria, "valor": valor})
        salvar_dados()
        await update.message.reply_text(f"Gasto registrado: {categoria} - R$ {valor:.2f}")
    except:
        await update.message.reply_text("Formato inválido. Use: /gasto categoria valor (ex: /gasto comida 25.50)")

# Comando /resumo
async def resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_gastos = sum(item["valor"] for item in dados["gastos"])
    saldo = dados["salario"] - dados["fixos"] - total_gastos
    await update.message.reply_text(f"Gastos: R$ {total_gastos:.2f}\nSaldo restante: R$ {saldo:.2f}")

# Leitura de imagem com OCR
async def receber_imagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    foto = await update.message.photo[-1].get_file()
    caminho = "comprovante.jpg"
    await foto.download_to_drive(caminho)

    leitor = easyocr.Reader(['pt'])
    resultado = leitor.readtext(caminho)

    for linha in resultado:
        texto = linha[1]
        if "R$" in texto or "," in texto:
            try:
                valor = float(texto.replace("R$", "").replace(",", "."))
                dados["gastos"].append({"categoria": "imagem", "valor": valor})
                salvar_dados()
                await update.message.reply_text(f"Gasto registrado via imagem: R$ {valor:.2f}")
                return
            except:
                continue

    await update.message.reply_text("Não consegui identificar o valor no comprovante.")

# Executar o bot
app = ApplicationBuilder().token("8467990599:AAEZqjcBwR-L1QpaXHbRCaHY7-C7O2tB4h8").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("salario", salario))
app.add_handler(CommandHandler("fixos", fixos))
app.add_handler(CommandHandler("lazer", lazer))
app.add_handler(CommandHandler("gasto", gasto))  # Novo comando
app.add_handler(CommandHandler("resumo", resumo))
app.add_handler(MessageHandler(filters.PHOTO, receber_imagem))

app.run_polling()
# Comando /relatorio
async def relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not dados["gastos"]:
        await update.message.reply_text("Nenhum gasto registrado ainda.")
        return

    categorias = {}
    for item in dados["gastos"]:
        cat = item["categoria"]
        val = item["valor"]
        categorias[cat] = categorias.get(cat, 0) + val

    texto = "📊 *Relatório de Gastos por Categoria:*\n"
    total = 0
    for cat, val in categorias.items():
        texto += f"• {cat.capitalize()}: R$ {val:.2f}\n"
        total += val

    texto += f"\n💰 *Total:* R$ {total:.2f}"
    await update.message.reply_text(texto, parse_mode="Markdown")

app.add_handler(CommandHandler("relatorio", relatorio))
