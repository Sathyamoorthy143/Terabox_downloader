import requests
import re
import os
import json
import time
import random
from urllib.parse import unquote, urlparse, parse_qs
import urllib3
from requests.adapters import HTTPAdapter

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TeraBoxDownloaderAdvanced:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        
        # Add retry strategy
        adapter = HTTPAdapter(max_retries=3)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.update_headers()
    
    def update_headers(self):
        """Update headers with random user agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        ]
        
        self.session.headers.update({
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        })
    
    def extract_file_info(self, terabox_url):
        """Extract file information using multiple methods"""
        try:
            print(f"🔍 Processing URL: {terabox_url}")
            
            # Method 1: Direct page analysis
            result = self._method_direct_analysis(terabox_url)
            if result['success']:
                return result
            
            # Method 2: API endpoint discovery
            result = self._method_api_discovery(terabox_url)
            if result['success']:
                return result
            
            # Method 3: Mobile user agent approach
            result = self._method_mobile_approach(terabox_url)
            if result['success']:
                return result
            
            return {
                'success': False,
                'error': 'All extraction methods failed. The link might be invalid, password protected, or require premium account.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Extraction failed: {str(e)}'
            }
    
    def _method_direct_analysis(self, url):
        """Method 1: Direct page analysis"""
        try:
            print("🔄 Trying Method 1: Direct page analysis...")
            time.sleep(2)
            
            response = self.session.get(url, timeout=30, allow_redirects=True)
            
            # Look for common TeraBox patterns
            patterns = [
                r'window\.yunData\s*=\s*({[^;]+});',
                r'window\.data\s*=\s*({[^;]+});',
                r'"dlink"\s*:\s*"([^"]+)"',
                r'"downloadUrl"\s*:\s*"([^"]+)"',
                r'<meta property="og:video" content="([^"]+)"',
                r'<video[^>]+src="([^"]+)"',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, response.text, re.DOTALL)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    
                    if match.startswith('{'):
                        # JSON data found
                        try:
                            data = json.loads(match)
                            download_url = self._find_url_in_json(data)
                            if download_url:
                                filename = self._extract_filename(response.text)
                                return {
                                    'success': True,
                                    'filename': filename,
                                    'final_url': response.url,
                                    'content': response.text,
                                    'download_url': download_url
                                }
                        except:
                            continue
                    elif match.startswith('http'):
                        # Direct URL found
                        filename = self._extract_filename(response.text)
                        return {
                            'success': True,
                            'filename': filename,
                            'final_url': response.url,
                            'content': response.text,
                            'download_url': match
                        }
            
            return {'success': False}
            
        except Exception as e:
            print(f"❌ Method 1 failed: {e}")
            return {'success': False}
    
    def _method_api_discovery(self, url):
        """Method 2: API endpoint discovery"""
        try:
            print("🔄 Trying Method 2: API discovery...")
            time.sleep(2)
            
            # Extract share code from URL
            share_code = self._extract_share_code(url)
            if not share_code:
                return {'success': False}
            
            # Try different API endpoints
            api_endpoints = [
                f"https://www.terabox.com/api/shorturlinfo?app_id=250528&shorturl={share_code}",
                f"https://www.terabox.com/share/list?app_id=250528&shorturl={share_code}",
                f"https://www.1024tera.com/api/shorturlinfo?app_id=250528&shorturl={share_code}",
            ]
            
            for api_url in api_endpoints:
                try:
                    headers = {
                        'Referer': 'https://www.terabox.com/',
                        'X-Requested-With': 'XMLHttpRequest',
                    }
                    
                    response = self.session.get(api_url, headers=headers, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        download_url = self._find_url_in_json(data)
                        if download_url:
                            filename = data.get('server_filename', f'file_{int(time.time())}.mp4')
                            return {
                                'success': True,
                                'filename': filename,
                                'final_url': url,
                                'content': response.text,
                                'download_url': download_url
                            }
                except:
                    continue
            
            return {'success': False}
            
        except Exception as e:
            print(f"❌ Method 2 failed: {e}")
            return {'success': False}
    
    def _method_mobile_approach(self, url):
        """Method 3: Mobile user agent approach"""
        try:
            print("🔄 Trying Method 3: Mobile approach...")
            time.sleep(2)
            
            # Switch to mobile user agent
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }
            
            response = self.session.get(url, headers=mobile_headers, timeout=30)
            
            # Look for mobile-specific patterns
            patterns = [
                r'data-url="([^"]+)"',
                r'data-file="([^"]+)"',
                r'download-link="([^"]+)"',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, response.text)
                for match in matches:
                    if match.startswith('http'):
                        filename = self._extract_filename(response.text)
                        return {
                            'success': True,
                            'filename': filename,
                            'final_url': response.url,
                            'content': response.text,
                            'download_url': match
                        }
            
            return {'success': False}
            
        except Exception as e:
            print(f"❌ Method 3 failed: {e}")
            return {'success': False}
    
    def _extract_share_code(self, url):
        """Extract share code from TeraBox URL"""
        patterns = [
            r'/s/([a-zA-Z0-9_-]+)',
            r'share/([a-zA-Z0-9_-]+)',
            r'/([a-zA-Z0-9_-]{10,})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _find_url_in_json(self, data):
        """Recursively find download URL in JSON data"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['dlink', 'download_url', 'direct_link', 'url'] and isinstance(value, str) and value.startswith('http'):
                    return value
                if isinstance(value, (dict, list)):
                    result = self._find_url_in_json(value)
                    if result:
                        return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_url_in_json(item)
                if result:
                    return result
        return None
    
    def _extract_filename(self, html_content):
        """Extract filename from HTML content"""
        patterns = [
            r'<title>([^<]+)</title>',
            r'"server_filename":"([^"]+)"',
            r'"filename":"([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                filename = match.group(1).strip()
                if filename:
                    filename = unquote(filename)
                    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                    if not re.search(r'\.[a-zA-Z0-9]{2,4}$', filename):
                        filename += '.mp4'
                    return filename
        
        return f'terabox_file_{int(time.time())}.mp4'
    
    def get_download_url(self, page_url, html_content=None):
        """Get download URL - simplified interface"""
        if html_content:
            # If we already have content, try to extract from it
            download_url = self._find_url_in_content(html_content)
            if download_url:
                return download_url
        
        # Otherwise use the multi-method approach
        result = self.extract_file_info(page_url)
        if result['success']:
            return result.get('download_url')
        
        return None
    
    def _find_url_in_content(self, html_content):
        """Find download URL in existing HTML content"""
        patterns = [
            r'"dlink"\s*:\s*"([^"]+)"',
            r'"downloadUrl"\s*:\s*"([^"]+)"',
            r'window\.yunData\s*=\s*({[^;]+});',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.DOTALL)
            for match in matches:
                if match.startswith('{'):
                    try:
                        data = json.loads(match)
                        return self._find_url_in_json(data)
                    except:
                        continue
                elif match.startswith('http'):
                    return match
        return None
    
    def download_file(self, download_url, filename, download_folder, chunk_size=8192):
        """Download the file with proper headers"""
        try:
            filepath = os.path.join(download_folder, filename)
            
            print(f"⬇️ Starting download: {filename}")
            print(f"🔗 From: {download_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.terabox.com/',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Range': 'bytes=0-',
            }
            
            response = self.session.get(
                download_url,
                stream=True,
                timeout=60,
                headers=headers
            )
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.reason}'
                }
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filepath, 'wb') as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size:
                            progress = (downloaded / total_size) * 100
                            print(f"\r📈 Progress: {progress:.1f}%", end='', flush=True)
            
            print(f"\n✅ Download completed: {downloaded} bytes")
            
            if downloaded == 0:
                if os.path.exists(filepath):
                    os.remove(filepath)
                return {
                    'success': False,
                    'error': 'Downloaded file is 0 bytes'
                }
            
            return {
                'success': True,
                'filepath': filepath,
                'file_size': downloaded
            }
            
        except Exception as e:
            print(f"❌ Download error: {e}")
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
            return {
                'success': False,
                'error': str(e)
            }