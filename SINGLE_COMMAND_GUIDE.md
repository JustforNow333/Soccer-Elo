# Single Command Setup Guide

## 🚀 **One Command to Rule Them All**

I've created a single command that intelligently handles your entire Top 250 teams workflow:

```bash
./start_worker.sh start
```

That's it! The worker will:
✅ **Automatically detect what needs to be done**
✅ **Map your 250 teams to API IDs**
✅ **Import historical data from 2000**
✅ **Start live updates (daily fixtures + 5-minute matches)**
✅ **Stay within your 7,500 API request limit**

## 📋 **Available Commands**

### **Core Commands**
```bash
# Start the complete workflow (recommended)
./start_worker.sh start

# Start with monitoring (auto-restart if crashes)
./start_worker.sh monitor

# Check status
./start_worker.sh status

# View live logs
./start_worker.sh logs

# Stop the worker
./start_worker.sh stop

# Restart the worker
./start_worker.sh restart
```

### **Advanced Commands**
```bash
# Manual control (if needed)
python3 top_250_worker.py --complete      # Complete workflow
python3 top_250_worker.py --setup         # Setup only
python3 top_250_worker.py --scheduler     # Live updates only
python3 top_250_worker.py --status        # Show status
python3 top_250_worker.py --map-only      # Map teams only
python3 top_250_worker.py --historical-only  # Historical import only
```

## 🧠 **Intelligent Workflow**

The worker automatically decides what to do based on current state:

### **First Run (Team Mapping)**
- 🔍 Searches for your 250 teams across all leagues
- 🗺️ Maps team names to API-Football IDs
- 💾 Saves mappings to avoid re-doing this step
- 📊 Uses ~300 API requests

### **Second Phase (Historical Import)**
- 📚 Imports data from 2000 to present
- 🏆 Processes each season systematically
- ⏸️ Stops before hitting API limits
- 📊 Uses ~5,000 API requests (one-time)

### **Live Updates (Continuous)**
- 📅 Daily fixture updates at 6 AM UTC
- ⚡ 5-minute match updates
- 🔄 Processes 50 teams per 5-minute cycle
- 📊 Uses only ~300 API requests per day

## 🎯 **For Background Workers**

### **Production Setup**
```bash
# Set your API key
export API_FOOTBALL_KEY="your_api_key_here"

# Start with monitoring (recommended for production)
./start_worker.sh monitor
```

### **What the Monitor Does**
- ✅ Automatically restarts if the worker crashes
- ✅ Logs all activity
- ✅ Retries up to 5 times with delays
- ✅ Runs continuously in the background

### **Docker/Container Setup**
```bash
# In your container startup script
export API_FOOTBALL_KEY="your_api_key_here"
cd /path/to/your/project
./start_worker.sh monitor
```

## 📊 **Status Monitoring**

### **Check Status Anytime**
```bash
./start_worker.sh status
```

**Shows:**
- 🔑 API key status
- 🗺️ Team mapping progress (X/250 teams)
- 📚 Historical import status
- 🔄 Scheduler status
- 📈 Today's API usage
- 💡 Recommendations for next steps

### **View Live Logs**
```bash
./start_worker.sh logs
```

## 🔧 **Files Created**

```
├── top_250_worker.py         # Intelligent worker script
├── start_worker.sh          # Background worker launcher
├── worker.log               # Activity logs
├── worker.pid               # Process ID file
├── worker_status.json       # Worker state tracking
├── team_id_mapping.json     # Team mappings (persistent)
├── api_requests_YYYYMMDD.log # Daily API request logs
└── SINGLE_COMMAND_GUIDE.md  # This guide
```

## 📈 **API Usage Breakdown**

| Phase | Requests | When |
|-------|----------|------|
| **Setup** | ~5,300 | One-time |
| **Daily** | ~300 | Every day |
| **Total** | ~5,600 | First run |

## 🚦 **Quick Start**

1. **Set your API key:**
   ```bash
   export API_FOOTBALL_KEY="your_api_key_here"
   ```

2. **Start the worker:**
   ```bash
   ./start_worker.sh start
   ```

3. **Check progress:**
   ```bash
   ./start_worker.sh status
   ```

That's it! The worker handles everything automatically.

## 🔄 **What Happens Next**

### **When API Resets (Tomorrow)**
1. Worker detects available API requests
2. Starts team mapping automatically
3. Shows progress in real-time
4. Saves mappings for future use

### **After Mapping (Same Day or Next)**
1. Worker detects good mapping progress
2. Starts historical import automatically
3. Processes 25 years of data systematically
4. Saves progress to resume if interrupted

### **After Setup (Ongoing)**
1. Worker switches to live update mode
2. Updates fixtures daily at 6 AM UTC
3. Updates matches every 5 minutes
4. Uses only ~300 API requests per day

## 🎉 **Benefits**

- ✅ **One command** handles everything
- ✅ **Intelligent decisions** based on current state
- ✅ **Persistent state** - never loses progress
- ✅ **Auto-restart** if crashes
- ✅ **API limit aware** - never exceeds limits
- ✅ **Background ready** - perfect for servers
- ✅ **Comprehensive logging** - easy to monitor

Your background worker is now ready to handle the complete Top 250 teams workflow with a single command!