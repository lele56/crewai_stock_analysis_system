# scripts/debug_api.py
"""调试数据源API原始响应"""
import http.client
import json
import ssl

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://finance.sina.com.cn/',
}

# ── 1. 腾讯K线 API (sh600000) ──
print("=" * 60)
print("1. 腾讯K线 API 多种格式")
print("=" * 60)

# 格式1: 原始格式
print("\n  格式1: /appstock/app/fqkline/get?param=sh600000,day,,,640,qfq")
try:
    conn = http.client.HTTPSConnection('web.ifzq.gtimg.cn', timeout=10, context=_SSL_CTX)
    conn.request('GET', '/appstock/app/fqkline/get?param=sh600000,day,,,640,qfq', headers=_HEADERS)
    resp = conn.getresponse()
    raw = resp.read().decode('utf-8', errors='ignore')
    conn.close()
    data = json.loads(raw)
    print(f"    code: {data.get('code')}, msg: {data.get('msg')}")
    if data.get('code') == 0:
        stock_data = data.get('data', {})
        if isinstance(stock_data, dict):
            for k in stock_data:
                print(f"    key: {k}, type: {type(stock_data[k])}")
                if isinstance(stock_data[k], dict):
                    for kk in stock_data[k]:
                        val = stock_data[k][kk]
                        if isinstance(val, list) and len(val) > 0:
                            print(f"      {kk}: {len(val)}条, 第一条={val[0]}")
                elif isinstance(stock_data[k], list) and len(stock_data[k]) > 0:
                    print(f"      {k}: {len(stock_data[k])}条, 第一条={stock_data[k][0]}")
except Exception as e:
    print(f"    错误: {e}")

# 格式2: 不带日期
print("\n  格式2: /appstock/app/kline/get?param=sh600000,day,2026-06-01,,640,qfq")
try:
    conn = http.client.HTTPSConnection('web.ifzq.gtimg.cn', timeout=10, context=_SSL_CTX)
    conn.request('GET', '/appstock/app/kline/get?param=sh600000,day,2026-06-01,,640,qfq', headers=_HEADERS)
    resp = conn.getresponse()
    raw = resp.read().decode('utf-8', errors='ignore')
    conn.close()
    data = json.loads(raw)
    print(f"    code: {data.get('code')}, msg: {data.get('msg')}")
    if data.get('code') == 0:
        stock_data = data.get('data', {})
        if isinstance(stock_data, dict):
            for k in stock_data:
                if isinstance(stock_data[k], list) and len(stock_data[k]) > 0:
                    print(f"    {k}: {len(stock_data[k])}条, 第一条={stock_data[k][0]}")
except Exception as e:
    print(f"    错误: {e}")

# 格式3: 使用腾讯其他接口
print("\n  格式3: web.sqt.gtimg.cn q=sh600000")
try:
    conn = http.client.HTTPSConnection('web.sqt.gtimg.cn', timeout=10, context=_SSL_CTX)
    conn.request('GET', '/q=sh600000', headers=_HEADERS)
    resp = conn.getresponse()
    raw = resp.read().decode('utf-8', errors='ignore')
    conn.close()
    print(f"    响应: {raw[:300]}")
except Exception as e:
    print(f"    错误: {e}")
print("\n" + "=" * 60)
print("2. 新浪个股行情 (大写 SH600000)")
print("=" * 60)
try:
    conn = http.client.HTTPSConnection('hq.sinajs.cn', timeout=10, context=_SSL_CTX)
    conn.request('GET', '/list=SH600000', headers=_HEADERS)
    resp = conn.getresponse()
    raw = resp.read().decode('gbk', errors='ignore')
    conn.close()
    print(f"  原始响应: {raw[:300]}")
    data = raw.split('"')[1] if '"' in raw else ''
    if data:
        fields = data.split(',')
        print(f"  fields[3] (现价): {fields[3]}")
except Exception as e:
    print(f"  错误: {e}")

# ── 2b. 新浪个股行情 (小写) ──
print("\n" + "=" * 60)
print("2b. 新浪个股行情 (小写 sh600000)")
print("=" * 60)
try:
    conn = http.client.HTTPSConnection('hq.sinajs.cn', timeout=10, context=_SSL_CTX)
    conn.request('GET', '/list=sh600000', headers=_HEADERS)
    resp = conn.getresponse()
    raw = resp.read().decode('gbk', errors='ignore')
    conn.close()
    print(f"  原始响应: {raw[:300]}")
    data = raw.split('"')[1] if '"' in raw else ''
    if data:
        fields = data.split(',')
        print(f"  fields[3] (现价): {fields[3]}")
except Exception as e:
    print(f"  错误: {e}")

# ── 3. 腾讯行情 ──
print("\n" + "=" * 60)
print("3. 腾讯行情 (sh600000)")
print("=" * 60)
try:
    conn = http.client.HTTPSConnection('qt.gtimg.cn', timeout=10, context=_SSL_CTX)
    conn.request('GET', '/q=sh600000', headers=_HEADERS)
    resp = conn.getresponse()
    raw = resp.read().decode('gbk', errors='ignore')
    conn.close()
    data = raw.split('"')[1] if '"' in raw else ''
    if data:
        fields = data.split('~')
        print(f"  字段数: {len(fields)}")
        print(f"  fields[3] (现价): {fields[3]}")
        print(f"  fields[39] (PE): {fields[39]}")
        print(f"  fields[44] (市值): {fields[44]}")
        print(f"  fields[46] (PB): {fields[46]}")
        print(f"  fields[47] (52周高): {fields[47]}")
        print(f"  fields[48] (52周低): {fields[48]}")
    else:
        print(f"  无数据: {raw[:200]}")
except Exception as e:
    print(f"  错误: {e}")

# ── 4. 新浪行业分类 ──
print("\n" + "=" * 60)
print("4. 新浪行业分类 (600000)")
print("=" * 60)
try:
    import re
    conn = http.client.HTTPConnection('vip.stock.finance.sina.com.cn', timeout=10)
    conn.request('GET', '/corp/go.php/vCI_CorpOtherInfo/stockid/600000/menu_num/2.phtml', headers=_HEADERS)
    resp = conn.getresponse()
    html = resp.read().decode('gbk', errors='ignore')
    conn.close()
    m = re.search(r'所属行业板块</td>\s*</tr>\s*<tr>.*?</tr>\s*<tr>\s*<td[^>]*>(.+?)</td>', html, re.DOTALL)
    if m:
        print(f"  行业: {m.group(1).strip()}")
    else:
        print(f"  未匹配到行业，HTML片段: {html[500:1500]}")
except Exception as e:
    print(f"  错误: {e}")