import requests
import os
from dotenv import load_dotenv

def test_github_connection():
    load_dotenv()
    
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN non trovato nel file .env")
        return False
    
    repo_url = "https://api.github.com/repos/Rns-lab/trading-assistant-mcp"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(repo_url, headers=headers)
        
        if response.status_code == 200:
            print("Connessione al repository GitHub riuscita!")
            repo_data = response.json()
            print("\nInformazioni repository:")
            print(f"Nome: {repo_data['name']}")
            print(f"Branch default: {repo_data['default_branch']}")
            return True
        else:
            print("Errore nella connessione al repository")
            print(f"Status code: {response.status_code}")
            print(f"Errore: {response.json().get('message')}")
            return False
            
    except Exception as e:
        print("Errore durante il test di connessione:")
        print(str(e))
        return False

def test_github_operations():
    load_dotenv()
    
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN non trovato nel file .env")
        return False
    
    # Add this line to define repo_url
    repo_url = "https://api.github.com/repos/Rns-lab/trading-assistant-mcp"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Test READ - Get repository contents
    contents_url = f"{repo_url}/contents"
    try:
        response = requests.get(contents_url, headers=headers)
        if response.status_code != 200:
            print("Errore nella lettura del repository")
            return False
        print("✓ Lettura repository riuscita")
        
        # Test WRITE - Create a new file
        test_file_path = "test_file.txt"
        create_file_url = f"{repo_url}/contents/{test_file_path}"
        content = "Test file content"
        import base64
        content_bytes = base64.b64encode(content.encode()).decode()
        
        data = {
            "message": "Test commit",
            "content": content_bytes
        }
        
        response = requests.put(create_file_url, json=data, headers=headers)
        if response.status_code not in [200, 201]:
            print("Errore nella creazione del file")
            return False
        print("✓ Creazione file riuscita")
        
        return True
        
    except Exception as e:
        print(f"Errore durante il test delle operazioni: {str(e)}")
        return False

if __name__ == "__main__":
    test_github_connection()
