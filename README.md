# TechPromos com Sobral

<div align="center">

**Monitorador de preços em marketplaces com saída para Telegram e n8n**

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)
![Requests](https://img.shields.io/badge/Requests-2.32-green)
![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup4-4.12-orange)

</div>

---

## 🎯 Sobre o Projeto

Ferramenta de linha de comando desenvolvida em Python para monitorar preços de produtos no **Mercado Livre**. 

A ferramenta extrai o nome do produto e suas variações de preço (Preço original, Preço com desconto/Pix e Preço parcelado). Os dados são retornados em **JSON** (ideal para integração com o n8n) ou formatados como **mensagem pronta para copiar e colar em grupos do Telegram**.

---

## 🚀 Como Instalar

```bash
# 1. Clone o repositório e entre na pasta
git clone https://github.com/seu-usuario/techpromos-sobral.git
cd techpromos-sobral

# 2. Crie e ative o ambiente virtual
python -m venv .venv

# Se estiver no Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Se estiver no Linux / macOS:
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt
```

---

## 📝 Como Adicionar Produtos

Para cadastrar novos produtos para monitoramento em lote, abra o arquivo `produtos.txt` e adicione a URL completa do produto. **Use apenas uma URL por linha.**

```text
# produtos.txt

# Você pode usar a tralha para fazer comentários
https://www.mercadolivre.com.br/console-playstation5-slim.../p/MLB57081243
https://www.mercadolivre.com.br/headset-sem-fio-pulse.../p/MLB35725883
```

> **Dica:** Abra o produto no navegador e copie o link direto da barra de endereços.

---

## ▶️ Como Usar

### 1. Monitorar a lista completa (Formato Telegram)
Lê o arquivo `produtos.txt` e gera as mensagens de todos os produtos cadastrados:
```bash
python monitorar.py
```

**Exemplo de Saída (Telegram):**
```
🔥 Headset Sem Fio Pulse Elite - Sony Cor Branco 🔥

💸 De: R$ 999,90
Por: R$ 743,91 (Pix)
ou 799,90 (Parcelado)

🛒 https://www.mercadolivre.com.br/headset-sem-fio-pulse-elite...

🤑 TECHPROMOS COM SOBRAL
https://t.me/techpromos_sobral 🔥
```

### 2. Monitorar a lista completa (Formato JSON para automações)
Para usar no n8n ou em outras APIs:
```bash
python monitorar.py --formato json
```

### 3. Testar apenas um produto avulso
Se quiser testar uma URL sem adicioná-la à lista:
```bash
python -m techpromos "URL_DO_PRODUTO" --formato telegram
```

---

## ⚙️ Tecnologias Utilizadas

- **Python 3.12+**
- **Requests:** Faz as requisições HTTP simulando o Googlebot para obter os dados completos do Mercado Livre.
- **BeautifulSoup4 & lxml:** Parseia o HTML extraindo os seletores de preço ou a estrutura oculta JSON-LD (schema.org).
- **Pytest:** Suíte de testes automatizados para garantir a estabilidade da raspagem.

---

## 🔧 Personalização

Para alterar o nome do seu grupo do Telegram e o link na mensagem gerada, edite as variáveis no topo do arquivo `techpromos/formatters.py`:

```python
TELEGRAM_GRUPO_NOME: str = "TECHPROMOS COM SOBRAL"
TELEGRAM_GRUPO_LINK: str = "https://t.me/techpromos_sobral"
```
