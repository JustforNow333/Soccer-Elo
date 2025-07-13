#!/bin/bash

# Top 250 Teams Background Worker Launcher
# This script ensures the worker runs continuously with proper error handling

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
WORKER_SCRIPT="top_250_worker.py"
LOG_FILE="worker.log"
PID_FILE="worker.pid"
MAX_RETRIES=5
RETRY_DELAY=60  # seconds

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# Check if worker is already running
check_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # Running
        else
            rm -f "$PID_FILE"
            return 1  # Not running
        fi
    fi
    return 1  # Not running
}

# Stop the worker
stop_worker() {
    log "Stopping worker..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            
            # Wait for graceful shutdown
            for i in {1..30}; do
                if ! ps -p "$PID" > /dev/null 2>&1; then
                    log_success "Worker stopped gracefully"
                    break
                fi
                sleep 1
            done
            
            # Force kill if still running
            if ps -p "$PID" > /dev/null 2>&1; then
                log_warning "Force killing worker..."
                kill -9 "$PID"
            fi
        fi
        rm -f "$PID_FILE"
    fi
}

# Start the worker
start_worker() {
    log "Starting Top 250 Teams worker..."
    
    # Check if already running
    if check_running; then
        log_warning "Worker is already running (PID: $(cat "$PID_FILE"))"
        return 0
    fi
    
    # Check Python environment
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found"
        return 1
    fi
    
    # Check if worker script exists
    if [ ! -f "$WORKER_SCRIPT" ]; then
        log_error "Worker script not found: $WORKER_SCRIPT"
        return 1
    fi
    
    # Check API key
    if [ -z "$API_FOOTBALL_KEY" ]; then
        log_error "API_FOOTBALL_KEY environment variable not set"
        return 1
    fi
    
    # Start the worker in the background with optimized single-day import
    nohup python3 "$WORKER_SCRIPT" --single-day >> "$LOG_FILE" 2>&1 &
    WORKER_PID=$!
    
    # Save PID
    echo "$WORKER_PID" > "$PID_FILE"
    
    # Give it a moment to start
    sleep 5
    
    # Check if it's still running
    if ps -p "$WORKER_PID" > /dev/null 2>&1; then
        log_success "Worker started successfully (PID: $WORKER_PID)"
        return 0
    else
        log_error "Worker failed to start"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Restart the worker
restart_worker() {
    log "Restarting worker..."
    stop_worker
    sleep 2
    start_worker
}

# Show worker status
show_status() {
    echo -e "${BLUE}=== Top 250 Teams Worker Status ===${NC}"
    
    if check_running; then
        PID=$(cat "$PID_FILE")
        echo -e "${GREEN}✅ Worker is running (PID: $PID)${NC}"
        
        # Show process info
        if command -v ps &> /dev/null; then
            echo -e "${BLUE}Process info:${NC}"
            ps -p "$PID" -o pid,ppid,etime,cmd 2>/dev/null || echo "Could not get process info"
        fi
    else
        echo -e "${RED}❌ Worker is not running${NC}"
    fi
    
    # Show recent logs
    echo -e "\n${BLUE}Recent logs:${NC}"
    if [ -f "$LOG_FILE" ]; then
        tail -10 "$LOG_FILE"
    else
        echo "No log file found"
    fi
    
    # Show worker status
    echo -e "\n${BLUE}Worker internal status:${NC}"
    python3 "$WORKER_SCRIPT" --status 2>/dev/null || echo "Could not get worker status"
}

# Monitor the worker and restart if it crashes
monitor_worker() {
    log "Starting worker monitor..."
    
    retries=0
    
    while true; do
        if ! check_running; then
            log_warning "Worker not running, attempting restart..."
            
            if start_worker; then
                log_success "Worker restarted successfully"
                retries=0
            else
                retries=$((retries + 1))
                log_error "Worker restart failed (attempt $retries/$MAX_RETRIES)"
                
                if [ $retries -ge $MAX_RETRIES ]; then
                    log_error "Max retries reached, giving up"
                    exit 1
                fi
                
                log "Waiting ${RETRY_DELAY} seconds before retry..."
                sleep $RETRY_DELAY
            fi
        else
            # Worker is running, check again in 60 seconds
            sleep 60
        fi
    done
}

# Main script logic
case "${1:-start}" in
    start)
        start_worker
        ;;
    stop)
        stop_worker
        ;;
    restart)
        restart_worker
        ;;
    status)
        show_status
        ;;
    monitor)
        monitor_worker
        ;;
    logs)
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            echo "No log file found"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|monitor|logs}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the worker"
        echo "  stop    - Stop the worker"
        echo "  restart - Restart the worker"
        echo "  status  - Show worker status"
        echo "  monitor - Monitor worker and restart if it crashes"
        echo "  logs    - Show live logs"
        echo ""
        echo "Examples:"
        echo "  $0 start     # Start worker once"
        echo "  $0 monitor   # Start worker with auto-restart"
        echo "  $0 status    # Check if worker is running"
        exit 1
        ;;
esac