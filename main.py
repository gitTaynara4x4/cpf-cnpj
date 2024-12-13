from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta, timezone

app = Flask(__name__)


load_dotenv()
CODIGO_BITRIX = os.getenv('CODIGO_BITRIX')
CODIGO_BITRIX_STR = os.getenv('CODIGO_BITRIX_STR')
PROFILE = os.getenv('PROFILE')
BASE_URL_API_BITRIX = os.getenv('BASE_URL_API_BITRIX')


BITRIX_WEBHOOK_URL = f"{BASE_URL_API_BITRIX}/{PROFILE}/{CODIGO_BITRIX}"


def validate_cpf(cpf):
    cpf = re.sub(r'\D', '', cpf) 
    if len(cpf) != 11 or cpf in [str(i) * 11 for i in range(10)]:
        return False
    
    for i in range(9, 11): 
        soma = sum(int(cpf[j]) * ((i + 1) - j) for j in range(i))
        digit = (soma * 10 % 11) % 10
        if int(cpf[i]) != digit:
            return False
    return True

def validate_cnpj(cnpj):
    cnpj = re.sub(r'\D', '', cnpj)
    if len(cnpj) != 14 or cnpj in [str(i) * 14 for i in range(10)]:
        return False
    
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1

    for i in [12, 13]:
        soma = sum(int(cnpj[j]) * pesos1[j] for j in range(i)) if i == 12 else sum(int(cnpj[j]) * pesos2[j] for j in range(i)) 
        digit = 11 - soma % 11
        if digit >= 10:
            digito = 0
        if int(cnpj[i]) != digit:
            return False
    return True


def format_doc(number):
    number = re.sub(r'\D', '', number)
    if len(number) == 11:
        return f'{number[:3]}.{number[3:6]}.{number[6:9]}-{number[9:]}'
    elif len(number) == 14: 
        return f'{number[:2]}.{number[2:5]}.{number[5:8]}/{number[8:12]}-{number[12:]}'
    return number

def get_field_bitrix(deal_id, field):
    url_crm = f"{BITRIX_WEBHOOK_URL}/crm.deal.get"
    params = {'id': deal_id}
    response = requests.get(url_crm, params=params)
    if response.status_code == 200:
        data = response.json()
        value = data.get('result', {}).get(field)
        return value
    else:
        print(f"ERRO AO BUSCAR O CAMPO CPF/CNPJ NO CRM: {response.text}")
        return None
    

@app.route('/validate-doc/<int:deal_id>', methods=['POST'])
def validate_doc(deal_id):
    bitrix_field = 'UF_CRM_1697807353336'
    doc = get_field_bitrix(deal_id, bitrix_field)
    if not doc: 
        return jsonify({"ERROR": "NÃO FOI POSSÍVEL PEGAR O CPF OU CNPJ DO CLIENTE."}), 400
    
    doc = re.sub(r'\D', '', doc)
    if len(doc) == 11 and validate_cpf(doc):
        formatted_doc = format_doc(doc)
    elif len(doc) == 14 and validate_cnpj(doc):
        formatted_doc == format_doc(doc)
    else: 
        formatted_doc = 'CPF INVÁLIDO' if len(doc) == 11 else 'CNPJ INVÁLIDO'
    
    update_field(deal_id, bitrix_field, formatted_doc)

    return jsonify({
        "deal_id": deal_id,
        "field": bitrix_field,
        "value": formatted_doc
    })

def update_field(deal_id, field, value):
    url_crm = f"{BITRIX_WEBHOOK_URL}/crm.deal.update"
    payload = {
        'id': deal_id,
        'fields': {
            field: value
        }
    }
    response = requests.post(url_crm, json=payload)
    if response.status_code != 200:
        print(f"ERRO AO ATUALIZAR O CAMPO CPF/CNPJ: {response.text}")
    return response.json()

if __name__ == '__main__':
    app.run(debug=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3449)
