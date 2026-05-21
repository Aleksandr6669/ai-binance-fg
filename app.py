from flask import Flask, render_template, request, jsonify
from binance_client import BinanceClient

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/portfolio", methods=["GET"])
def portfolio():
    # Extract API Keys securely from the Request Headers
    api_key = request.headers.get("X-MBX-APIKEY")
    api_secret = request.headers.get("X-MBX-SECRET")

    if not api_key or not api_secret:
        return jsonify({"error": "Missing Binance API credentials in headers"}), 401

    try:
        # Initialize client per request (Stateless)
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
        
        # Determine target fiat from query parameter, default to UAH
        fiat = request.args.get("fiat", "UAH")
        
        portfolio_data = client.get_full_portfolio(fiat_currency=fiat)
        return jsonify(portfolio_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=8000)
