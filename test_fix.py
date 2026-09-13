import os
os.environ['VERCEL'] = '1'
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test /api/books/categories
resp = client.get('/api/books/categories')
print(f'GET /api/books/categories: {resp.status_code}')
if resp.status_code != 200:
    print(f'  Error: {resp.text[:200]}')
else:
    print(f'  ✅ OK, returned {len(resp.json())} categories')

# Test /api/books
resp = client.get('/api/books')
print(f'GET /api/books: {resp.status_code}')
if resp.status_code != 200:
    print(f'  Error: {resp.text[:300]}')
else:
    books = resp.json()
    print(f'  ✅ OK, returned {len(books)} books')
    if books:
        title = books[0]['title'][:50]
        print(f'  Sample: {title}')

# Test /api/books/recommendations
resp = client.get('/api/books/recommendations')
print(f'GET /api/books/recommendations: {resp.status_code}')
if resp.status_code != 200:
    print(f'  Error: {resp.text[:200]}')
else:
    print(f'  ✅ OK, returned {len(resp.json())} recommendations')
