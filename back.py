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

# Минимальный ABI BEP-20 токена
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]

@app.route('/risk-score', methods=['POST'])
def get_risk_score():
    data = request.json
    raw_address = data.get('address')

    try:
        address = Web3.to_checksum_address(raw_address)
    except ValueError:
        return jsonify({"error": "Invalid address format"}), 400

    if not w3.is_address(address):
        return jsonify({"error": "Invalid address"}), 400

    try:
        code = w3.eth.get_code(address)
        if code == b'' or code == '0x':
            return jsonify({'error': 'This is not a contract address'}), 400

        # Получаем имя и символ токена
        contract = w3.eth.contract(address=address, abi=ERC20_ABI)

        try:
            name = contract.functions.name().call()
        except Exception:
            name = None

        try:
            symbol = contract.functions.symbol().call()
        except Exception:
            symbol = None

        score = 0
        code_hex = code.hex()
        if code_hex.count("a") > 150:
            score += 40
        if address.lower().startswith("0x0"):
            score += 30
        score = min(score, 100)

        return jsonify({
            "address": address,
            "risk_score": score,
            "name": name,
            "symbol": symbol
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Connected:", w3.is_connected())
    print("Chain ID:", w3.eth.chain_id)
    app.run(debug=True)
