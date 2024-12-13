import os
import requests
from dotenv import load_dotenv
from datetime import datetime

def test_telegram_connection():
    """Test della connessione al bot Telegram dopo la correzione del formato"""
    
    # Ricarica le variabili d'ambiente
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ Variabili d'ambiente non trovate")
        print(f"Token presente: {'✓' if token else '✗'}")
        print(f"Chat ID presente: {'✓' if chat_id else '✗'}")
        return False
    
    base_url = f'https://api.telegram.org/bot{token}'
    
    try:
        # 1. Test connessione base
        print("\n1. Test connessione base al bot...")
        me_response = requests.get(f'{base_url}/getMe')
        print(f"Status: {me_response.status_code}")
        if me_response.status_code == 200:
            bot_info = me_response.json()
            print(f"✓ Bot trovato: @{bot_info['result']['username']}")
        else:
            print(f"✗ Errore: {me_response.text}")
            return False
        
        # 2. Test invio messaggio
        print("\n2. Test invio messaggio...")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test_message = f"""🔄 Test Connessione Bot
        
⏰ Timestamp: {current_time}
🆔 Chat ID: {chat_id}
        
Se ricevi questo messaggio, la connessione è attiva."""
        
        msg_response = requests.post(
            f'{base_url}/sendMessage',
            json={
                'chat_id': chat_id,
                'text': test_message,
                'parse_mode': 'HTML'
            }
        )
        
        print(f"Status invio: {msg_response.status_code}")
        if msg_response.status_code == 200:
            print("✓ Messaggio inviato con successo")
            return True
        else:
            print(f"✗ Errore invio: {msg_response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Errore durante il test: {str(e)}")
        return False

if __name__ == '__main__':
    print("=== Test Connessione Bot Telegram ===")
    success = test_telegram_connection()
    print(f"\nTest completato: {'✓ Connessione attiva' if success else '✗ Verificare errori sopra'}")