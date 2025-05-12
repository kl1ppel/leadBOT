#!/usr/bin/env python3
"""
whats_auto_gui.py

Interface gráfica para automação de envio de mensagens via WhatsApp Business,
carregando planilha e executando o envio.
"""
import os
import time
import logging
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

# --- Configurações de ambiente ---
load_dotenv()
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "chromedriver")
WHATSAPP_WEB_BASE = "https://web.whatsapp.com/send"
TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

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
        send_btn = WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='compose-btn-send']"))
        )
        send_btn.click()
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
        self.geometry("400x180")
        self.resizable(False, False)

        self.file_path: Optional[Path] = None

        self.label = tk.Label(self, text="Nenhuma planilha selecionada")
        self.label.pack(pady=10)

        self.btn_load = tk.Button(self, text="Carregar Planilha", command=self.load_file)
        self.btn_load.pack(pady=5)

        self.btn_run = tk.Button(self, text="Executar Envio", command=self.run_sending, state=tk.DISABLED)
        self.btn_run.pack(pady=5)

    def load_file(self):
        path_str = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv")]
        )
        if path_str:
            self.file_path = Path(path_str)
            self.label.config(text=self.file_path.name)
            self.btn_run.config(state=tk.NORMAL)

    def run_sending(self):
        if not self.file_path:
            messagebox.showwarning("Aviso", "Selecione uma planilha primeiro.")
            return
        # Inicia driver e QR
        driver = setup_driver()
        messagebox.showinfo("Passo 1", "Escaneie o QR Code no WhatsApp Web e clique em OK.")
        driver.get("https://web.whatsapp.com")

        contacts = load_contacts(self.file_path)
        for _, row in contacts.iterrows():
            phone = str(row['telefone']).strip()
            text = str(row['mensagem']).strip()
            send_message(driver, phone, text)
            time.sleep(2)

        driver.quit()
        messagebox.showinfo("Concluído", "Envio de mensagens finalizado com sucesso.")


def main():
    app = WhatsAutoGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
