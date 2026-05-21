import time
import hmac
import hashlib
import requests

class BinanceClient:
    BASE_URL = "https://api.binance.com"
    
    def __init__(self, api_key: str = "", api_secret: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        
    def set_credentials(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        
    def _get_server_time_offset(self) -> int:
        """Get offset between local time and Binance server time in ms to avoid timestamp errors."""
        try:
            url = f"{self.BASE_URL}/api/v3/time"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            server_time = response.json().get("serverTime")
            local_time = int(time.time() * 1000)
            return server_time - local_time
        except Exception:
            return 0

    def _sign_query(self, query_string: str) -> str:
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
    def _get_signed_headers(self) -> dict:
        return {
            "X-MBX-APIKEY": self.api_key
        }
        
    def get_ticker_prices(self) -> dict:
        """Fetch all symbol prices in USDT/BTC etc. to use for balance conversion."""
        try:
            url = f"{self.BASE_URL}/api/v3/ticker/price"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {item["symbol"]: float(item["price"]) for item in data}
        except Exception as e:
            print(f"Error fetching ticker prices: {e}")
            return {}
            
    def get_spot_balances(self, time_offset: int = 0) -> list:
        """Fetch spot wallet balances with positive amounts."""
        if not self.api_key or not self.api_secret:
            raise ValueError("API Key and Secret must be provided")
            
        timestamp = int(time.time() * 1000) + time_offset
        query_string = f"timestamp={timestamp}&recvWindow=60000"
        signature = self._sign_query(query_string)
        
        url = f"{self.BASE_URL}/api/v3/account?{query_string}&signature={signature}"
        headers = self._get_signed_headers()
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 401:
            raise PermissionError("Invalid API Key or Secret")
        elif response.status_code == 400:
            err_data = response.json()
            raise Exception(f"Binance API Error: {err_data.get('msg', 'Bad Request')}")
        response.raise_for_status()
        
        data = response.json()
        balances = []
        for b in data.get("balances", []):
            free = float(b.get("free", 0.0))
            locked = float(b.get("locked", 0.0))
            total = free + locked
            if total > 0.000001:  # Filter out dust balances below standard thresholds
                balances.append({
                    "asset": b["asset"],
                    "free": free,
                    "locked": locked,
                    "total": total,
                    "wallet": "Spot"
                })
        return balances

    def get_funding_balances(self, time_offset: int = 0) -> list:
        """Fetch funding wallet balances with positive amounts."""
        if not self.api_key or not self.api_secret:
            raise ValueError("API Key and Secret must be provided")
            
        timestamp = int(time.time() * 1000) + time_offset
        query_string = f"timestamp={timestamp}&recvWindow=60000"
        signature = self._sign_query(query_string)
        
        url = f"{self.BASE_URL}/sapi/v1/asset/get-funding-asset"
        headers = self._get_signed_headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        
        payload = f"{query_string}&signature={signature}"
        
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        
        if response.status_code == 401:
            raise PermissionError("Invalid API Key or Secret")
        elif response.status_code == 403:
            raise PermissionError("API key does not have permission to access Funding wallet. Please verify API settings on Binance.")
        elif response.status_code == 400:
            err_data = response.json()
            raise Exception(f"Binance API Error: {err_data.get('msg', 'Bad Request')}")
        response.raise_for_status()
        
        data = response.json()
        balances = []
        for b in data:
            free = float(b.get("free", 0.0))
            locked = float(b.get("locked", 0.0))
            freeze = float(b.get("freeze", 0.0))
            withdrawing = float(b.get("withdrawing", 0.0))
            total = free + locked + freeze + withdrawing
            if total > 0.000001:
                balances.append({
                    "asset": b["asset"],
                    "free": free,
                    "locked": locked + freeze + withdrawing,
                    "total": total,
                    "wallet": "Funding"
                })
        return balances

    def get_wallet_balances(self, time_offset: int = 0) -> list:
        """Fetch unified wallet balances using GET /sapi/v1/asset/wallet/balance."""
        if not self.api_key or not self.api_secret:
            raise ValueError("API Key and Secret must be provided")
            
        timestamp = int(time.time() * 1000) + time_offset
        query_string = f"timestamp={timestamp}&recvWindow=60000"
        signature = self._sign_query(query_string)
        
        url = f"{self.BASE_URL}/sapi/v1/asset/wallet/balance?{query_string}&signature={signature}"
        headers = self._get_signed_headers()
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 401:
            raise PermissionError("Invalid API Key or Secret")
        elif response.status_code == 400:
            err_data = response.json()
            raise Exception(f"Binance API Error: {err_data.get('msg', 'Bad Request')}")
        response.raise_for_status()
        return response.json()

    def get_full_portfolio(self) -> dict:
        """Fetch and aggregate Spot, Funding, Trading Bots, and Futures balances with conversion to USD."""
        time_offset = self._get_server_time_offset()
        prices = self.get_ticker_prices()
        
        spot_error = None
        funding_error = None
        wallet_error = None
        spot_balances = []
        funding_balances = []
        wallet_balances = []
        
        try:
            spot_balances = self.get_spot_balances(time_offset)
        except Exception as e:
            spot_error = str(e)
            
        try:
            funding_balances = self.get_funding_balances(time_offset)
        except Exception as e:
            # If Funding fails but Spot succeeds, we want to proceed and let user know about the Funding restriction
            funding_error = str(e)
            
        try:
            wallet_balances = self.get_wallet_balances(time_offset)
        except Exception as e:
            wallet_error = str(e)
            
        if spot_error and funding_error and wallet_error:
            # If all failed, we cannot show any portfolio
            raise Exception(f"Could not load balances:\nSpot: {spot_error}\nFunding: {funding_error}\nWallet: {wallet_error}")
            
        aggregated = []
        spot_usd = 0.0
        funding_usd = 0.0
        trading_bots_usd = 0.0
        futures_usd = 0.0
        
        def get_usd_value(asset, amount):
            if asset in ("USDT", "USDC", "BUSD", "USD"):
                return amount
            
            # Check price of direct USDT pairs
            if f"{asset}USDT" in prices:
                return amount * prices[f"{asset}USDT"]
            if f"USDT{asset}" in prices:
                return amount / prices[f"USDT{asset}"]
            if f"{asset}BUSD" in prices:
                return amount * prices[f"{asset}BUSD"]
            if f"BUSD{asset}" in prices:
                return amount / prices[f"BUSD{asset}"]
            if f"{asset}USDC" in prices:
                return amount * prices[f"{asset}USDC"]
            if f"USDC{asset}" in prices:
                return amount / prices[f"USDC{asset}"]
                
            # Secondary check with BTC pair
            if f"{asset}BTC" in prices and "BTCUSDT" in prices:
                return amount * prices[f"{asset}BTC"] * prices["BTCUSDT"]
                
            # Secondary check with ETH pair
            if f"{asset}ETH" in prices and "ETHUSDT" in prices:
                return amount * prices[f"{asset}ETH"] * prices["ETHUSDT"]
                
            return 0.0
            
        for asset_data in spot_balances:
            val = get_usd_value(asset_data["asset"], asset_data["total"])
            price = val / asset_data["total"] if asset_data["total"] > 0 else 0.0
            spot_usd += val
            aggregated.append({
                **asset_data,
                "usd_value": val,
                "price": price
            })
            
        for asset_data in funding_balances:
            val = get_usd_value(asset_data["asset"], asset_data["total"])
            price = val / asset_data["total"] if asset_data["total"] > 0 else 0.0
            funding_usd += val
            aggregated.append({
                **asset_data,
                "usd_value": val,
                "price": price
            })
            
        # Parse specialized Trading Bots and Futures wallets from unified wallet balances
        btc_price = prices.get("BTCUSDT", 95000.0)
        for w in wallet_balances:
            name = w.get("walletName")
            balance_val = float(w.get("balance", 0.0))
            if balance_val > 0.0:
                if name == "Trading Bots":
                    val = balance_val * btc_price
                    trading_bots_usd += val
                    aggregated.append({
                        "asset": "BTC (Бот)",
                        "free": balance_val,
                        "locked": 0.0,
                        "total": balance_val,
                        "wallet": "Trading Bots",
                        "usd_value": val,
                        "price": btc_price
                    })
                elif name in ("USDⓈ-M Futures", "COIN-M Futures"):
                    # Check if there is active balance in Futures not covered under standard spot/funding
                    val = balance_val * btc_price
                    futures_usd += val
                    aggregated.append({
                        "asset": "BTC (Фьюч)",
                        "free": balance_val,
                        "locked": 0.0,
                        "total": balance_val,
                        "wallet": "Futures",
                        "usd_value": val,
                        "price": btc_price
                    })
            
        aggregated.sort(key=lambda x: x["usd_value"], reverse=True)
        
        total_usd = spot_usd + funding_usd + trading_bots_usd + futures_usd
        for asset_data in aggregated:
            asset_data["percentage"] = (asset_data["usd_value"] / total_usd * 100.0) if total_usd > 0 else 0.0
            
        # Get common exchange rates from live market prices (default fallbacks)
        fiat_rates = {
            "UAH": prices.get("USDTUAH", 40.2),
            "EUR": 1.0 / prices.get("EURUSDT") if "EURUSDT" in prices else 0.92,
            "RUB": prices.get("USDTRUB") if "USDTRUB" in prices else 91.5,
            "BTC": 1.0 / prices.get("BTCUSDT") if "BTCUSDT" in prices else 0.00001
        }
        
        # Try to query the official global exchange rates API to get exact bank rates
        try:
            res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=3)
            if res.status_code == 200:
                ext_rates = res.json().get("rates", {})
                # Use official bank rates for UAH and EUR to match standard display expectations
                if "UAH" in ext_rates:
                    fiat_rates["UAH"] = ext_rates["UAH"]
                if "EUR" in ext_rates:
                    fiat_rates["EUR"] = ext_rates["EUR"]
                # For RUB, we intentionally prefer the free-market Binance rate (USDTRUB) 
                # because the official rate is artificial due to capital controls.
        except Exception as e:
            print(f"Error fetching external exchange rates: {e}")
        
        return {
            "assets": aggregated,
            "total_usd": total_usd,
            "spot_usd": spot_usd,
            "funding_usd": funding_usd,
            "trading_bots_usd": trading_bots_usd,
            "futures_usd": futures_usd,
            "spot_error": spot_error,
            "funding_error": funding_error or wallet_error,
            "fiat_rates": fiat_rates
        }

