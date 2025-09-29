import os
import sys
import glob
import uuid
import requests
import tldextract
import subprocess
import traceback
import random
from pathlib import Path
from typing import List, Union, Optional, Tuple
from urllib.parse import urlparse
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup, Tag, Comment
import praw
import difflib
import re
import json
import time
import logging
from logging import Logger
from concurrent.futures import ThreadPoolExecutor, as_completed

import urllib.parse
from time import sleep

from langchain.agents import Tool as LCTool, AgentExecutor, LLMSingleActionAgent, AgentOutputParser
from langchain.prompts import StringPromptTemplate
from langchain.schema import AgentAction, AgentFinish, OutputParserException
from langchain.utilities.tavily_search import TavilySearchAPIWrapper
from langchain.tools.tavily_search import TavilySearchResults
from langchain_openai import AzureChatOpenAI
from langchain.tools.base import BaseTool
from langchain.chains import LLMChain
from langchain_community.callbacks import get_openai_callback
from playwright.sync_api import sync_playwright
from databricks_langchain import ChatDatabricks

try:
    from langchain.callbacks.base import BaseCallbackHandler  # langchain < 0.2
except ImportError:
    from langchain_core.callbacks import BaseCallbackHandler  # langchain >= 0.2
    
import urllib.parse
import idna
import tldextract
import base64
import json
import time
from time import sleep
from typing import List, Dict, Any, Optional
import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from typing import ClassVar

# ========= Env =========
load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_TYPE = os.getenv('OPENAI_API_TYPE')
OPENAI_API_VERSION = os.getenv('OPENAI_API_VERSION')
OPENAI_API_BASE = os.getenv('OPENAI_API_BASE')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

REDDIT_API_FILE = os.getenv('REDDIT_API_FILE')
TAVILY_API_FILE = os.getenv('TAVILY_API_FILE')

LOG_DIR = os.getenv('LOG_DIR', '/app/logs/')
SAVE_CONTENT_DIR = os.getenv('SAVE_CONTENT_DIR', '/app/content/')
SAVE_SCREENSHOT_DIR = os.getenv('SAVE_SCREENSHOT_DIR', '/app/screenshots/')
SAVE_LLM_RESPONSE_DIR = os.getenv('SAVE_LLM_RESPONSE_DIR', '/app/results/')
CUSTOM_CONTENT_DIR = os.getenv('CUSTOM_CONTENT_DIR', '/custom_app/content/')

TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
TWITTER_BEARER_TOKEN_FILE = os.getenv('TWITTER_BEARER_TOKEN_FILE')

REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
TARGET_URL_FILE = os.getenv('TARGET_URL_FILE')
ANALYSIS_LLM_TYPE = os.getenv('ANALYSIS_LLM_TYPE')
DATABRICKS_HOST = os.getenv('DATABRICKS_HOST')
DATABRICKS_TOKEN = os.getenv('DATABRICKS_TOKEN')
DATABRICKS_ENDPOINT = os.getenv('DATABRICKS_ENDPOINT')

current_time = datetime.now().strftime("%Y%m%dT%H%M%S")

# ========= Utility / Key rotation =========
def _read_lines(path: Optional[str]) -> List[str]:
    if not path:
        return []
    p = Path(path)
    if not p.exists() or not p.is_file():
        return []
    lines: List[str] = []
    with p.open('r', encoding='utf-8') as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith('#'):
                continue
            lines.append(s)
    return lines

def load_reddit_pairs(file_path: Optional[str]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for line in _read_lines(file_path):
        parts = [x.strip() for x in line.split(',')]
        if len(parts) >= 2 and parts and parts[1]:
            pairs.append((parts[0], parts[1]))
    return pairs

def load_tavily_keys(file_path: Optional[str]) -> List[str]:
    return _read_lines(file_path)

def load_twitter_keys(file_path: Optional[str], fallback_env_value: Optional[str]) -> List[str]:
    keys = _read_lines(file_path)
    if keys:
        return keys
    return [fallback_env_value] if fallback_env_value else []

def choose_random(seq: List):
    return random.choice(seq) if seq else None

def to_env_str(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        value = value if value else None
    if value is None:
        return None
    return value if isinstance(value, str) else str(value)

def set_and_export_env(key: str, value: Optional[object]):
    s = to_env_str(value)
    if s is None:
        return
    os.environ[key] = s

REDDIT_PAIRS: List[Tuple[str, str]] = load_reddit_pairs(REDDIT_API_FILE)
TAVILY_KEYS: List[str] = load_tavily_keys(TAVILY_API_FILE)
TWITTER_KEYS: List[str] = load_twitter_keys(TWITTER_BEARER_TOKEN_FILE, TWITTER_BEARER_TOKEN)

for path in [LOG_DIR, SAVE_CONTENT_DIR, SAVE_SCREENSHOT_DIR, SAVE_LLM_RESPONSE_DIR]:
    os.makedirs(path, exist_ok=True)

def generate_uuid_from_url(url):
    return uuid.uuid5(uuid.NAMESPACE_URL, url)

def is_similar(new_text, extracted_texts, similarity_threshold=0.8):
    for existing_text in extracted_texts:
        similarity = difflib.SequenceMatcher(None, new_text, existing_text).ratio()
        if similarity > similarity_threshold:
            return True
    return False

def sanitize_one_line(text: Optional[str]) -> str:
    if text is None:
        return ""
    s = str(text)
    s = s.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    s = re.sub(r"[ ]{2,}", " ", s)
    return s.strip()

# ========= Tools =========
class AccessURLTool(BaseTool):
    name: str = "AccessURL"
    description: str = "A tool that accesses a URL to obtain a status code. This tool requires a URL as an argument."
    def _run(self, url):
        browser = None
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                device = {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    "screen": {"width": 1920, "height": 1080},
                    "viewport": {"width": 1280, "height": 720},
                    "device_scale_factor": 1,
                    "is_mobile": False,
                    "has_touch": False,
                    "default_browser_type": "chromium",
                    "extra_http_headers": {"Referer": "https://www.google.com/"},
                }
                context = browser.new_context(**device, ignore_https_errors=True)
                context.set_default_timeout(30000)
                page = context.new_page()
                response = page.goto(url, wait_until='domcontentloaded')
                base_domain = urlparse(url).netloc
                generated_uuid = generate_uuid_from_url(url)
                content_filename = f"{current_time}_{generated_uuid}_{base_domain}.html"
                screenshot_filename = f"{current_time}_{generated_uuid}_{base_domain}.png"
                content = page.content()
                with open(f'{SAVE_CONTENT_DIR}/{content_filename}', 'w', encoding='utf-8') as f:
                    f.write(content)
                page.screenshot(path=f'{SAVE_SCREENSHOT_DIR}/{screenshot_filename}', full_page=True)
                status_code = response.status if response else 0
                ssl_warning = ""
                if "https://" in url:
                    ssl_warning = " (Note: SSL certificate issues detected - potential security risk)"
                return f"Navigating to {url} returned status code {status_code}{ssl_warning}"
        except Exception as e:
            error_msg = str(e)
            if "ERR_CERT_AUTHORITY_INVALID" in error_msg:
                return f"ACCESS_FAILED: {url} - SSL certificate is invalid or untrusted. This is a significant security red flag and often indicates fraudulent websites."
            elif "ERR_NAME_NOT_RESOLVED" in error_msg:
                return f"ACCESS_FAILED: {url} - Domain name resolution failed. The website may not exist or DNS issues present."
            elif "ERR_CONNECTION_REFUSED" in error_msg:
                return f"ACCESS_FAILED: {url} - Server refused connection. The website may be down or blocking access."
            elif "ERR_CONNECTION_TIMED_OUT" in error_msg or "TimeoutError" in error_msg:
                return f"ACCESS_FAILED: {url} - Connection timed out. Server may be overloaded or non-responsive."
            elif "ERR_NETWORK_ACCESS_DENIED" in error_msg:
                return f"ACCESS_FAILED: {url} - Network access denied."
            else:
                return f"ACCESS_FAILED: {url} - Unexpected error: {error_msg}. Website is not accessible."
        finally:
            if browser:
                try:
                    browser.close()
                except:
                    pass
    async def _arun(self, url):
        return self._run(url)

class ExtractTextTool(BaseTool):
    name: str = "ExtractText"
    description: str = "A tool extracts text in the HTML. You must first access the URL using the AccessURL tool before you can use this tool. This tool requires a URL as an argument."
    def _run(self, url):
        unique_uuid = uuid.uuid5(uuid.NAMESPACE_URL, url)
        html_file_list = glob.glob(f'{SAVE_CONTENT_DIR}/*{unique_uuid}*.html')
        if len(html_file_list) > 0:
            html_file = html_file_list[-1]
        else:
            return "You must first access the URL using the AccessURL tool before you can use this tool."

        with open(html_file, 'r', encoding='utf-8') as file:
            html_content = file.read()
        soup = BeautifulSoup(html_content, 'lxml')
        for script_or_style in soup(['script', 'style', 'noscript']):
            script_or_style.decompose()
        for comment in soup.findAll(text=lambda text: isinstance(text, Comment)):
            comment.extract()
        for tag in soup():
            for attribute in ["style", "onclick", "onmouseover", "onmouseout", "onchange", "onload"]:
                if attribute in tag.attrs:
                    del tag[attribute]
        extracted_texts: List[str] = []
        tags_seen: dict = {}
        for tag in soup.find_all(True):
            parent_id = str(id(tag.parent))
            tag_name = tag.name
            unique_key = f"{parent_id}_{tag_name}"
            if tags_seen.get(unique_key, 0) < 3:
                tags_seen[unique_key] = tags_seen.get(unique_key, 0) + 1
                new_text = next(tag.stripped_strings, "")
                if new_text and not is_similar(new_text, extracted_texts):
                    extracted_texts.append(new_text)
        return " ".join(extracted_texts)
    async def _arun(self, url):
        return self._run(url)

class ExtractHyperlinkTool(BaseTool):
    name: str = "ExtractHyperlink"
    description: str = "A tool that extracts a-tag hyperlinks and texts in the HTML. You must access a URL first before using this tool. This tool requires the URL as an argument."
    def _run(self, url):
        unique_uuid = uuid.uuid5(uuid.NAMESPACE_URL, url)
        html_file_list = glob.glob(f'{SAVE_CONTENT_DIR}/*{unique_uuid}*.html')
        if len(html_file_list) > 0:
            html_file = html_file_list[-1]
        else:
            return "You must first access the URL using the AccessURL tool before you can use this tool."

        with open(html_file, 'r', encoding='utf-8') as file:
            html_content = file.read()
        soup = BeautifulSoup(html_content, 'html.parser')
        def find_initial_a_tag_level(tag, current_level=0):
            if tag.name == 'a' and 'http' in tag.get('href', ''):
                return current_level
            child_levels = [find_initial_a_tag_level(child, current_level + 1)
                            for child in tag.children if isinstance(child, Tag)]
            if child_levels:
                return min(child_levels)
            else:
                return sys.maxsize
        initial_level = find_initial_a_tag_level(soup)
        max_level = initial_level + 1
        def extract_a_tags_with_http(tag, current_level=0):
            if current_level > max_level:
                return
            for child in tag.children:
                if isinstance(child, Tag):
                    if child.name == 'a' and 'http' in child.get('href', ''):
                        yield (child.get('href'), child.text.strip())
                    yield from extract_a_tags_with_http(child, current_level + 1)
        return list(extract_a_tags_with_http(soup))
    async def _arun(self, url):
        return self._run(url)

class RetrieveWHOISTool(BaseTool):
    name: str = "RetrieveWHOIS"
    description: str = "A tool to retrieve domain name information from WHOIS. This tool requires a domain name as an argument. If WHOIS fails, it falls back to RDAP."
    def _whois_api(self, registered_domain: str):
        url = f"https://api.whoisproxy.info/whois/{registered_domain}"
        try:
            response = requests.get(url, timeout=20)
            if response.status_code == 200:
                data = response.json()
                return data.get('results', data)
            else:
                return None
        except Exception:
            return None
    def _whois_cli(self, domain_name: str, registered_domain: str):
        try:
            tld = tldextract.extract(domain_name).suffix
            whois_server = f"whois.nic.{tld}"
            result = subprocess.run(
                ['whois', '-h', whois_server, registered_domain],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=20
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
            result2 = subprocess.run(
                ['whois', registered_domain],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=20
            )
            if result2.returncode == 0 and result2.stdout.strip():
                return result2.stdout
            return None
        except Exception:
            return None
    def _rdap_bootstrap_servers(self):
        try:
            resp = requests.get("https://data.iana.org/rdap/dns.json", timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                services = data.get("services", [])
                tld_to_urls = {}
                for entry in services:
                    if not isinstance(entry, list) or len(entry) < 2:
                        continue
                    tlds = entry[0]
                    urls = entry[1]
                    for t in tlds:
                        tld_to_urls[t.lower()] = urls
                return tld_to_urls
        except Exception:
            pass
        return {}
    def _rdap_query(self, domain_name: str):
        ext = tldextract.extract(domain_name)
        tld = (ext.suffix or "").lower()
        if not tld:
            return None
        tld_servers = getattr(self, "_RDAP_TLD_MAP", None)
        if tld_servers is None:
            tld_servers = self._rdap_bootstrap_servers()
            self._RDAP_TLD_MAP = tld_servers
        base_urls = tld_servers.get(tld)
        if not base_urls:
            return None
        for base in base_urls:
            base = base.rstrip('/')
            rdap_url = f"{base}/domain/{domain_name}"
            try:
                r = requests.get(rdap_url, timeout=20, headers={"Accept": "application/rdap+json, application/json"})
                if r.status_code == 200:
                    data = r.json()
                    return self._normalize_rdap(data)
            except Exception:
                continue
        return None
    def _normalize_rdap(self, data: dict):
        out = {}
        out["objectClassName"] = data.get("objectClassName")
        out["handle"] = data.get("handle")
        out["ldhName"] = data.get("ldhName")
        out["unicodeName"] = data.get("unicodeName")
        ns_list = []
        for ns in data.get("nameservers", []) or []:
            ldh = ns.get("ldhName")
            if ldh:
                ns_list.append(ldh)
        if ns_list:
            out["nameservers"] = ns_list
        st = data.get("status")
        if st:
            out["status"] = st
        ev_out = []
        for ev in data.get("events", []) or []:
            ev_out.append({
                "eventAction": ev.get("eventAction"),
                "eventDate": ev.get("eventDate")
            })
        if ev_out:
            out["events"] = ev_out
        registrar = None
        registrant = None
        for ent in data.get("entities", []) or []:
            roles = ent.get("roles", [])
            if "registrar" in roles and not registrar:
                registrar = ent.get("vcardArray", ent.get("handle"))
            if "registrant" in roles and not registrant:
                registrant = ent.get("vcardArray", ent.get("handle"))
        if registrar:
            out["registrar"] = registrar
        if registrant:
            out["registrant"] = registrant
        links = []
        for ln in data.get("links", []) or []:
            href = ln.get("href")
            if href:
                links.append(href)
        if links:
            out["links"] = links
        out["raw_rdap"] = data
        return out
    def _run(self, domain_name):
        paylevel_domain_name = tldextract.extract(domain_name).registered_domain
        api_res = self._whois_api(paylevel_domain_name)
        if api_res:
            return api_res
        cli_res = self._whois_cli(domain_name, paylevel_domain_name)
        if cli_res:
            return cli_res
        rdap_res = self._rdap_query(paylevel_domain_name)
        if rdap_res:
            return rdap_res
        return f"Error: WHOIS and RDAP lookup failed for {paylevel_domain_name}"
    async def _arun(self, domain_name):
        return self._run(domain_name)

class RetrieveCertificateTool(BaseTool):
    name: str = "RetrieveCertificate"
    description: str = "A tool to retrieve certificate information from crt.sh. This tool requires a domain name as an argument. Note that only the latest top 5 results will be retrieved."

    CT_LOGS: ClassVar[List[str]] = [
        "https://ct.googleapis.com/logs/argon2024",
        "https://ct.googleapis.com/logs/xenon2023",
        "https://ct.cloudflare.com/logs/nimbus2023",
        "https://oak.ct.letsencrypt.org/2023",
    ]

    def _normalize_domain(self, domain_name: str) -> str:
        s = (domain_name or "").strip()
        try:
            parsed = urllib.parse.urlparse(s if "://" in s else f"https://{s}")
            host = parsed.hostname or s
        except Exception:
            host = s
        try:
            host = idna.encode(host).decode("ascii")
        except Exception:
            pass
        ext = tldextract.extract(host)
        registered = ext.registered_domain or host
        return registered.lower()

    def _fetch_crtsh_json(self, domain: str, max_attempts: int = 3, timeout: int = 20):
        q = urllib.parse.quote_plus(domain)
        url = f"https://crt.sh/?q={q}&output=json"
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; CertFetcher/1.0)",
            "Accept": "application/json, text/plain;q=0.8, */*;q=0.5",
        }
        backoff = 1.0
        last_err = None
        for _ in range(max_attempts):
            try:
                resp = requests.get(url, headers=headers, timeout=timeout)
            except Exception as e:
                last_err = f"request_error:{str(e)}"
                sleep(backoff); backoff = min(backoff * 2, 8.0)
                continue
            if resp.status_code in (429, 500, 502, 503, 504):
                ra = resp.headers.get("Retry-After")
                try:
                    sleep(float(ra)) if ra else sleep(backoff)
                except Exception:
                    sleep(backoff)
                backoff = min(backoff * 2, 16.0)
                last_err = f"http_{resp.status_code}"
                continue
            if resp.status_code in (401, 403):
                return {"error": f"crt.sh returned {resp.status_code}", "body_snippet": resp.text[:300]}
            if not resp.ok:
                last_err = f"http_{resp.status_code}"
                sleep(backoff); backoff = min(backoff * 2, 16.0)
                continue
            try:
                data = resp.json()
                return {"data": data}
            except Exception:
                return {"error": "invalid_json", "body_snippet": resp.text[:500]}
        return {"error": last_err or "exhausted"}

    def _fetch_ctlog_recent_light(self, domain: str, per_log_scan: int = 1000, batch: int = 256, timeout: int = 12) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for base in self.CT_LOGS:
            try:
                sth_resp = requests.get(f"{base}/ct/v1/get-sth", timeout=timeout)
                if not sth_resp.ok:
                    continue
                sth = sth_resp.json()
                tree_size = sth.get("tree_size")
                if not isinstance(tree_size, int) or tree_size <= 0:
                    continue
                start = max(0, tree_size - per_log_scan)
                end = tree_size - 1
                idx = start
                while idx <= end and len(items) < 10:
                    this_end = min(idx + batch - 1, end)
                    resp = requests.get(f"{base}/ct/v1/get-entries?start={idx}&end={this_end}", timeout=timeout)
                    if not resp.ok:
                        break
                    data = resp.json()
                    entries = data.get("entries", [])
                    for e in entries[:5]:
                        items.append({
                            "ct_log": base,
                            "leaf_input_len": len(e.get("leaf_input", "")),
                            "extra_data_len": len(e.get("extra_data", "")),
                        })
                    idx = this_end + 1
            except Exception:
                continue
        return items

    def _run(self, domain_name):
        domain = self._normalize_domain(domain_name)

        crt = self._fetch_crtsh_json(domain)
        if isinstance(crt, dict) and "data" in crt and isinstance(crt["data"], list) and len(crt["data"]) > 0:
            try:
                seen = set()
                uniq = []
                for c in crt["data"]:
                    key = c.get("id") or c.get("min_cert_id") or c.get("serial_number") or json.dumps(c, sort_keys=True)
                    if key in seen:
                        continue
                    seen.add(key)
                    uniq.append(c)
                return uniq[:5]
            except Exception:
                return (crt.get("data") or [])[:5]

        light = self._fetch_ctlog_recent_light(domain)
        if light:
            return light[:5]

        err = crt.get("error") if isinstance(crt, dict) else "unknown_error"
        snippet = crt.get("body_snippet") if isinstance(crt, dict) else ""
        return f"Error fetching certificates information: {err}. {snippet}"

    async def _arun(self, domain_name):
        return self._run(domain_name)

class RetrieveDNSRecordTool(BaseTool):
    name: str = "RetrieveDNSRecord"
    description: str = "A tool to retrieve dns records using the dig command. This tool requires a domain name as an argument."
    def _run(self, domain_name):
        result = subprocess.run(["dig", "ANY", domain_name, "@8.8.8.8"], stdout=subprocess.PIPE, text=True)
        return result.stdout
    async def _arun(self, domain_name):
        return self._run(domain_name)

class SearchXTwitterTool(BaseTool):
    name: str = "SearchX/Twitter"
    description: str = "A tool to search and retrieve posts containing keywords from X/Twitter. This tool requires a search query as an argument. You cannot take a URL as-is as a search query. Note that only the latest top 10 results will be searched."

    max_results: str = '100'
    tweet_fields: List[str] = ['created_at', 'id', 'lang', 'source', 'text', 'conversation_id', 'entities', 'public_metrics']
    user_fields: List[str] = ['created_at', 'description', 'entities', 'id', 'name', 'profile_image_url', 'public_metrics', 'url', 'username', 'verified']

    def _try_request(self, token: str, search_query: str) -> Union[dict, str]:
        q = urllib.parse.quote_plus(search_query)
        url = (
            f'https://api.twitter.com/2/tweets/search/recent'
            f'?query={q}&max_results={self.max_results}'
            f'&tweet.fields={",".join(self.tweet_fields)}'
            f'&user.fields={",".join(self.user_fields)}'
        )
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (compatible; Bot/1.0; +https://example.org)'
        }

        backoff = 1.0
        for attempt in range(4):
            try:
                response = requests.get(url, headers=headers, timeout=20)
            except Exception as e:
                return f"Error: Twitter request failed - {sanitize_one_line(str(e))}"

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception:
                    return f"Error: Invalid JSON from Twitter API (200) - {sanitize_one_line(response.text)}"

            if response.status_code == 429:
                ra = response.headers.get('retry-after') or response.headers.get('Retry-After')
                if ra:
                    try:
                        sleep(float(ra))
                    except Exception:
                        sleep(backoff)
                else:
                    sleep(backoff)
                backoff = min(backoff * 2, 16.0)
                continue

            if 500 <= response.status_code < 600:
                sleep(backoff)
                backoff = min(backoff * 2, 16.0)
                continue

            if response.status_code in (401, 403):
                return f'Error: Twitter auth/permission issue, status code {response.status_code} - {sanitize_one_line(response.text)}'

            return f'Error: Unable to fetch data, status code {response.status_code} - {sanitize_one_line(response.text)}'

        return 'Error: Twitter request exhausted retries (429/5xx persistent)'

    def _run(self, search_query):
        tokens = TWITTER_KEYS[:] if TWITTER_KEYS else ([TWITTER_BEARER_TOKEN] if TWITTER_BEARER_TOKEN else [])
        tokens = [t for t in tokens if t]
        if not tokens:
            return "Twitter search skipped: no bearer token available"

        last_err = None
        for idx, token in enumerate(tokens):
            set_and_export_env('TWITTER_BEARER_TOKEN', token)
            result = self._try_request(token, search_query)
            if isinstance(result, dict):
                return result
            if isinstance(result, str) and ('401' in result or '403' in result):
                last_err = result
                continue
            last_err = result

        return last_err or "Error: Twitter request failed with all tokens"

    async def _arun(self, domain_name):
        return self._run(domain_name)

class SearchRedditTool(BaseTool):
    name: str = "SearchReddit"
    description: str = "A tool to retrieve posts containing a keyword from Reddit. This tool requires a search query as an argument. You cannot use a URL as-is as a search query. Note that only the top five related posts and the top five associated comments will be retrieved."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._reddit: Optional[praw.Reddit] = None

    def _ensure_client(self):
        pair = choose_random(REDDIT_PAIRS)
        client_id, client_secret = (None, None)
        if pair:
            try:
                client_id = pair[0]
                client_secret = pair[1]
            except Exception:
                client_id, client_secret = (None, None)

        if not client_id:
            client_id = os.getenv('REDDIT_CLIENT_ID')
        if not client_secret:
            client_secret = os.getenv('REDDIT_CLIENT_SECRET')

        set_and_export_env('REDDIT_CLIENT_ID', client_id)
        set_and_export_env('REDDIT_CLIENT_SECRET', client_secret)

        if client_id is None or client_secret is None:
            raise RuntimeError("Reddit API credentials missing")

        self._reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent='script:domain-analyzer:1.0 (by u/your_username)'
        )
        try:
            self._reddit.read_only = True
        except Exception:
            pass

    def _run(self, search_query):
        backoff = 1.0
        for attempt in range(4):
            try:
                if self._reddit is None:
                    self._ensure_client()
            except Exception as e:
                return f"Reddit search skipped: {sanitize_one_line(str(e))}"

            try:
                results = list()
                for submission in self._reddit.subreddit("all").search(search_query, limit=5):
                    dic = {
                        'title': f'{submission.title}',
                        'subreddit': f'{submission.subreddit}',
                        'url': f'{submission.url}',
                        'selftext': f'{submission.selftext}'
                    }

                    comments = list()
                    try:
                        submission.comments.replace_more(limit=0)
                        count = 0
                        for c in submission.comments.list():
                            if count >= 5:
                                break
                            if hasattr(c, 'body'):
                                comments.append(c.body.strip())
                                count += 1
                    except Exception:
                        pass

                    dic['comments'] = comments
                    results.append(dic)

                return results

            except praw.exceptions.RedditAPIException as e:
                msg = sanitize_one_line(str(e))
                if '401' in msg or 'invalid_grant' in msg or 'forbidden' in msg:
                    self._reddit = None
                    sleep(backoff)
                    backoff = min(backoff * 2, 8.0)
                    continue
                return f"Reddit search skipped: {msg}"

            except Exception as e:
                msg = sanitize_one_line(str(e))
                if '401' in msg or 'HTTPError 401' in msg or 'received 401' in msg:
                    self._reddit = None
                    sleep(backoff)
                    backoff = min(backoff * 2, 8.0)
                    continue
                if 'ratelimit' in msg.lower() or 'temporarily unavailable' in msg.lower() or 'timed out' in msg.lower():
                    sleep(backoff)
                    backoff = min(backoff * 2, 8.0)
                    continue
                return f"Reddit search skipped: {msg}"

        return "Reddit search skipped: exhausted retries due to auth/rate-limit issues"

    async def _arun(self, domain_name):
        return self._run(domain_name)
    
class DynamicTavilyTool(BaseTool):
    name: str = "GetSearchResult"
    description: str = "A tool to retrieve search results from a search engine. This tool requires a search query as an argument. You cannot take a URL as-is as a search query."
    def _run(self, query: str):
        key = choose_random(TAVILY_KEYS) or os.getenv('TAVILY_API_KEY')
        set_and_export_env('TAVILY_API_KEY', key)
        api = TavilySearchAPIWrapper()
        tool = TavilySearchResults(api_wrapper=api)
        return tool.run(query)
    async def _arun(self, query: str):
        return self._run(query)

# ========= Prompt / Parser =========
class CustomPromptTemplate(StringPromptTemplate):
    template: str
    tools: List[LCTool]
    def format(self, **kwargs) -> str:
        intermediate_steps = kwargs.pop("intermediate_steps")
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservation: {observation}\nThought: "
        kwargs["agent_scratchpad"] = thoughts
        kwargs["tools"] = "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools])
        kwargs["tool_names"] = ", ".join([tool.name for tool in self.tools])
        return self.template.format(**kwargs)

class CustomOutputParser(AgentOutputParser):
    def __init__(self, url_logger: Optional[Logger] = None):
        super().__init__()
        self._url_logger = url_logger

    def parse(self, llm_output: str) -> Union[AgentAction, AgentFinish]:
        if "Final Answer:" in llm_output:
            return AgentFinish(
                return_values={"output": llm_output.split("Final Answer:")[-1].strip()},
                log=llm_output,
            )

        regex = r"Action\s*\d*\s*:\s*(?P<tool>.+?)\s*\n\s*Action\s*Input\s*\d*\s*:\s*(?P<input>.+)"
        match = re.search(regex, llm_output, re.DOTALL)

        if not match:
            if self._url_logger:
                self._url_logger.error("OUTPUT_PARSING_FAILURE raw LLM output: %s", llm_output)
            raise OutputParserException(
                "Could not parse the output. Please respond EXACTLY with either:\n"
                "1) 'Action: <one of the allowed tools>' + newline + 'Action Input: <input>'\n"
                "OR\n"
                "2) 'Thought: I now know the final answer' + newline + 'Final Answer: <JSON>'"
            )

        action = match.group("tool").strip()
        action_input = match.group("input").strip().strip('"')
        return AgentAction(tool=action, tool_input=action_input, log=llm_output)

# ========= Logging helpers =========
def _truncate(s: object, maxlen: int = 2000) -> str:
    try:
        txt = str(s)
    except Exception:
        txt = repr(s)
    txt = sanitize_one_line(txt)
    return txt if len(txt) <= maxlen else txt[:maxlen] + " ...[truncated]"

def _safe_json(o) -> str:
    try:
        txt = json.dumps(o, ensure_ascii=False)
    except Exception:
        txt = str(o)
    return _truncate(txt, 2000)

def _obs_stringify(obj) -> str:
    try:
        if isinstance(obj, (dict, list, tuple)):
            return json.dumps(obj, ensure_ascii=False)
        return str(obj)
    except Exception:
        return repr(obj)

def _obs_summarize(s: str, maxlen: int = 2000) -> str:
    s = sanitize_one_line(s)
    return s if len(s) <= maxlen else s[:maxlen] + " ...[truncated]"

# ========= UrlScopedCallbackHandler =========
class UrlScopedCallbackHandler(BaseCallbackHandler):
    def __init__(self, logger: Logger, obs_maxlen: int = 2000):
        self.logger = logger
        self._current_tool_name: Optional[str] = None
        self._tool_depth: int = 0
        self._obs_maxlen = obs_maxlen

    def on_chain_start(self, serialized, inputs, **kwargs):
        name = (serialized or {}).get("name") or "chain"
        try:
            self.logger.info("> Chain start: %s | inputs=%s", name, _safe_json(inputs))
        except Exception:
            self.logger.info("> Chain start: %s", name)

    def on_chain_end(self, outputs, **kwargs):
        try:
            self.logger.info("> Chain end: outputs=%s", _safe_json(outputs))
        except Exception:
            self.logger.info("> Chain end")

    def on_chain_error(self, error, **kwargs):
        self.logger.error("> Chain error: %s", _truncate(error))

    def on_llm_start(self, serialized, prompts, **kwargs):
        try:
            for i, p in enumerate(prompts or []):
                self.logger.info("> LLM prompt[%d]: %s", i, _truncate(p))
        except Exception:
            pass

    def on_llm_end(self, response, **kwargs):
        self.logger.info("> LLM end")

    def on_llm_error(self, error, **kwargs):
        self.logger.error("> LLM error: %s", _truncate(error))

    def on_tool_start(self, serialized, input_str, **kwargs):
        self._tool_depth += 1
        self._current_tool_name = (serialized or {}).get("name") or "tool"
        inp = _obs_summarize(_obs_stringify(input_str), maxlen=self._obs_maxlen)
        self.logger.info("> Tool start: %s | input=%s", self._current_tool_name, inp if inp else "(empty)")

    def on_tool_end(self, output, **kwargs):
        out = _obs_summarize(_obs_stringify(output), maxlen=self._obs_maxlen)
        self.logger.info("> Tool end: %s", out if out else "(empty)")
        if self._current_tool_name:
            self.logger.info("Observation(%s): %s", self._current_tool_name, out if out else "(empty)")
        else:
            self.logger.info("Observation: %s", out if out else "(empty)")
        self._tool_depth = max(0, self._tool_depth - 1)
        if self._tool_depth == 0:
            self._current_tool_name = None

    def on_tool_error(self, error, **kwargs):
        err = _truncate(error)
        self.logger.error("> Tool error: %s", err)
        if self._current_tool_name:
            self.logger.info("Observation(%s): %s", self._current_tool_name, f"ERROR: {err}")
        else:
            self.logger.info("Observation: %s", f"ERROR: {err}")
        self._tool_depth = max(0, self._tool_depth - 1)
        if self._tool_depth == 0:
            self._current_tool_name = None

    def on_text(self, text, **kwargs):
        if text is None:
            return
        t = _obs_summarize(str(text), maxlen=self._obs_maxlen)
        if not t:
            return
        if self._tool_depth > 0:
            if self._current_tool_name:
                self.logger.info("Observation(%s): %s", self._current_tool_name, t)
            else:
                self.logger.info("Observation: %s", t)
        self.logger.info("%s", t)

    def on_agent_action(self, action, **kwargs):
        try:
            log = action.log if isinstance(action.log, str) else str(action.log)
            thought_raw = log.split("\nObservation:")[0].split("Action") if log else ""
            thought = sanitize_one_line(thought_raw)
            if thought:
                self.logger.info("Thought: %s", _truncate(thought))
            self.logger.info("Action: %s", getattr(action, "tool", ""))
            self.logger.info("Action Input: %s", _truncate(getattr(action, "tool_input", "")))
        except Exception:
            pass

    def on_agent_observation(self, observation, **kwargs):
        obs = _obs_summarize(_obs_stringify(observation), maxlen=self._obs_maxlen)
        if self._current_tool_name:
            self.logger.info("Observation(%s): %s", self._current_tool_name, obs if obs else "(empty)")
        else:
            self.logger.info("Observation: %s", obs if obs else "(empty)")

    def on_agent_finish(self, finish, **kwargs):
        try:
            self.logger.info("Final Answer: %s", _truncate(getattr(finish, "log", "")))
        except Exception:
            pass

# ========= Tool return logging wrapper =========
class LoggingTool(LCTool):
    def __init__(self, base_tool: LCTool, logger: Logger, obs_maxlen: int = 2000):
        super().__init__(
            name=base_tool.name,
            description=base_tool.description,
            func=base_tool.func,
            coroutine=base_tool.coroutine,
            args_schema=getattr(base_tool, "args_schema", None),
            return_direct=getattr(base_tool, "return_direct", False),
        )
        self._logger = logger
        self._obs_maxlen = obs_maxlen
        self._orig_func = base_tool.func
        self._orig_coro = base_tool.coroutine

        def wrapped_func(*args, **kwargs):
            output = None
            try:
                output = self._orig_func(*args, **kwargs)
                out = _obs_summarize(_obs_stringify(output), maxlen=self._obs_maxlen)
                self._logger.info("Observation(%s): %s", self.name, out if out else "(empty)")
                return output
            except Exception as e:
                err = _truncate(e)
                self._logger.info("Observation(%s): %s", self.name, f"ERROR: {err}")
                raise

        async def wrapped_coro(*args, **kwargs):
            output = None
            try:
                output = await self._orig_coro(*args, **kwargs)
                out = _obs_summarize(_obs_stringify(output), maxlen=self._obs_maxlen)
                self._logger.info("Observation(%s): %s", self.name, out if out else "(empty)")
                return output
            except Exception as e:
                err = _truncate(e)
                self._logger.info("Observation(%s): %s", self.name, f"ERROR: {err}")
                raise

        self.func = wrapped_func
        if self._orig_coro:
            self.coroutine = wrapped_coro

# ========= Logger / AgentExecutor =========
def make_url_logger(filename_base: str) -> Tuple[Logger, logging.Handler]:
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"{filename_base}.log")
    logger = logging.getLogger(f"url_logger:{filename_base}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for h in list(logger.handlers):
        logger.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass
    handler = logging.FileHandler(log_path, mode='a', encoding='utf-8', delay=False)
    fmt = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger, handler

def build_agent_executor(url_logger: Logger):
    template = """
I want you to act as a professional scam website detection expert. You are tasked with analyzing the content of URLs given to you to determine if the URL is a scam website or not. Scam websites have the following characteristics.
1. Unusually low prices and claims of free.
2. Claims to be able to get an amount of money that is generally not possible.
3. Texts that target human psychological weaknesses exist on websites.
4. Information on non-existent companies.
5. Handling different products from common e-commerce websites.
6. Inquiry phone number and email address are not appropriate for business use.
7. Privacy of customer information notation is ambiguous.
8. Payment methods are not common and are unusual.
9. The information listed has not been updated.
10. Pop-up messages and fake error alerts claiming system issues or security threats.
11. Use of celebrity endorsements or fake testimonials without verification.
12. Requires upfront fees or deposits for verification, processing, or withdrawal.
13. Excessive use of urgency tactics with limited-time offers or immediate action requirements.
14. Requests for remote access to devices or installation of suspicious software.
15. Promises of guaranteed returns or risk-free investments with unrealistic percentages.
16. Mimics or spoofs legitimate company names, logos, and website designs.

You can access the following tools to help you answer the question:
{tools}

Please follow the format below when answering the questions:
Question: the question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (You can repeat this Thought/Action/Action Input/Observation N times to derive your answer.)
Thought: I now know the final answer
Final Answer: the final answer to the original question

You are to derive the Final Answer based on no more than ten actions. To do so, you need to analyze efficiently. Be sure to say I now know the final answer when you know the answer.

After the Final Answer is determined, output the analysis results in JSON format according to the following key:
- scam : True or False (result of URL scam determination)
- website_type : Please identify the website's category according to the following rules.
  - The main scam categories are: Fake Online Shopping, Technical Support Scams, Cryptocurrency Scams, Investment Scams.
  - If 'scam' is True, select the most appropriate category from the list above.
  - If 'scam' is False, state the corresponding legitimate category (e.g., "Online Shopping" for "Fake Online Shopping", "Technical Support Service" for "Technical Support Scams").
  - If the website does not fit any of these categories, determine and provide the most suitable category name yourself (e.g., "News Media", "Corporate Blog", "Social Media").
- reason : Please logically state the basis for your decision using the characteristics of the scam website shared.

The current year is 2025. Begin!

Question: {input}
{agent_scratchpad}
"""
    if ANALYSIS_LLM_TYPE and ANALYSIS_LLM_TYPE.startswith('databricks-'):
        if DATABRICKS_HOST and DATABRICKS_TOKEN:
            os.environ["DATABRICKS_HOST"] = to_env_str(DATABRICKS_HOST) or ""
            os.environ["DATABRICKS_TOKEN"] = to_env_str(DATABRICKS_TOKEN) or ""
        if ANALYSIS_LLM_TYPE == 'databricks-custom':
            if not DATABRICKS_ENDPOINT:
                raise ValueError("DATABRICKS_ENDPOINT must be set when using databricks-custom")
            endpoint_name = DATABRICKS_ENDPOINT
        else:
            endpoint_name = ANALYSIS_LLM_TYPE
        llm = ChatDatabricks(endpoint=endpoint_name, temperature=0.1, max_tokens=8192, timeout=300, max_retries=3)
    else:
        if 'Llama-3.3-70B-Instruct'in ANALYSIS_LLM_TYPE:
            llm = AzureChatOpenAI(azure_deployment=ANALYSIS_LLM_TYPE, api_version=OPENAI_API_VERSION, azure_endpoint=OPENAI_API_BASE, timeout=300, max_retries=3, model_kwargs={"max_completion_tokens": 8192})
        else:
            llm = AzureChatOpenAI(azure_deployment=ANALYSIS_LLM_TYPE, api_version=OPENAI_API_VERSION, azure_endpoint=OPENAI_API_BASE, timeout=300, max_retries=3)

    dynamic_tavily_tool = DynamicTavilyTool()
    whois_tool = RetrieveWHOISTool()
    access_tool = AccessURLTool()
    text_tool = ExtractTextTool()
    hyperlink_tool = ExtractHyperlinkTool()
    certificate_tool = RetrieveCertificateTool()
    dnsrecord_tool = RetrieveDNSRecordTool()
    xsearch_tool = SearchXTwitterTool()
    redditsearch_tool = SearchRedditTool()

    native_tools: List[LCTool] = [
        LCTool(name=access_tool.name, func=access_tool.run, coroutine=access_tool.arun, description=access_tool.description),
        LCTool(name=text_tool.name, func=text_tool.run, coroutine=text_tool.arun, description=text_tool.description),
        LCTool(name=hyperlink_tool.name, func=hyperlink_tool.run, coroutine=hyperlink_tool.arun, description=hyperlink_tool.description),
        LCTool(name=dynamic_tavily_tool.name, func=dynamic_tavily_tool.run, coroutine=dynamic_tavily_tool.arun, description=dynamic_tavily_tool.description),
        LCTool(name=whois_tool.name, func=whois_tool.run, coroutine=whois_tool.arun, description=whois_tool.description),
        LCTool(name=certificate_tool.name, func=certificate_tool.run, coroutine=certificate_tool.arun, description=certificate_tool.description),
        LCTool(name=dnsrecord_tool.name, func=dnsrecord_tool.run, coroutine=dnsrecord_tool.arun, description=dnsrecord_tool.description),
        LCTool(name=xsearch_tool.name, func=xsearch_tool.run, coroutine=xsearch_tool.arun, description=xsearch_tool.description),
        LCTool(name=redditsearch_tool.name, func=redditsearch_tool.run, coroutine=redditsearch_tool.arun, description=redditsearch_tool.description),
    ]

    wrapped_tools: List[LCTool] = [LoggingTool(t, url_logger, obs_maxlen=2000) for t in native_tools]

    prompt = CustomPromptTemplate(template=template, tools=wrapped_tools, input_variables=["input", "intermediate_steps"])
    llm_chain = LLMChain(llm=llm, prompt=prompt)
    output_parser = CustomOutputParser(url_logger=url_logger)
    tool_names = [tool.name for tool in wrapped_tools]

    agent = LLMSingleActionAgent(
        llm_chain=llm_chain,
        output_parser=output_parser,
        stop=["\nObservation:"],
        allowed_tools=tool_names
    )

    callbacks = [UrlScopedCallbackHandler(url_logger)]
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=wrapped_tools,
        handle_parsing_errors=True,
        max_iterations=15,
        max_execution_time=600,
        verbose=False,          
        callbacks=callbacks,
    )
    return agent_executor

# ========= URL processing =========
def process_single_url(url: str, analysis_llm_type: Optional[str]) -> None:
    start_time = time.time()
    start_datetime = datetime.now()

    base_domain = urlparse(url).netloc
    generated_uuid = generate_uuid_from_url(url)
    filename_base = f"{current_time}_{generated_uuid}_{base_domain}"

    url_logger, handler = make_url_logger(filename_base)

    try:
        url_logger.info("%s %s", url, base_domain)
        url_logger.info("Analysis started at: %s", start_datetime.strftime('%Y-%m-%d %H:%M:%S'))

        agent_executor = build_agent_executor(url_logger)

        result_dict = None

        if analysis_llm_type in ['o3-mini', 'gpt-4.1', 'gpt-4o-mini', 'Llama', 'Llama-4-Maverick-17B-128E-Instruct-FP8']:
            with get_openai_callback() as cb:
                result_raw = agent_executor.run(f"Please analyze this URL {url}.")
                try:
                    i1 = result_raw.find('{'); i2 = result_raw.rfind('}') + 1
                    result = json.loads(result_raw[i1:i2]) if (i1 != -1 and i2 > i1) else result_raw
                except Exception:
                    result = result_raw

                end_time = time.time()
                execution_time = end_time - start_time
                end_datetime = datetime.now()

                result_dict = {
                    'target_url': url,
                    'analysis_llm': analysis_llm_type,
                    'llm_response': result,
                    'total_tokens': cb.total_tokens,
                    'prompt_tokens': cb.prompt_tokens,
                    'completion_tokens': cb.completion_tokens,
                    'total_cost': cb.total_cost,
                    'execution_time_seconds': round(execution_time, 2),
                    'execution_time_formatted': f"{int(execution_time // 60)}m {int(execution_time % 60)}s",
                    'start_time': start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': end_datetime.strftime('%Y-%m-%d %H:%M:%S')
                }

                url_logger.info("Summary Result: %s", (json.dumps(result, ensure_ascii=False)[:4000] if not isinstance(result, str) else str(result)[:4000]))
                url_logger.info("Total Tokens: %s | Prompt: %s | Completion: %s | Cost: $%s", cb.total_tokens, cb.prompt_tokens, cb.completion_tokens, cb.total_cost)
                url_logger.info("Execution Time: %.2f seconds", execution_time)

        elif analysis_llm_type and (analysis_llm_type.startswith('databricks-') or analysis_llm_type == 'databricks-custom'):
            result_raw = agent_executor.run(f"Please analyze this URL {url}.")
            try:
                i1 = result_raw.find('{'); i2 = result_raw.rfind('}') + 1
                result = json.loads(result_raw[i1:i2]) if (i1 != -1 and i2 > i1) else result_raw
            except Exception:
                result = result_raw

            end_time = time.time()
            execution_time = end_time - start_time
            end_datetime = datetime.now()

            result_dict = {
                'target_url': url,
                'analysis_llm': analysis_llm_type,
                'llm_response': result,
                'endpoint': DATABRICKS_ENDPOINT or analysis_llm_type,
                'execution_time_seconds': round(execution_time, 2),
                'execution_time_formatted': f"{int(execution_time // 60)}m {int(execution_time % 60)}s",
                'start_time': start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': end_datetime.strftime('%Y-%m-%d %H:%M:%S')
            }

            url_logger.info("Summary Result: %s", (json.dumps(result, ensure_ascii=False)[:4000] if not isinstance(result, str) else str(result)[:4000]))
            url_logger.info("Execution Time: %.2f seconds", execution_time)

        else:
            result_raw = agent_executor.run(f"Please analyze this URL {url}.")
            try:
                i1 = result_raw.find('{'); i2 = result_raw.rfind('}') + 1
                result = json.loads(result_raw[i1:i2]) if (i1 != -1 and i2 > i1) else result_raw
            except Exception:
                result = result_raw

            end_time = time.time()
            execution_time = end_time - start_time
            end_datetime = datetime.now()

            result_dict = {
                'target_url': url,
                'analysis_llm': analysis_llm_type,
                'llm_response': result,
                'execution_time_seconds': round(execution_time, 2),
                'execution_time_formatted': f"{int(execution_time // 60)}m {int(execution_time % 60)}s",
                'start_time': start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': end_datetime.strftime('%Y-%m-%d %H:%M:%S')
            }

            url_logger.info("Summary Result: %s", (json.dumps(result, ensure_ascii=False)[:4000] if not isinstance(result, str) else str(result)[:4000]))
            url_logger.info("Execution Time: %.2f seconds", execution_time)

        if result_dict is not None:
            os.makedirs(SAVE_LLM_RESPONSE_DIR, exist_ok=True)
            with open(f'{SAVE_LLM_RESPONSE_DIR}/{filename_base}.json', 'w', encoding='utf-8') as file:
                json.dump(result_dict, file, indent=4, ensure_ascii=False)

    except Exception:
        end_time = time.time()
        execution_time = end_time - start_time
        end_datetime = datetime.now()

        error_dict = {
            'target_url': url,
            'analysis_llm': analysis_llm_type,
            'error': str(sys.exc_info()[1]),
            'traceback': traceback.format_exc(),
            'execution_time_seconds': round(execution_time, 2),
            'execution_time_formatted': f"{int(execution_time // 60)}m {int(execution_time % 60)}s",
            'start_time': start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': end_datetime.strftime('%Y-%m-%d %H:%M:%S')
        }

        error_filename = f"{current_time}_{generate_uuid_from_url(url)}_{urlparse(url).netloc}_ERROR"
        os.makedirs(SAVE_LLM_RESPONSE_DIR, exist_ok=True)
        with open(f'{SAVE_LLM_RESPONSE_DIR}/{error_filename}.json', 'w', encoding='utf-8') as file:
            json.dump(error_dict, file, indent=4, ensure_ascii=False)

        err_line = sanitize_one_line(traceback.format_exc())
        url_logger.error("Exception: %s", _truncate(err_line))

    finally:
        try:
            url_logger.removeHandler(handler)
        finally:
            try:
                handler.close()
            except Exception:
                pass

def main():
    if not TARGET_URL_FILE:
        raise ValueError("TARGET_URL_FILE must be set")
    with open(TARGET_URL_FILE, 'r', encoding='utf-8') as f:
        url_list = [line.strip() for line in f if line.strip()]

    max_workers = int(os.getenv("MAX_WORKERS", "2"))
    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for url in url_list:
            fut = executor.submit(process_single_url, url, ANALYSIS_LLM_TYPE)
            futures.append(fut)
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception:
                print("A task raised an unexpected exception:\n", traceback.format_exc(), file=sys.stderr)

if __name__ == '__main__':
    main()
