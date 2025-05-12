#!/usr/bin/env python3
"""
whats_auto_gui.py

Interface gráfica para automação de envio de mensagens via WhatsApp Business,
carregando planilha e executando o envio com controle de delay, modo headless,
progress bar, logs integrados e botão de parada.
"""
import os
import time
import logging
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# --- Configuração de ambiente ---
load_dotenv()
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "chromedriver")
WHATSAPP_WEB_BASE = "https://web.whatsapp.com/send"
TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class TextHandler(logging.Handler):
    """Logging handler que envia logs para um Text widget no Tkinter"""
    def __init__(self, text_widget: tk.Text):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        def append():
            self.text_widget.configure(state=tk.NORMAL)
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state=tk.DISABLED)
            self.text_widget.yview(tk.END)
        self.text_widget.after(0, append)

# --- Funções de automação ---

def setup_driver(headless: bool = False) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless")
    opts.add_argument("--user-data-dir=./.whatsapp_profile")
    driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, options=opts)
    driver.maximize_window()
    return driver


def load_contacts(path: Path) -> pd.DataFrame:
    if path.suffix in (".xls", ".xlsx"):
        df = pd.read_excel(path)
    elif path.suffix == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError("Formato inválido. Use .xlsx, .xls ou .csv")
    if 'telefone' not in df.columns or 'mensagem' not in df.columns:
        raise KeyError("A planilha deve conter colunas 'telefone' e 'mensagem'.")
    return df[['telefone', 'mensagem']]


def send_message(driver: webdriver.Chrome, phone: str, message: str) -> bool:
    params = f"?phone={phone}&text={message}"
    driver.get(WHATSAPP_WEB_BASE + params)
    try:
        btn = WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='compose-btn-send']"))
        )
        btn.click()
        logger.info(f"[{phone}] Mensagem enviada.")
        return True
    except Exception as e:
        logger.error(f"[{phone}] Falha ao enviar: {e}")
        return False

# --- GUI ---

class WhatsAutoGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WhatsAuto GUI")
        self.geometry("500x600")
        self.resizable(False, False)

        self.file_path: Optional[Path] = None
        self.stop_flag = False

        # Label de arquivo
        self.label_file = tk.Label(self, text="Nenhuma planilha selecionada")
        self.label_file.pack(pady=5)

        # Botão carregar
        self.btn_load = tk.Button(self, text="Carregar Planilha", command=self.load_file)
        self.btn_load.pack(pady=5)

        # Delay
        tk.Label(self, text="Delay entre envios (s):").pack()
        self.delay_var = tk.DoubleVar(value=2.0)
        self.spin_delay = tk.Spinbox(
            self, from_=0.5, to=10.0, increment=0.5,
            textvariable=self.delay_var, width=5
        )
        self.spin_delay.pack(pady=5)

        # Headless
        self.headless_var = tk.BooleanVar(value=False)
        self.chk_headless = tk.Checkbutton(self, text="Modo Headless", variable=self.headless_var)
        self.chk_headless.pack(pady=5)

        # Botões executar/parar
        self.btn_run = tk.Button(self, text="Executar Envio", command=self.start_sending, state=tk.DISABLED)
        self.btn_run.pack(pady=5)
        self.btn_stop = tk.Button(self, text="Parar Envio", command=self.stop_sending, state=tk.DISABLED)
        self.btn_stop.pack(pady=5)

        # Progresso
        self.progress_label = tk.Label(self, text="Aguardando ação...")
        self.progress_label.pack(pady=5)

        # Text widget para logs
        self.log_text = tk.Text(self, height=15, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        handler = TextHandler(self.log_text)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)

    def load_file(self):
        path_str = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv")]
        )
        if path_str:
            self.file_path = Path(path_str)
            self.label_file.config(text=self.file_path.name)
            self.btn_run.config(state=tk.NORMAL)

    def start_sending(self):
        if not self.file_path:
            messagebox.showwarning("Aviso", "Selecione uma planilha primeiro.")
            return
        self.btn_load.config(state=tk.DISABLED)
        self.btn_run.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.stop_flag = False
        threading.Thread(target=self.run_sending, daemon=True).start()

    def stop_sending(self):
        self.stop_flag = True
        logger.info("Parando envio a pedido do usuário...")

    def run_sending(self):
        # Setup driver
        driver = setup_driver(headless=self.headless_var.get())
        messagebox.showinfo("Passo 1", "Escaneie o QR Code no WhatsApp Web e clique em OK.")

        # Carrega contatos
        try:
            contacts = load_contacts(self.file_path)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar planilha: {e}")
            self.reset_ui()
            return

        total = len(contacts)
        for idx, row in enumerate(contacts.itertuples(index=False), start=1):
            if self.stop_flag:
                break
            phone = str(row.telefone).strip()
            text  = str(row.mensagem).strip()
            # Atualiza label de progresso
            self.progress_label.after(0, lambda i=idx, t=total: self.progress_label.config(
                text=f"Enviando {i}/{t}"
            ))
            send_message(driver, phone, text)
            time.sleep(self.delay_var.get())

        driver.quit()
        if not self.stop_flag:
            messagebox.showinfo("Concluído", "Envio de mensagens finalizado com sucesso.")
        self.reset_ui()

    def reset_ui(self):
        self.btn_load.config(state=tk.NORMAL)
        self.btn_run.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.progress_label.after(0, lambda: self.progress_label.config(text="Aguardando ação..."))


def main():
    app = WhatsAutoGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
