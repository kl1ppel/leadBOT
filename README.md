# 1. Crie o arquivo README.md
New-Item -Name README.md -ItemType File

# 2. Abra no seu editor (pode usar o VSCode, Notepad, Nano etc)
code README.md      # se você tiver o VSCode CLI instalado
# — ou —
notepad README.md   # no Windows puro

# 3. Cole algo como isto dentro do README.md:

# 🤖 leadBOT
**Bot de automação de mensagens para WhatsApp Business**

Automatiza o envio de mensagens a partir de uma planilha com colunas:
- `telefone`  
- `mensagem`  

**Funcionalidades principais:**
- Interface gráfica (Tkinter) com botão para carregar planilha
- Envio um-a-um via WhatsApp Web (Selenium)
- Delay configurável e logs em tempo real

---

## 🚀 Como usar

1. Clone este repositório:
   ```bash
   git clone git@github.com:kl1ppel/leadBOT.git
   cd leadBOT
