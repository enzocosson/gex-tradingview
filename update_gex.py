"""
Script de mise à jour des niveaux GEX pour TradingView
Récupère uniquement les données GexBot (sans IV/volatilité)
"""
import requests
import pandas as pd
from datetime import datetime
import sys
from config import *

def log(message):
    """Logger simple"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")

# ==================== GEXBOT API ====================

def fetch_gex_chain(ticker):
    """Récupère la chaîne GEX complète"""
    url = f"{BASE_URL}/{ticker}/classic/chain?key={API_KEY}"
    try:
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        log(f"✅ {ticker} chain récupérée")
        return response.json()
    except Exception as e:
        log(f"❌ Erreur chain {ticker}: {e}")
        return None

def fetch_gex_major_levels(ticker):
    """Récupère les niveaux majeurs"""
    url = f"{BASE_URL}/{ticker}/classic/major?key={API_KEY}"
    try:
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        log(f"✅ {ticker} major levels récupérés")
        return response.json()
    except Exception as e:
        log(f"❌ Erreur major {ticker}: {e}")
        return None

def fetch_gex_max_change(ticker):
    """Récupère les changements maximum"""
    url = f"{BASE_URL}/{ticker}/classic/maxchange?key={API_KEY}"
    try:
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        log(f"✅ {ticker} max change récupéré")
        return response.json()
    except Exception as e:
        log(f"⚠️  Max change {ticker} non disponible")
        return None

# ==================== CONVERSION ====================

def convert_to_futures(source_ticker, chain, major, maxchange):
    """Convertit SPX/NDX en ES/NQ"""
    
    config = TICKERS[source_ticker]
    ratio = config['ratio']
    target = config['target']
    
    levels = []
    
    # 1. Niveaux majeurs
    if major:
        levels.append({
            'strike': round(major['zero_gamma'] / ratio, 2),
            'gex_vol': 0,
            'gex_oi': 0,
            'type': 'zero_gamma',
            'importance': 10,
            'label': 'Zero Gamma'
        })
        
        levels.append({
            'strike': round(major['mpos_vol'] / ratio, 2),
            'gex_vol': major.get('net_gex_vol', 0),
            'gex_oi': 0,
            'type': 'support',
            'importance': 9,
            'label': 'Major Support (Vol)'
        })
        
        levels.append({
            'strike': round(major['mneg_vol'] / ratio, 2),
            'gex_vol': major.get('net_gex_vol', 0),
            'gex_oi': 0,
            'type': 'resistance',
            'importance': 9,
            'label': 'Major Resistance (Vol)'
        })
        
        levels.append({
            'strike': round(major['mpos_oi'] / ratio, 2),
            'gex_vol': 0,
            'gex_oi': major.get('net_gex_oi', 0),
            'type': 'support',
            'importance': 8,
            'label': 'Major Support (OI)'
        })
        
        levels.append({
            'strike': round(major['mneg_oi'] / ratio, 2),
            'gex_vol': 0,
            'gex_oi': major.get('net_gex_oi', 0),
            'type': 'resistance',
            'importance': 8,
            'label': 'Major Resistance (OI)'
        })
    
    # 2. Top strikes de la chaîne
    if chain and 'strikes' in chain:
        strikes_data = []
        for strike_array in chain['strikes']:
            if len(strike_array) >= 3:
                strike = strike_array[0]
                gex_vol = strike_array[1]
                gex_oi = strike_array[2]
                importance_score = abs(gex_vol) + abs(gex_oi)
                
                strikes_data.append({
                    'strike': strike,
                    'gex_vol': gex_vol,
                    'gex_oi': gex_oi,
                    'importance': importance_score
                })
        
        strikes_data.sort(key=lambda x: x['importance'], reverse=True)
        
        for strike_info in strikes_data[:TOP_STRIKES_COUNT]:
            strike_type = 'support' if strike_info['gex_vol'] > 0 else 'resistance'
            
            levels.append({
                'strike': round(strike_info['strike'] / ratio, 2),
                'gex_vol': strike_info['gex_vol'],
                'gex_oi': strike_info['gex_oi'],
                'type': strike_type,
                'importance': 7,
                'label': strike_type.capitalize()
            })
    
    # 3. Max changes
    if maxchange:
        for interval, key in [('1min', 'one'), ('5min', 'five'), ('15min', 'fifteen')]:
            if key in maxchange and maxchange[key] and len(maxchange[key]) >= 2:
                levels.append({
                    'strike': round(maxchange[key][0] / ratio, 2),
                    'gex_vol': maxchange[key][1],
                    'gex_oi': 0,
                    'type': 'hotspot',
                    'importance': 6,
                    'label': f'Max Change {interval}'
                })
    
    log(f"✅ {target}: {len(levels)} niveaux générés")
    return levels

# ==================== MAIN ====================

def main():
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    log("=" * 60)
    log(f"🚀 DÉMARRAGE MISE À JOUR GEX - {timestamp}")
    log("=" * 60)
    
    if not API_KEY:
        log("❌ ERREUR: GEXBOT_API_KEY non définie")
        sys.exit(1)
    
    # Traiter chaque ticker
    for source_ticker, config in TICKERS.items():
        log(f"\n📊 Traitement {source_ticker} → {config['target']}...")
        
        chain = fetch_gex_chain(source_ticker)
        major = fetch_gex_major_levels(source_ticker)
        maxchange = fetch_gex_max_change(source_ticker)
        
        if chain or major:
            levels = convert_to_futures(source_ticker, chain, major, maxchange)
            
            df = pd.DataFrame(levels)
            df = df.sort_values(['importance', 'strike'], ascending=[False, True])
            
            output_file = OUTPUT_FILES[config['target']]
            df.to_csv(output_file, index=False)
            log(f"✅ Fichier sauvegardé: {output_file}")
            
            if major:
                log(f"   Zero Gamma: {major.get('zero_gamma', 'N/A')}")
                log(f"   Spot: {major.get('spot', 'N/A')}")
        else:
            log(f"❌ Impossible de générer {config['target']}")
    
    # Timestamp
    with open(OUTPUT_FILES['TIMESTAMP'], 'w') as f:
        f.write(timestamp)
    
    log("\n" + "=" * 60)
    log(f"✅ MISE À JOUR TERMINÉE - {timestamp}")
    log("=" * 60)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log(f"❌ ERREUR CRITIQUE: {e}")
        sys.exit(1)
