import requests
import time
import json

# URL base de tu API
BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint, description):
    """Probar un endpoint y mostrar resultado"""
    try:
        print(f"🔍 Testing {description}...")
        response = requests.get(f"{BASE_URL}{endpoint}")
        
        if response.status_code == 200:
            print(f"✅ {description} - Status: {response.status_code}")
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
        else:
            print(f"❌ {description} - Status: {response.status_code}")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error testing {description}: {e}")
        return False

def generate_load():
    """Generar múltiples requests para testing"""
    print("🚀 Iniciando pruebas de carga...")
    
    endpoints = [
        ("/", "Root Endpoint"),
        ("/health", "Health Check"),
        ("/catalog", "Catalog Data"),
    ]
    
    # Ejecutar cada endpoint múltiples veces
    for round_num in range(1, 21):  # 20 rondas
        print(f"\n🔄 Ronda {round_num}/21")
        
        for endpoint, description in endpoints:
            success = test_endpoint(endpoint, f"{description} (Round {round_num})")
            if success:
                time.sleep(0.5)  # Esperar medio segundo entre requests
            else:
                print(f"⚠️ Saltando endpoint {endpoint} por error")
                
        print(f"✅ Ronda {round_num} completada")
        time.sleep(2)  # Esperar 2 segundos entre rondas
    
    print("\n🎯 Pruebas completadas!")
    print("📊 Ve a Azure Portal → Application Insights → Logs")
    print("⏰ Espera 2-3 minutos y ejecuta esta query:")
    print("""
    requests
    | where timestamp > ago(10m)
    | order by timestamp desc
    | project timestamp, name, url, resultCode, duration
    """)

if __name__ == "__main__":
    print("🧪 Load Test para Steam API")
    print("📡 Asegúrate de que tu API esté corriendo en http://localhost:8000")
    
    # Verificar que la API esté activa
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ API está activa, iniciando pruebas...")
            generate_load()
        else:
            print(f"❌ API no responde correctamente (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ No se puede conectar a la API: {e}")
        print("   Verifica que esté corriendo con: python simple_test.py")