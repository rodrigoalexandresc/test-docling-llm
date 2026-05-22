import re
import json
import ollama

from pydantic import BaseModel, field_validator
from docling.document_converter import DocumentConverter

# ==========================================
# SCHEMA / GUARD RAILS
# ==========================================

class CRLV(BaseModel):

    placa: str | None = None
    renavam: str | None = None
    chassi: str | None = None
    proprietario: str | None = None

    @field_validator("placa")
    def validar_placa(cls, v):

        if v is None:
            return v

        if not re.match(r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$', v):
            raise ValueError("Placa inválida")

        return v

    @field_validator("renavam")
    def validar_renavam(cls, v):

        if v is None:
            return v

        if not re.match(r'^\d{11}$', v):
            raise ValueError("RENAVAM inválido")

        return v

# ==========================================
# OCR / DOCLING
# ==========================================

converter = DocumentConverter()

result = converter.convert(
    "crlv.pdf",
    max_num_pages=1
)

# TEXTO SIMPLES
texto = result.document.export_to_text()

# ==========================================
# LIMPEZA / REDUÇÃO TOKENS
# ==========================================

# remove múltiplos espaços
texto = re.sub(r'\s+', ' ', texto)

# remove caracteres estranhos
texto = re.sub(r'[^\w\s:/.-]', ' ', texto)

# remove palavras muito pequenas
texto = re.sub(r'\b\w{1,2}\b', ' ', texto)

# reduz espaços novamente
texto = re.sub(r'\s+', ' ', texto)

# limita tamanho
texto = texto[:2500]

# ==========================================
# EXTRAÇÃO BARATA VIA REGEX
# ==========================================

placa_match = re.search(
    r'[A-Z]{3}[0-9][A-Z][0-9]{2}',
    texto
)

renavam_match = re.search(
    r'\b\d{11}\b',
    texto
)

placa = placa_match.group(0) if placa_match else None
renavam = renavam_match.group(0) if renavam_match else None

# ==========================================
# REMOVE DADOS JÁ EXTRAÍDOS
# REDUZ TOKENS
# ==========================================

if placa:
    texto = texto.replace(placa, '')

if renavam:
    texto = texto.replace(renavam, '')

# ==========================================
# PROMPT MINIMALISTA
# ==========================================

prompt = f"""
Extraia somente:

- chassi
- proprietario
- cpf proprietário

Retorne JSON válido.

Texto:
{texto}
"""

# ==========================================
# LLM
# ==========================================

response = ollama.chat(
    model='qwen2.5vl:7b',
    messages=[
        {
            'role': 'user',
            'content': prompt
        }
    ]
)

# ==========================================
# TOKENS
# ==========================================

print("\n===== TOKENS =====")

print(
    "Prompt:",
    response.get("prompt_eval_count")
)

print(
    "Resposta:",
    response.get("eval_count")
)

# ==========================================
# PARSE JSON
# ==========================================

content = response['message']['content']

# remove markdown JSON
content = content.replace("```json", "")
content = content.replace("```", "")

data = json.loads(content)

# injeta regex
data["placa"] = placa
data["renavam"] = renavam

# ==========================================
# VALIDAÇÃO FINAL
# ==========================================

crlv = CRLV.model_validate(data)

print("\n===== RESULTADO =====")

print(crlv.model_dump_json(indent=2))