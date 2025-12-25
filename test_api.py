"""Script de test pour GexBot API"""
import requests
from config import API_KEY, BASE_URL

def test_endpoint(ticker, endpoint_type):
    """Test d'un endpoint"""
    endpoints = {
        'chain': f"{BASE_URL}/{ticker}/classic/chain?key={API_KEY}",
        'major': f"{BASE_URL}/{ticker}/classic/major?key={API_KEY}",
        'maxchange': f"{BASE_URL}/{ticker}/classic/maxchange?key={API_KEY}"
    }
    
    url = endpoints[endpoint_type]
    print(f"\n📡 Test {ticker} - {endpoint_type}")
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        print(f"   ✅ Status: {response.status_code}")
        
        if endpoint_type == 'chain' and 'strikes' in data:
            print(f"   📈 Strikes: {len(data['strikes'])}")
            print(f"   💰 Spot: {data.get('spot', 'N/A')}")
            
        elif endpoint_type == 'major':
            print(f"   🎯 Zero Gamma: {data.get('zero_gamma', 'N/A')}")
            print(f"   ⬆️  Support: {data.get('mpos_vol', 'N/A')}")
            print(f"   ⬇️  Resistance: {data.get('mneg_vol', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False

def main():
    print("=" * 60)
    print("🧪 TEST API GEXBOT")
    print("=" * 60)
    
    if not API_KEY:
        print("❌ GEXBOT_API_KEY non définie")
        return
    
    print(f"✅ Clé API: {API_KEY[:10]}...")
    
    # Tests
    tests = [
        ('SPX', 'chain'),
        ('SPX', 'major'),
        ('SPX', 'maxchange'),
        ('NDX', 'chain'),
        ('NDX', 'major'),
        ('NDX', 'maxchange')
    ]
    
    results = []
    for ticker, endpoint in tests:
        result = test_endpoint(ticker, endpoint)
        results.append((f"{ticker} {endpoint}", result))
    
    # Résumé
    print("\n" + "=" * 60)
    print("📋 RÉSUMÉ")
    print("=" * 60)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    passed = sum(1 for _, r in results if r)
    print(f"\n🎯 {passed}/{len(results)} tests réussis")
    
    if passed == len(results):
        print("\n✅ Parfait ! Lancez: python update_gex.py")

if __name__ == '__main__':
    main()
