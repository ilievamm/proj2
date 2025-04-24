from flask import Flask, request, jsonify
from web3 import Web3
from dotenv import load_dotenv
import os
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)

BNB_RPC = os.getenv("BNB_RPC", "https://data-seed-prebsc-1-s1.binance.org:8545")
w3 = Web3(Web3.HTTPProvider(BNB_RPC))

ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
]

@app.route('/risk-score', methods=['POST'])
def get_risk_score():
    data = request.json
    contract_address = data.get('address')

    if not w3.is_address(contract_address):
        return jsonify({"error": "Invalid address"}), 400

    contract_address = Web3.to_checksum_address(contract_address)

    try:
        code = w3.eth.get_code(contract_address)
        if code == b'':
            return jsonify({'error': 'This is not a contract address'}), 400

        score = 0
        explanations = []
        code_hex = code.hex()

        # Проверка опасных инструкций
        if 'delegatecall' in code_hex:
            score += 30
            explanations.append("Используется опасная инструкция delegatecall")
        if 'selfdestruct' in code_hex:
            score += 20
            explanations.append("Контракт может быть уничтожен через selfdestruct")
        if 'tx.origin' in code_hex:
            score += 20
            explanations.append("Используется tx.origin — это может быть уязвимость")

        # Проверка адреса
        if contract_address.lower().startswith("0x0"):
            score += 15
            explanations.append("Контракт имеет подозрительно чистый адрес")

        contract = w3.eth.contract(address=contract_address, abi=ERC20_ABI)
        name = "Неизвестно"
        symbol = "???"
        decimals = 0

        try:
            name = contract.functions.name().call()
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
        except:
            score += 15
            explanations.append("Отсутствует имя/символ/десятичные знаки — токен может быть фейковым")

        # Проверка эмиссии
        try:
            supply = contract.functions.totalSupply().call()
            if supply > 1e27:
                score += 10
                explanations.append("Очень большая эмиссия токена")
        except:
            pass

        # Ограничение балла
        score = min(score, 100)

        return jsonify({
            "address": contract_address,
            "risk_score": score,
            "explanations": explanations,
            "token_info": {
                "name": name,
                "symbol": symbol,
                "decimals": decimals
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Connected:", w3.is_connected())
    app.run(debug=True)
