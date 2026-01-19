import requests
from bs4 import BeautifulSoup

def test_url(site, issuedby):
    url = f"https://forecast.weather.gov/product.php?site={site}&issuedby={issuedby}&product=CLI&format=txt&version=1&glossary=0"
    print(f"Testing: {url}")
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            print("Success (200)")
            # Peek at content
            soup = BeautifulSoup(r.content, "html.parser")
            pre_tags = soup.find_all("pre")
            found = False
            for pre in pre_tags:
                if pre.text and "PRECIPITATION (IN)" in pre.text:
                    print("Found PRECIPITATION section.")
                    # Print first few lines of precip
                    lines = pre.text.split('\n')
                    for line in lines:
                        if "MONTH TO DATE" in line:
                            print(f"Line match: {line.strip()}")
                            found = True
                    break
            if not found:
                print("PRECIPITATION section NOT found.")
        else:
            print(f"Failed: {r.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 20)

if __name__ == "__main__":
    # Test Current Config
    print("Test 1: Current Config (SEW/SEW)")
    test_url("SEW", "SEW")
    
    # Test User Suggestion (NWS/SEA)
    print("Test 2: User Config (NWS/SEA)")
    test_url("NWS", "SEA")
    
    # Test Hybrid (SEW/SEA) - Often site matches WFO
    print("Test 3: Hybrid (SEW/SEA)")
    test_url("SEW", "SEA")
