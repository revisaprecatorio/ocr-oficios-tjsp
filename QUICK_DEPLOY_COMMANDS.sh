#!/bin/bash
# ============================================================================
# QUICK DEPLOY v2.4.0 TO VPS
# ============================================================================
# Run these commands on the VPS to deploy the legal terms detection feature
# ============================================================================

echo "============================================================"
echo "🚀 DEPLOYING v2.4.0 TO VPS"
echo "============================================================"
echo ""

# Step 1: Navigate to project
echo "📁 Step 1: Navigating to project directory..."
cd /root/3_OCR || { echo "❌ Project directory not found!"; exit 1; }
echo "✅ Current directory: $(pwd)"
echo ""

# Step 2: Backup current code (optional)
echo "💾 Step 2: Creating backup..."
timestamp=$(date +%Y%m%d_%H%M%S)
cp -r 1_parsing_PDF/app "1_parsing_PDF/app.backup.$timestamp"
cp -r 3_streamlit/app "3_streamlit/app.backup.$timestamp"
echo "✅ Backup created: app.backup.$timestamp"
echo ""

# Step 3: Pull latest code
echo "📥 Step 3: Pulling latest code from GitHub..."
git stash  # Stash any local changes
git pull origin main
echo ""

# Step 4: Verify the update
echo "🔍 Step 4: Verifying update..."
git log -1 --oneline
echo ""

# Step 5: Check new files
echo "📋 Step 5: Checking new files..."
if [ -f "1_parsing_PDF/app/detector_termos_juridicos.py" ]; then
    echo "✅ detector_termos_juridicos.py found"
else
    echo "❌ detector_termos_juridicos.py NOT found!"
fi

if [ -f "IMPLEMENTATION_SUCCESS_v2.4.0.md" ]; then
    echo "✅ Documentation found"
else
    echo "❌ Documentation NOT found!"
fi
echo ""

# Step 6: Verify database (data already populated)
echo "🗄️  Step 6: Verifying database..."
PGPASSWORD="BetaAgent2024SecureDB" psql -h 72.60.62.124 -p 5432 -U admin -d n8n -c "
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN preferencial = TRUE THEN 1 END) as preferencial,
    COUNT(CASE WHEN habilitacao_herdeiros = TRUE THEN 1 END) as habilitacao,
    COUNT(CASE WHEN cessao_credito = TRUE THEN 1 END) as cessao
FROM esaj_detalhe_processos;
"
echo ""

# Step 7: Restart Streamlit
echo "🔄 Step 7: Restarting Streamlit..."
echo "   Detecting Streamlit process manager..."

if systemctl is-active --quiet streamlit; then
    echo "   Using systemd..."
    sudo systemctl restart streamlit
    sleep 2
    sudo systemctl status streamlit --no-pager
elif command -v pm2 &> /dev/null; then
    echo "   Using PM2..."
    pm2 restart streamlit
    sleep 2
    pm2 list | grep streamlit
elif docker ps | grep -q streamlit; then
    echo "   Using Docker..."
    docker-compose restart streamlit
    sleep 2
    docker-compose ps streamlit
else
    echo "   ⚠️  Manual restart needed!"
    echo "   Run: pkill -f 'streamlit run' && cd 3_streamlit && nohup streamlit run app/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 &"
fi
echo ""

# Step 8: Verify Streamlit is running
echo "🌐 Step 8: Verifying Streamlit..."
sleep 3
if netstat -tulpn 2>/dev/null | grep -q 8501 || ss -tulpn 2>/dev/null | grep -q 8501; then
    echo "✅ Streamlit is running on port 8501"
else
    echo "❌ Streamlit is NOT running on port 8501!"
fi
echo ""

# Step 9: Test HTTP response
echo "🧪 Step 9: Testing HTTP response..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8501 | grep -q 200; then
    echo "✅ Streamlit is responding (HTTP 200)"
else
    echo "⚠️  Streamlit may not be fully ready yet"
fi
echo ""

echo "============================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "============================================================"
echo ""
echo "🎯 Next steps:"
echo "   1. Open browser: http://72.60.62.124:8501"
echo "   2. Verify filters appear in sidebar"
echo "   3. Check statistics cards (should show: 33, 42, 19)"
echo "   4. Test filters and chart"
echo ""
echo "📚 Documentation:"
echo "   - DEPLOY_v2.4.0_TO_VPS.md"
echo "   - IMPLEMENTATION_SUCCESS_v2.4.0.md"
echo ""
echo "============================================================"
