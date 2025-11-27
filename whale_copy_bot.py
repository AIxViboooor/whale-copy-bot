"""
🐋 WHALE COPY TRADING BOT
==========================
Copies trades from a specific whale wallet on Polymarket.

When the whale buys YES → you buy YES
When the whale buys NO → you buy NO

LIVE MODE - Real money trading!

Author: Built with Claude
"""

import asyncio
import json
import time
import os
from datetime import datetime, timezone
from typing import Optional, Dict, List
from dataclasses import dataclass
import httpx

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# =============================================================================
# CONFIGURATION
# =============================================================================

# Whale to copy
WHALE_ADDRESS = os.getenv("WHALE_ADDRESS", "0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee")

# Your credentials
POLY_PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY", "")
POLY_FUNDER_ADDRESS = os.getenv("POLY_FUNDER_ADDRESS", "")
POLY_SIGNATURE_TYPE = int(os.getenv("POLY_SIGNATURE_TYPE", "1"))

# Trading settings
COPY_AMOUNT_USD = float(os.getenv("COPY_AMOUNT_USD", "10"))  # Amount per copied trade
MAX_DAILY_TRADES = int(os.getenv("MAX_DAILY_TRADES", "20"))
MIN_WHALE_TRADE_SIZE = float(os.getenv("MIN_WHALE_TRADE_SIZE", "100"))  # Only copy trades > $100

# API URLs
POLYMARKET_CLOB = "https://clob.polymarket.com"
POLYMARKET_DATA = "https://data-api.polymarket.com"
POLYMARKET_GAMMA = "https://gamma-api.polymarket.com"


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class WhaleTrade:
    """Represents a trade made by the whale"""
    timestamp: str
    market_id: str
    market_title: str
    side: str  # "BUY" or "SELL"
    outcome: str  # "YES" or "NO"
    amount_usd: float
    price: float
    token_id: str


@dataclass
class CopiedTrade:
    """Represents a trade we copied"""
    whale_trade: WhaleTrade
    our_amount: float
    success: bool
    timestamp: str


# =============================================================================
# POLYMARKET CLIENT
# =============================================================================

class PolymarketTrader:
    """Handles all Polymarket trading operations"""
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self.clob_client = None
        self.initialized = False
        self.markets_cache: Dict[str, dict] = {}
    
    async def initialize(self):
        """Initialize trading client"""
        if not POLY_PRIVATE_KEY:
            print("❌ No private key configured!")
            return False
        
        try:
            from py_clob_client.client import ClobClient
            
            self.clob_client = ClobClient(
                POLYMARKET_CLOB,
                key=POLY_PRIVATE_KEY,
                chain_id=137,
                signature_type=POLY_SIGNATURE_TYPE,
                funder=POLY_FUNDER_ADDRESS
            )
            creds = self.clob_client.create_or_derive_api_creds()
            self.clob_client.set_api_creds(creds)
            self.initialized = True
            print("✅ Trading client initialized")
            return True
        except Exception as e:
            print(f"❌ Init error: {e}")
            return False
    
    async def get_market_info(self, condition_id: str) -> Optional[dict]:
        """Get market info by condition ID"""
        if condition_id in self.markets_cache:
            return self.markets_cache[condition_id]
        
        try:
            response = await self.http.get(
                f"{POLYMARKET_GAMMA}/markets/{condition_id}"
            )
            if response.status_code == 200:
                market = response.json()
                self.markets_cache[condition_id] = market
                return market
        except:
            pass
        
        return None
    
    async def get_token_info(self, token_id: str) -> Optional[dict]:
        """Get token info to determine YES/NO and market"""
        try:
            response = await self.http.get(
                f"{POLYMARKET_CLOB}/token/{token_id}"
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    async def buy(self, token_id: str, amount_usd: float) -> bool:
        """Execute a market buy order"""
        if not self.initialized:
            print("❌ Client not initialized")
            return False
        
        try:
            from py_clob_client.clob_types import MarketOrderArgs, OrderType
            from py_clob_client.order_builder.constants import BUY
            
            # Create market order
            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount_usd,
                side=BUY,
            )
            
            signed_order = self.clob_client.create_market_order(order_args)
            result = self.clob_client.post_order(signed_order, OrderType.FOK)
            
            print(f"✅ BUY order executed: {result}")
            return True
            
        except Exception as e:
            print(f"❌ BUY order failed: {e}")
            return False
    
    async def sell(self, token_id: str, amount_usd: float) -> bool:
        """Execute a market sell order"""
        if not self.initialized:
            print("❌ Client not initialized")
            return False
        
        try:
            from py_clob_client.clob_types import MarketOrderArgs, OrderType
            from py_clob_client.order_builder.constants import SELL
            
            # Create market order
            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount_usd,
                side=SELL,
            )
            
            signed_order = self.clob_client.create_market_order(order_args)
            result = self.clob_client.post_order(signed_order, OrderType.FOK)
            
            print(f"✅ SELL order executed: {result}")
            return True
            
        except Exception as e:
            print(f"❌ SELL order failed: {e}")
            return False
    
    async def close(self):
        await self.http.aclose()


# =============================================================================
# WHALE TRACKER
# =============================================================================

class WhaleTracker:
    """Tracks trades from the whale wallet"""
    
    def __init__(self, whale_address: str):
        self.whale_address = whale_address.lower()
        self.http = httpx.AsyncClient(timeout=30.0)
        self.last_seen_trade_id: Optional[str] = None
        self.seen_trades: set = set()
    
    async def get_recent_trades(self) -> List[WhaleTrade]:
        """Fetch recent trades from the whale"""
        trades = []
        
        # Try the profiles activity endpoint first
        try:
            response = await self.http.get(
                f"https://data-api.polymarket.com/activity",
                params={
                    "address": self.whale_address,
                    "limit": 20
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data:
                    try:
                        trade_id = item.get("id") or item.get("transactionHash") or f"{item.get('timestamp')}_{item.get('asset')}"
                        
                        if trade_id in self.seen_trades:
                            continue
                        
                        side = item.get("side", "").upper()
                        if side not in ["BUY", "SELL"]:
                            # Try to infer from type
                            trade_type = item.get("type", "").upper()
                            if "BUY" in trade_type:
                                side = "BUY"
                            elif "SELL" in trade_type:
                                side = "SELL"
                            else:
                                continue
                        
                        amount = float(item.get("usdcSize", 0) or item.get("value", 0) or item.get("size", 0) or 0)
                        if amount < MIN_WHALE_TRADE_SIZE:
                            continue
                        
                        # Get token ID from various possible fields
                        token_id = (
                            item.get("asset") or 
                            item.get("assetId") or 
                            item.get("asset_id") or
                            item.get("tokenId") or 
                            item.get("token_id") or
                            item.get("outcomeTokenId") or
                            ""
                        )
                        
                        trades.append(WhaleTrade(
                            timestamp=item.get("timestamp", ""),
                            market_id=item.get("conditionId", item.get("condition_id", item.get("market", ""))),
                            market_title=item.get("title", item.get("question", item.get("marketTitle", "Unknown"))),
                            side=side,
                            outcome=item.get("outcome", item.get("outcomeName", "YES")),
                            amount_usd=amount,
                            price=float(item.get("price", 0.5)),
                            token_id=token_id
                        ))
                        
                        self.seen_trades.add(trade_id)
                        
                    except Exception as e:
                        print(f"⚠️  Error parsing trade: {e}")
                        continue
                        
        except Exception as e:
            print(f"⚠️  Activity endpoint error: {e}")
        
        # Also try the trades endpoint
        try:
            response = await self.http.get(
                f"https://clob.polymarket.com/trades",
                params={
                    "maker_address": self.whale_address,
                    "limit": 20
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data if isinstance(data, list) else data.get("trades", data.get("data", []))
                
                for item in items:
                    try:
                        trade_id = item.get("id") or item.get("trade_id") or f"{item.get('timestamp')}_{item.get('asset_id')}"
                        if trade_id in self.seen_trades:
                            continue
                        
                        # Get side
                        side = item.get("side", "").upper()
                        if side not in ["BUY", "SELL"]:
                            side = "BUY" if item.get("is_taker_buy", True) else "SELL"
                        
                        # Calculate amount
                        size = float(item.get("size", 0) or item.get("amount", 0) or 0)
                        price = float(item.get("price", 0.5))
                        amount = size * price if size > 10 else size  # Handle different formats
                        
                        if amount < MIN_WHALE_TRADE_SIZE:
                            continue
                        
                        token_id = item.get("asset_id") or item.get("token_id") or item.get("market_id") or ""
                        
                        if not token_id:
                            continue
                        
                        outcome = "YES" if item.get("outcome_index", 0) == 0 else "NO"
                        
                        trades.append(WhaleTrade(
                            timestamp=item.get("timestamp", item.get("created_at", "")),
                            market_id=item.get("condition_id", item.get("market", "")),
                            market_title=item.get("market_slug", item.get("title", "Unknown")),
                            side=side,
                            outcome=outcome,
                            amount_usd=amount,
                            price=price,
                            token_id=token_id
                        ))
                        
                        self.seen_trades.add(trade_id)
                        
                    except Exception as e:
                        continue
                        
        except Exception as e:
            print(f"⚠️  Trades endpoint error: {e}")
        
        # Try taker trades endpoint
        try:
            response = await self.http.get(
                f"https://clob.polymarket.com/trades",
                params={
                    "taker_address": self.whale_address,
                    "limit": 20
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data if isinstance(data, list) else data.get("trades", data.get("data", []))
                
                for item in items:
                    try:
                        trade_id = item.get("id") or f"taker_{item.get('timestamp')}_{item.get('asset_id')}"
                        if trade_id in self.seen_trades:
                            continue
                        
                        side = "BUY" if item.get("side", "").upper() == "BUY" else "SELL"
                        
                        size = float(item.get("size", 0) or 0)
                        price = float(item.get("price", 0.5))
                        amount = size * price if size > 10 else size
                        
                        if amount < MIN_WHALE_TRADE_SIZE:
                            continue
                        
                        token_id = item.get("asset_id") or item.get("token_id") or ""
                        
                        if not token_id:
                            continue
                        
                        trades.append(WhaleTrade(
                            timestamp=item.get("timestamp", ""),
                            market_id=item.get("condition_id", ""),
                            market_title=item.get("market_slug", "Unknown"),
                            side=side,
                            outcome="YES" if item.get("outcome_index", 0) == 0 else "NO",
                            amount_usd=amount,
                            price=price,
                            token_id=token_id
                        ))
                        
                        self.seen_trades.add(trade_id)
                        
                    except:
                        continue
                        
        except Exception as e:
            pass
        
        return trades
    
    async def close(self):
        await self.http.aclose()


# =============================================================================
# MAIN BOT
# =============================================================================

class WhaleCopyBot:
    """Main whale copy trading bot"""
    
    def __init__(self):
        self.trader = PolymarketTrader()
        self.tracker = WhaleTracker(WHALE_ADDRESS)
        self.running = False
        self.trades_today = 0
        self.total_copied = 0
        self.copied_trades: List[CopiedTrade] = []
        self.start_time = None
    
    async def initialize(self):
        """Initialize the bot"""
        print_banner()
        
        success = await self.trader.initialize()
        if not success:
            return False
        
        print_config()
        return True
    
    async def copy_trade(self, whale_trade: WhaleTrade) -> bool:
        """Copy a whale trade"""
        
        print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║ 🐋 WHALE TRADE DETECTED!                                             ║
╠══════════════════════════════════════════════════════════════════════╣
║ Market:  {whale_trade.market_title[:55]:<55}
║ Side:    {whale_trade.side} {whale_trade.outcome}
║ Amount:  ${whale_trade.amount_usd:,.2f}
║ Price:   ${whale_trade.price:.3f}
╠══════════════════════════════════════════════════════════════════════╣
║ 📋 COPYING TRADE...                                                  ║
║ Our Amount: ${COPY_AMOUNT_USD:.2f}
╚══════════════════════════════════════════════════════════════════════╝
        """)
        
        if self.trades_today >= MAX_DAILY_TRADES:
            print("⚠️  Daily trade limit reached, skipping")
            return False
        
        if not whale_trade.token_id:
            print("⚠️  No token ID available, skipping")
            return False
        
        # Execute our copy trade - BUY or SELL
        if whale_trade.side == "BUY":
            success = await self.trader.buy(whale_trade.token_id, COPY_AMOUNT_USD)
        elif whale_trade.side == "SELL":
            success = await self.trader.sell(whale_trade.token_id, COPY_AMOUNT_USD)
        else:
            print(f"⚠️  Unknown trade side: {whale_trade.side}, skipping")
            return False
        
        if success:
            self.trades_today += 1
            self.total_copied += 1
            print(f"✅ Successfully copied {whale_trade.side} trade!")
        else:
            print(f"❌ Failed to copy trade")
        
        self.copied_trades.append(CopiedTrade(
            whale_trade=whale_trade,
            our_amount=COPY_AMOUNT_USD,
            success=success,
            timestamp=datetime.now(timezone.utc).isoformat()
        ))
        
        return success
    
    async def run(self):
        """Main bot loop"""
        self.running = True
        self.start_time = datetime.now(timezone.utc)
        
        print(f"""
🚀 BOT STARTED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
   Watching whale: {WHALE_ADDRESS}
   Copy amount: ${COPY_AMOUNT_USD}
   Press Ctrl+C to stop
        """)
        
        scan_count = 0
        
        while self.running:
            try:
                scan_count += 1
                
                # Check for new whale trades
                new_trades = await self.tracker.get_recent_trades()
                
                if new_trades:
                    print(f"\n🔍 Found {len(new_trades)} new whale trade(s)!")
                    
                    for trade in new_trades:
                        await self.copy_trade(trade)
                        await asyncio.sleep(1)  # Small delay between copies
                
                # Status update every 10 scans
                if scan_count % 10 == 0:
                    self.print_status()
                
                # Reset daily counter at midnight UTC
                now = datetime.now(timezone.utc)
                if now.hour == 0 and now.minute == 0:
                    self.trades_today = 0
                
                # Wait before next scan
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                await asyncio.sleep(60)
    
    def print_status(self):
        """Print current status"""
        uptime = datetime.now(timezone.utc) - self.start_time if self.start_time else "N/A"
        
        print(f"""
┌──────────────────────────────────────────────────────────────────────┐
│ 📊 STATUS - {datetime.now().strftime('%H:%M:%S')}                                              │
├──────────────────────────────────────────────────────────────────────┤
│ Uptime:          {str(uptime).split('.')[0]:<52}│
│ Trades Today:    {self.trades_today}/{MAX_DAILY_TRADES:<50}│
│ Total Copied:    {self.total_copied:<52}│
│ Watching:        {WHALE_ADDRESS[:20]}...{' '*28}│
└──────────────────────────────────────────────────────────────────────┘
        """)
    
    async def close(self):
        """Cleanup"""
        self.running = False
        await self.trader.close()
        await self.tracker.close()
        
        print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║ 📊 SESSION SUMMARY                                                   ║
╠══════════════════════════════════════════════════════════════════════╣
║ Total Trades Copied: {self.total_copied:<48}║
║ Successful:          {sum(1 for t in self.copied_trades if t.success):<48}║
║ Failed:              {sum(1 for t in self.copied_trades if not t.success):<48}║
╚══════════════════════════════════════════════════════════════════════╝
        """)


# =============================================================================
# DISPLAY
# =============================================================================

def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🐋 WHALE COPY TRADING BOT 🐋                                       ║
║                                                                      ║
║   Copy trades from successful Polymarket traders                     ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)


def print_config():
    print(f"""
┌──────────────────────────────────────────────────────────────────────┐
│ CONFIGURATION                                                        │
├──────────────────────────────────────────────────────────────────────┤
│ Mode:              🔴 LIVE TRADING                                   │
│ Whale Address:     {WHALE_ADDRESS[:20]}...                          │
│ Copy Amount:       ${COPY_AMOUNT_USD:<48.2f}│
│ Max Daily Trades:  {MAX_DAILY_TRADES:<50}│
│ Min Whale Trade:   ${MIN_WHALE_TRADE_SIZE:<48.0f}│
└──────────────────────────────────────────────────────────────────────┘
    """)


# =============================================================================
# MAIN
# =============================================================================

async def main():
    bot = WhaleCopyBot()
    
    success = await bot.initialize()
    if not success:
        print("❌ Failed to initialize bot")
        return
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Stopping bot...")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
