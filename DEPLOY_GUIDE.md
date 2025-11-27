# 🐋 WHALE COPY BOT - 24/7 Cloud Deployment Guide

## Your Bot Will:
- Watch wallet: `0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee`
- Copy every trade with $10 (you can change this)
- Run 24/7 even when your Mac is off
- Cost: ~$5/month on Railway

---

# STEP 1: Create Railway Account (2 min)

1. Go to **https://railway.app**
2. Click **"Login"** → **"Login with GitHub"**
3. If you don't have GitHub: go to **https://github.com** and create free account first

---

# STEP 2: Create New Project (1 min)

1. On Railway dashboard, click **"New Project"**
2. Click **"Empty Project"**

---

# STEP 3: Add a Service (1 min)

1. Click **"Add a Service"** (or the + button)
2. Click **"Empty Service"**
3. Name it: `whale-copy-bot`

---

# STEP 4: Upload Your Files (3 min)

### Option A: Connect GitHub (Recommended)
1. Create a new **private** repository on GitHub
2. Upload these files to it:
   - `whale_copy_bot.py`
   - `requirements.txt`
   - `Procfile`
   - `runtime.txt`
3. In Railway, click your service → "Settings" → "Connect Repo"
4. Select your repository

### Option B: Use Railway CLI
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Deploy
railway up
```

---

# STEP 5: Add Environment Variables (2 min)

1. Click on your service in Railway
2. Go to **"Variables"** tab
3. Click **"Add Variable"** for each of these:

```
POLY_PRIVATE_KEY = (your 64-character key, no 0x)
POLY_FUNDER_ADDRESS = 0xbB04a12170d6dbBf81A59416AeAaA90A47DcE7FB
POLY_SIGNATURE_TYPE = 1
WHALE_ADDRESS = 0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee
COPY_AMOUNT_USD = 10
MAX_DAILY_TRADES = 20
MIN_WHALE_TRADE_SIZE = 100
```

⚠️ **IMPORTANT**: Your private key stays secure - Railway encrypts all variables!

---

# STEP 6: Deploy (1 min)

1. Railway will automatically deploy when you add files
2. Click on **"Deployments"** tab to see status
3. Click on the deployment to see logs

---

# STEP 7: Monitor Your Bot

## View Logs:
1. Click your service
2. Click **"Deployments"** 
3. Click latest deployment
4. See live logs!

## Check if it's running:
Look for:
```
✅ Trading client initialized
🚀 BOT STARTED
   Watching whale: 0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee
```

---

# Settings You Can Change

Edit these in Railway Variables:

| Variable | Default | What it does |
|----------|---------|--------------|
| `COPY_AMOUNT_USD` | 10 | How much $ per copied trade |
| `MAX_DAILY_TRADES` | 20 | Max trades per day |
| `MIN_WHALE_TRADE_SIZE` | 100 | Only copy trades > this amount |

---

# Costs

Railway pricing:
- **Free tier**: 500 hours/month (enough for ~20 days)
- **Hobby plan**: $5/month (unlimited, recommended)

The bot uses minimal resources (~$2-3/month actual usage).

---

# Stop/Start the Bot

## To Stop:
1. Go to your service in Railway
2. Click **"Settings"**
3. Click **"Remove Service"** (or just pause deployments)

## To Restart:
1. Click **"Deployments"**
2. Click **"Redeploy"**

---

# Troubleshooting

### "Module not found" error
- Make sure `requirements.txt` is uploaded

### "Invalid private key" error
- Check your private key is 64 characters (no 0x prefix)

### Bot not copying trades
- Whale might not be trading
- Check the logs for errors
- Try lowering `MIN_WHALE_TRADE_SIZE`

---

# 🎉 Done!

Your bot now runs 24/7 copying trades from the whale wallet.

Every time they buy, you buy too!

Check Railway logs periodically to see activity.
