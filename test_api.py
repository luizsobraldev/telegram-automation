import subprocess
import time
import requests

# Inicia o servidor em segundo plano
process = subprocess.Popen([".venv/Scripts/python.exe", "-m", "uvicorn", "app:app", "--port", "8000"])

time.sleep(3) # Aguarda o servidor subir

try:
    print("Enviando requisição POST...")
    response = requests.post(
        "http://127.0.0.1:8000/monitorar",
        json={"url": "https://www.mercadolivre.com.br/headset-sem-fio-pulse-elite-sony-cor-branco/p/MLB35725883"}
    )
    print("Status:", response.status_code)
    print("Response JSON:", response.json())
finally:
    process.terminate()
    print("Servidor encerrado.")
