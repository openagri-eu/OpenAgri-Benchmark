#!/bin/bash
# Offline test script for Irrigation Service on RPi
# Usage: bash test_offline.sh

BASE_URL="http://localhost:8005"
EMAIL="test2@test.com"
PASSWORD="Test1234!"
LOCATION_ID=1

CSV_FILE_FOR_NAME="$(dirname "$0")/Irrigation demo data - 9 months.csv"
CSV_NAME=$(basename "$CSV_FILE_FOR_NAME" .csv | tr ' ' '_')
RESULTS_FILE="$(dirname "$0")/results_${CSV_NAME}.txt"
exec > >(tee "$RESULTS_FILE") 2>&1

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; }
skip() { echo "[SKIP] $1"; }
sep()  { echo ""; echo "========================================"; echo "ENDPOINT: $1"; echo "PURPOSE:  $2"; echo "OFFLINE:  $3"; echo "========================================"; }

json_field() { python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('$2',''))" "$1" 2>/dev/null; }
has_error()  { echo "$1" | grep -qi "error\|detail\|exception"; }


# ── AUTH ─────────────────────────────────────────────────────────────────────

sep "POST /api/v1/user/register/" \
    "Create a new user account" \
    "YES"
RES=$(curl -s -X POST "$BASE_URL/api/v1/user/register/" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
echo "RESULT: $RES"


sep "POST /api/v1/login/access-token/" \
    "Authenticate user and retrieve JWT access token" \
    "YES"
RES=$(curl -s -X POST "$BASE_URL/api/v1/login/access-token/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$EMAIL&password=$PASSWORD")
TOKEN=$(json_field "$RES" "access_token")
if [ -z "$TOKEN" ]; then fail "Login failed — no token returned. RESULT: $RES"; exit 1; fi
pass "Token received"
echo "RESULT: token=${TOKEN:0:40}..."


sep "GET /api/v1/user/me/" \
    "Return currently authenticated user's email" \
    "YES"
RES=$(curl -s "$BASE_URL/api/v1/user/me/" \
  -H "Authorization: Bearer $TOKEN")
echo "RESULT: $RES"
has_error "$RES" && fail "User profile fetch failed" || pass "User profile returned"


sep "POST /api/v1/login/logout/" \
    "Invalidate current session (only active when USING_GATEKEEPER=True)" \
    "NO — requires GateKeeper"
skip "Skipped — USING_GATEKEEPER=False in offline mode"


# ── LOCATION ─────────────────────────────────────────────────────────────────

sep "POST /api/v1/location/parcel-wkt/" \
    "Register a field parcel using WKT polygon — fetches elevation from OpenTopoData API" \
    "NO — requires internet for elevation lookup"
RES=$(curl -s -X POST "$BASE_URL/api/v1/location/parcel-wkt/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"coordinates":"POLYGON ((44.8 20.4, 44.9 20.5, 44.9 20.4, 44.8 20.4))"}')
echo "RESULT: $RES"
LOCATION_ID=$(json_field "$RES" "id")
if [ -z "$LOCATION_ID" ]; then
  fail "Location creation failed — elevation API requires internet (expected in offline mode)"
else
  pass "Location created — id=$LOCATION_ID"
fi


sep "GET /api/v1/location/" \
    "List all registered field parcels" \
    "YES"
RES=$(curl -s "$BASE_URL/api/v1/location/" \
  -H "Authorization: Bearer $TOKEN")
echo "RESULT: $RES"
has_error "$RES" && fail "Location list failed" || pass "Location list returned"


if [ -n "$LOCATION_ID" ]; then
  sep "GET /api/v1/location/{location_id}/" \
      "Get a single location by ID" \
      "YES"
  RES=$(curl -s "$BASE_URL/api/v1/location/$LOCATION_ID/" \
    -H "Authorization: Bearer $TOKEN")
  echo "RESULT: $RES"
  has_error "$RES" && fail "Get location failed" || pass "Location returned"

  sep "DELETE /api/v1/location/{location_id}/" \
      "Delete a location by ID" \
      "YES"
  RES=$(curl -s -X DELETE "$BASE_URL/api/v1/location/$LOCATION_ID/" \
    -H "Authorization: Bearer $TOKEN")
  echo "RESULT: $RES"
  has_error "$RES" && fail "Delete location failed" || pass "Location deleted"
else
  skip "GET /api/v1/location/{id}/ — no location available (offline)"
  skip "DELETE /api/v1/location/{id}/ — no location available (offline)"
fi


# ── DATASET ──────────────────────────────────────────────────────────────────

sep "GET /api/v1/dataset/soil-types/" \
    "Return list of available soil types for analysis" \
    "YES"
RES=$(curl -s "$BASE_URL/api/v1/dataset/soil-types/" \
  -H "Authorization: Bearer $TOKEN")
echo "RESULT: $RES"
has_error "$RES" && fail "Soil types failed" || pass "Soil types returned"


sep "GET /api/v1/dataset/weights/" \
    "Return current sensor depth weights used in soil moisture calculation" \
    "YES"
RES=$(curl -s "$BASE_URL/api/v1/dataset/weights/" \
  -H "Authorization: Bearer $TOKEN")
echo "RESULT: $RES"
has_error "$RES" && fail "Get weights failed" || pass "Weights returned"


sep "POST /api/v1/dataset/weights/" \
    "Set sensor depth weights (must sum to 1.0)" \
    "YES"
RES=$(curl -s -X POST "$BASE_URL/api/v1/dataset/weights/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"10":0.3,"20":0.3,"30":0.2,"40":0.1,"50":0.05,"60":0.05}')
echo "RESULT: $RES"
has_error "$RES" && fail "Set weights failed" || pass "Weights updated"


sep "POST /api/v1/dataset/" \
    "Upload time-series soil moisture measurements from CSV file" \
    "YES"
CSV_FILE="$(dirname "$0")/Irrigation demo data - 9 months.csv"
if [ ! -f "$CSV_FILE" ]; then
  fail "CSV file not found: $CSV_FILE"
  exit 1
fi
DATASET_TMP=$(mktemp /tmp/dataset_upload_XXXXXX.json)
python3 -c "
import csv, json, sys
rows = []
with open(sys.argv[1]) as f:
    for r in csv.DictReader(f):
        rows.append({
            'dataset_id': r['dataset_id'],
            'date': r['date'].replace('.000Z', ''),
            'soil_moisture_10': float(r['soil_moisture_10']),
            'soil_moisture_20': float(r['soil_moisture_20']),
            'soil_moisture_30': float(r['soil_moisture_30']),
            'soil_moisture_40': float(r['soil_moisture_40']),
            'soil_moisture_50': float(r['soil_moisture_50']),
            'soil_moisture_60': float(r['soil_moisture_60']),
            'rain': float(r['rain']),
            'temperature': float(r['temperature']),
            'humidity': float(r['humidity']),
        })
print(json.dumps(rows))
" "$CSV_FILE" > "$DATASET_TMP"
echo "Loaded $(python3 -c "import json; print(len(json.load(open('$DATASET_TMP'))))" ) rows from CSV"
RES=$(curl -s -X POST "$BASE_URL/api/v1/dataset/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  --data "@$DATASET_TMP")
rm -f "$DATASET_TMP"
echo "RESULT: $RES"
has_error "$RES" && fail "Dataset upload failed" || pass "Dataset uploaded"


sep "GET /api/v1/dataset/" \
    "List all uploaded dataset IDs" \
    "YES"
RES=$(curl -s "$BASE_URL/api/v1/dataset/" \
  -H "Authorization: Bearer $TOKEN")
echo "RESULT: $RES"
DATASET_ID=$(python3 -c "
import json,sys
d=json.loads(sys.argv[1])
if not d: print(''); exit()
first=d[0]
if isinstance(first, str): print(first)
elif 'dataset_id' in first: print(first['dataset_id'])
elif 'id' in first: print(first['id'])
else: print('')
" "$RES" 2>/dev/null)
if [ -z "$DATASET_ID" ]; then fail "No datasets found — cannot continue"; exit 1; fi
pass "Dataset ID: $DATASET_ID"


sep "GET /api/v1/dataset/{dataset_id}/" \
    "Return raw dataset records for a given dataset ID" \
    "YES"
RES=$(curl -s "$BASE_URL/api/v1/dataset/$DATASET_ID/" \
  -H "Authorization: Bearer $TOKEN")
echo "RESULT: ${RES:0:300}..."
has_error "$RES" && fail "Get dataset failed" || pass "Dataset records returned"


sep "GET /api/v1/dataset/{dataset_id}/analysis/" \
    "Run soil moisture analysis — detects irrigation events, rain events, stress level (slow, may take 1-2 min)" \
    "YES"
RES=$(curl -s "$BASE_URL/api/v1/dataset/$DATASET_ID/analysis/" \
  -H "Authorization: Bearer $TOKEN")
echo "RESULT: $RES"
has_error "$RES" && fail "Analysis failed" || pass "Analysis completed"


sep "GET /api/v1/dataset/{dataset_id}/irrigation-datapoints/" \
    "Return irrigation datapoints — field capacity, wilting point, high-dose irrigation days" \
    "YES"
RES=$(curl -s "$BASE_URL/api/v1/dataset/$DATASET_ID/irrigation-datapoints/" \
  -H "Authorization: Bearer $TOKEN")
echo "RESULT: $RES"
has_error "$RES" && fail "Irrigation datapoints failed" || pass "Irrigation datapoints returned"


sep "DELETE /api/v1/dataset/{dataset_id}/" \
    "Delete a dataset and all its records" \
    "YES"
RES=$(curl -s -X DELETE "$BASE_URL/api/v1/dataset/$DATASET_ID/" \
  -H "Authorization: Bearer $TOKEN")
echo "RESULT: $RES"
has_error "$RES" && fail "Delete dataset failed" || pass "Dataset deleted"


# ── ETO (online only) ────────────────────────────────────────────────────────

sep "GET /api/v1/eto/option-types/" \
    "Return available crop types and KC coefficient stages" \
    "YES"
RES=$(curl -s "$BASE_URL/api/v1/eto/option-types/" \
  -H "Authorization: Bearer $TOKEN")
echo "RESULT: $RES"
has_error "$RES" && fail "ETO option types failed" || pass "ETO option types returned"


sep "GET /api/v1/eto/calculate-coordinates/" \
    "Calculate ETO for given coordinates using external weather API" \
    "NO — requires WeatherService and internet"
RES=$(curl -s "$BASE_URL/api/v1/eto/calculate-coordinates/?latitude=44.8&longitude=20.4&from_date=2024-05-01&to_date=2024-05-05" \
  -H "Authorization: Bearer $TOKEN")
echo "RESULT: $RES"
has_error "$RES" && fail "ETO calculate-coordinates failed (expected in offline mode)" || pass "ETO calculation succeeded"


sep "GET /api/v1/eto/fetch-and-store-eto/" \
    "Fetch ETO from weather API and store in database for a location" \
    "NO — requires WeatherService and internet"
RES=$(curl -s "$BASE_URL/api/v1/eto/fetch-and-store-eto/?location_id=$LOCATION_ID&latitude=44.8&longitude=20.4&from_date=2024-05-01&to_date=2024-05-05" \
  -H "Authorization: Bearer $TOKEN")
echo "RESULT: $RES"
has_error "$RES" && fail "fetch-and-store-eto failed (expected in offline mode)" || pass "fetch-and-store-eto succeeded"


sep "GET /api/v1/eto/get-calculations/{location_id}/from/{from}/to/{to}/" \
    "Return stored ETO calculations from database for a location and date range" \
    "YES (reads from DB, no external call)"
RES=$(curl -s "$BASE_URL/api/v1/eto/get-calculations/$LOCATION_ID/from/2024-05-01/to/2024-05-05/" \
  -H "Authorization: Bearer $TOKEN")
echo "RESULT: $RES"
has_error "$RES" && fail "get-calculations failed" || pass "get-calculations returned"


sep "GET /api/v1/eto/calculate-gk/" \
    "Calculate ETO via GateKeeper parcel ID (GateKeeper proxy)" \
    "NO — requires GateKeeper"
skip "Skipped — USING_GATEKEEPER=False in offline mode"


echo ""
echo "========================================"
echo "ALL TESTS COMPLETE"
echo "========================================"
