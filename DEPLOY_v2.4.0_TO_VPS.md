# 🚀 Deploy v2.4.0 to VPS - Legal Terms Detection

**Date:** November 10, 2025  
**Version:** 2.4.0  
**Status:** Ready to deploy

---

## 📋 Pre-Deployment Checklist

- [x] Code committed to GitHub
- [x] All tests passing locally
- [x] Database schema updated on VPS
- [x] Data validated in VPS database
- [x] Documentation complete
- [ ] VPS code updated (pending)
- [ ] Streamlit restarted on VPS (pending)

---

## 🔧 Deployment Steps

### **Step 1: SSH into VPS**

```bash
ssh root@srv987902.hstgr.cloud
```

**Password:** (use your SSH key or password)

---

### **Step 2: Navigate to Project Directory**

```bash
cd /root/3_OCR
```

**Verify current location:**
```bash
pwd
# Should output: /root/3_OCR
```

---

### **Step 3: Backup Current Version (Optional but Recommended)**

```bash
# Create backup of current code
cp -r 1_parsing_PDF/app 1_parsing_PDF/app.backup.$(date +%Y%m%d_%H%M%S)
cp -r 2_ingestao/scripts 2_ingestao/scripts.backup.$(date +%Y%m%d_%H%M%S)
cp -r 3_streamlit/app 3_streamlit/app.backup.$(date +%Y%m%d_%H%M%S)

echo "✅ Backup created"
```

---

### **Step 4: Pull Latest Code from GitHub**

```bash
# Stash any local changes (if any)
git stash

# Pull latest code
git pull origin main

# Verify the update
git log -1 --oneline
# Should show: "feat: Add legal terms detection v2.4.0"
```

**Expected output:**
```
Updating b86c418..7865278
Fast-forward
 1_parsing_PDF/app/detector_termos_juridicos.py | 163 ++++++++++++++++
 1_parsing_PDF/app/processador.py               |  45 ++++-
 1_parsing_PDF/app/schemas.py                   |   9 +
 2_ingestao/scripts/ingest_json.py              |  18 +-
 2_ingestao/sql/01_create_table.sql             |   6 +
 3_streamlit/app/streamlit_app.py               | 120 +++++++++++-
 ...
 14 files changed, 2191 insertions(+), 9 deletions(-)
```

---

### **Step 5: Verify New Files**

```bash
# Check if detector was created
ls -lh 1_parsing_PDF/app/detector_termos_juridicos.py

# Check documentation
ls -lh *.md | grep -E "(PLANO|RESULTADO|PHASE6|IMPLEMENTATION)"

# Verify Streamlit updates
grep -n "preferencial\|habilitacao_herdeiros\|cessao_credito" 3_streamlit/app/streamlit_app.py | head -5
```

---

### **Step 6: Verify Database Schema (Already Done)**

The database already has the columns (we updated it earlier). Let's verify:

```bash
PGPASSWORD="BetaAgent2024SecureDB" psql -h 72.60.62.124 -p 5432 -U admin -d n8n -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'esaj_detalhe_processos' 
  AND column_name IN ('preferencial', 'habilitacao_herdeiros', 'cessao_credito')
ORDER BY column_name;
"
```

**Expected output:**
```
      column_name      | data_type 
-----------------------+-----------
 cessao_credito        | boolean
 habilitacao_herdeiros | boolean
 preferencial          | boolean
(3 rows)
```

---

### **Step 7: Verify Data (Already Populated)**

The data is already in the database (we ingested it earlier). Let's verify:

```bash
PGPASSWORD="BetaAgent2024SecureDB" psql -h 72.60.62.124 -p 5432 -U admin -d n8n -c "
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN preferencial = TRUE THEN 1 END) as preferencial,
    COUNT(CASE WHEN habilitacao_herdeiros = TRUE THEN 1 END) as habilitacao,
    COUNT(CASE WHEN cessao_credito = TRUE THEN 1 END) as cessao
FROM esaj_detalhe_processos;
"
```

**Expected output:**
```
 total | preferencial | habilitacao | cessao 
-------+--------------+-------------+--------
    52 |           33 |          42 |     19
(1 row)
```

✅ If you see these numbers, data is already populated!

---

### **Step 8: Restart Streamlit Service**

Check how Streamlit is running on the VPS:

```bash
# Option A: If using systemd
sudo systemctl status streamlit
sudo systemctl restart streamlit
sudo systemctl status streamlit

# Option B: If using PM2
pm2 list
pm2 restart streamlit
pm2 logs streamlit --lines 20

# Option C: If using Docker
docker ps | grep streamlit
docker-compose restart streamlit
docker-compose logs streamlit --tail 20

# Option D: If running manually
pkill -f "streamlit run"
cd 3_streamlit
nohup streamlit run app/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 > logs/streamlit.log 2>&1 &
```

---

### **Step 9: Verify Streamlit is Running**

```bash
# Check if port 8501 is listening
netstat -tulpn | grep 8501

# Or using ss
ss -tulpn | grep 8501

# Test HTTP response
curl -I http://localhost:8501
# Should return: HTTP/1.1 200 OK
```

---

### **Step 10: Test from Browser**

Open your browser and go to:

**Production URL:** `http://72.60.62.124:8501`

**Verify:**
- [ ] Page loads successfully
- [ ] Sidebar shows "📜 Termos Jurídicos" section
- [ ] Statistics cards show term counts (33, 42, 19)
- [ ] Filters work correctly
- [ ] Chart appears in "📊 Gráficos" tab
- [ ] Data table shows all columns

---

## 🧪 Post-Deployment Testing

### **Test 1: Filter by Preferência**
1. Sidebar → "⭐ Preferência" → Select "Com Preferência"
2. Verify: Table shows only 33 processes
3. Verify: Statistics update accordingly

### **Test 2: Filter by Habilitação**
1. Sidebar → "👨‍👩‍👧‍👦 Habilitação de Herdeiros" → Select "Com Habilitação"
2. Verify: Table shows only 42 processes
3. Verify: Statistics update accordingly

### **Test 3: Filter by Cessão**
1. Sidebar → "📄 Cessão de Crédito" → Select "Com Cessão"
2. Verify: Table shows only 19 processes
3. Verify: Statistics update accordingly

### **Test 4: Multiple Filters**
1. Select "Com Preferência" + "Com Habilitação"
2. Verify: Only processes with BOTH terms appear
3. Verify: Statistics are correct

### **Test 5: Chart Visualization**
1. Go to "📊 Gráficos" tab
2. Scroll to "Distribuição de Termos Jurídicos"
3. Verify: Horizontal bar chart appears
4. Verify: Shows 3 bars with correct values

### **Test 6: Export Data**
1. Apply a filter (e.g., "Com Preferência")
2. Click "📥 Download CSV"
3. Verify: CSV contains filtered data
4. Verify: CSV includes term columns

---

## 🔍 Troubleshooting

### **Issue: Streamlit not showing new filters**

**Cause:** Browser cache or Streamlit cache

**Solution:**
```bash
# On VPS: Clear Streamlit cache
rm -rf ~/.streamlit/cache/

# Restart Streamlit
sudo systemctl restart streamlit  # or pm2 restart streamlit

# On browser: Hard refresh
# Chrome/Firefox: Ctrl+Shift+R (Cmd+Shift+R on Mac)
```

---

### **Issue: Statistics showing 0 for all terms**

**Cause:** Database not updated or connection issue

**Solution:**
```bash
# Verify database connection
PGPASSWORD="BetaAgent2024SecureDB" psql -h 72.60.62.124 -p 5432 -U admin -d n8n -c "
SELECT COUNT(*) FROM esaj_detalhe_processos WHERE preferencial = TRUE;
"

# If returns 0, data needs to be re-ingested
# Contact admin to re-run ingestion
```

---

### **Issue: "Column does not exist" error**

**Cause:** Database schema not updated

**Solution:**
```bash
# Add missing columns
PGPASSWORD="BetaAgent2024SecureDB" psql -h 72.60.62.124 -p 5432 -U admin -d n8n -c "
ALTER TABLE esaj_detalhe_processos 
ADD COLUMN IF NOT EXISTS preferencial BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS habilitacao_herdeiros BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS cessao_credito BOOLEAN DEFAULT FALSE;
"
```

---

### **Issue: Streamlit won't start**

**Cause:** Port already in use or Python environment issue

**Solution:**
```bash
# Check what's using port 8501
lsof -i :8501
# Kill the process if needed
kill -9 <PID>

# Verify Python environment
source .venv/bin/activate
python --version  # Should be 3.11+
pip list | grep streamlit  # Should show streamlit

# Reinstall if needed
pip install --upgrade streamlit
```

---

## 📊 Monitoring

### **Check Streamlit Logs**

```bash
# If using systemd
sudo journalctl -u streamlit -f

# If using PM2
pm2 logs streamlit --lines 100

# If using Docker
docker-compose logs streamlit -f

# If manual
tail -f 3_streamlit/logs/streamlit.log
```

### **Check Database Connection**

```bash
# Test connection from VPS
PGPASSWORD="BetaAgent2024SecureDB" psql -h 72.60.62.124 -p 5432 -U admin -d n8n -c "SELECT 1;"
```

---

## ✅ Deployment Verification Checklist

After deployment, verify:

- [ ] Git pull successful (commit 7865278)
- [ ] New files present (detector_termos_juridicos.py)
- [ ] Database schema has 3 new columns
- [ ] Database has data with terms (33, 42, 19)
- [ ] Streamlit service restarted
- [ ] Streamlit accessible at http://72.60.62.124:8501
- [ ] Filters appear in sidebar
- [ ] Statistics cards show correct counts
- [ ] Chart displays in Graphs tab
- [ ] All filters work correctly
- [ ] Export CSV works
- [ ] No errors in logs

---

## 🎉 Success Criteria

Deployment is successful when:

✅ **Code:** Latest version (7865278) running on VPS  
✅ **Database:** 52 processes with legal terms populated  
✅ **UI:** Streamlit showing filters, stats, and chart  
✅ **Functionality:** All filters and exports working  
✅ **Performance:** Page loads in <3 seconds  
✅ **Stability:** No errors in logs for 5 minutes  

---

## 📞 Support

**If you encounter issues:**

1. Check logs first (see Monitoring section)
2. Verify database connection
3. Clear caches (browser + Streamlit)
4. Restart Streamlit service
5. Contact: Persival Balleste

**Documentation:**
- `IMPLEMENTATION_SUCCESS_v2.4.0.md` - Full implementation report
- `PHASE6_STREAMLIT_UPDATE.md` - Streamlit update guide
- `RESULTADO_IMPLEMENTACAO_TERMOS_JURIDICOS.md` - Detailed results

---

**Version:** 2.4.0  
**Deploy Date:** November 10, 2025  
**Deployed By:** Persival Balleste + Cascade AI  
**Status:** ✅ Ready for Production
