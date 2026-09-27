#!/usr/bin/env python3
"""
tools/web_reader.py - Extractor y limpiador de texto completo de páginas web.
Permite a la célula madre leer artículos, papers y guías clínicas completas.
"""
import sys
import json
import re
import urllib.request
import urllib.parse
from html.parser import HTMLParser

class SimpleHTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'header', 'footer', 'nav', 'noscript'):
            self.skip = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'header', 'footer', 'nav', 'noscript'):
            self.skip = False

    def handle_data(self, data):
        if not self.skip:
            text = data.strip()
            if text:
                self.result.append(text)

    def get_text(self):
        return " ".join(self.result)

def fetch_url(url: str, max_chars: int = 12000) -> dict:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get('Content-Type', '')
            raw_data = resp.read()
            html = raw_data.decode('utf-8', errors='replace')
            
            # Extraer título
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else "Sin título"
            
            # Limpiar HTML
            parser = SimpleHTMLTextExtractor()
            parser.feed(html)
            text = parser.get_text()
            text = re.sub(r'\s+', ' ', text)
            
            return {
                "url": url,
                "title": title,
                "text": text[:max_chars],
                "total_chars": len(text),
                "truncated": len(text) > max_chars,
                "success": True
            }
    except Exception as e:
        return {"url": url, "error": str(e), "success": False}

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Uso: web_reader.py <URL> [max_caracteres]"}))
        sys.exit(1)
        
    url = sys.argv[1]
    max_c = int(sys.argv[2]) if len(sys.argv) > 2 else 12000
    res = fetch_url(url, max_chars=max_c)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
