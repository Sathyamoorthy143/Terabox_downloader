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

class TeraBoxDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        
        # Add retry strategy
        adapter = HTTPAdapter(max_retries=3)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
        """
        Extract file information from TeraBox share link
        """
        try:
            print(f"🔍 Processing URL: {terabox_url}")
            
            # Add random delay to avoid detection
            time.sleep(random.uniform(1, 3))
            
            # Follow redirects to get the actual page
            response = self.session.get(
                terabox_url, 
                allow_redirects=True, 
                timeout=30
            )
            response.raise_for_status()
            
            print(f"✅ Final URL: {response.url}")
            print(f"📄 Status Code: {response.status_code}")
            
            # Extract filename from page
            filename = self._extract_filename(response.text, response.url)
            
            return {
                'success': True,
                'filename': filename,
                'final_url': response.url,
                'content': response.text,
                'content_length': len(response.text)
            }
            
        except Exception as e:
            print(f"❌ Error extracting file info: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_filename(self, html_content, url):
        """Extract filename from HTML content using multiple methods"""
        patterns = [
            r'<title>([^<]+)</title>',
            r'<meta property="og:title" content="([^"]+)"',
            r'"filename":"([^"]+)"',
            r'"server_filename":"([^"]+)"',
            r'file_name["\']?:\s*["\']([^"\']+)["\']',
            r'download_filename["\']?:\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                filename = match.group(1).strip()
                if filename and len(filename) > 1:
                    print(f"📝 Found filename: {filename}")
                    # Clean filename
                    filename = unquote(filename)
                    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                    # Ensure it has an extension
                    if not re.search(r'\.[a-zA-Z0-9]{2,4}$', filename):
                        # Try to detect file type from content
                        if any(ext in html_content.lower() for ext in ['.mp4', '.avi', '.mkv', '.mov']):
                            filename += '.mp4'
                        elif any(ext in html_content.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                            filename += '.jpg'
                        elif any(ext in html_content.lower() for ext in ['.pdf', '.doc', '.docx']):
                            filename += '.pdf'
                        else:
                            filename += '.bin'
                    return filename
        
        # Fallback: generate filename from URL or timestamp
        return f"terabox_file_{int(time.time())}.mp4"
    
    def get_download_url(self, page_url, html_content=None):
        """
        Extract actual download URL from TeraBox page using multiple methods
        """
        try:
            if not html_content:
                response = self.session.get(page_url, timeout=30)
                html_content = response.text
            
            print("🔍 Searching for download URLs in page content...")
            
            # Method 1: Extract from window.yunData (most reliable)
            download_url = self._extract_from_yun_data(html_content)
            if download_url:
                print(f"✅ Found download URL from yunData: {download_url}")
                return download_url
            
            # Method 2: Extract from JSON-LD data
            download_url = self._extract_from_json_ld(html_content)
            if download_url:
                print(f"✅ Found download URL from JSON-LD: {download_url}")
                return download_url
            
            # Method 3: Extract from JavaScript variables
            download_url = self._extract_from_javascript(html_content)
            if download_url:
                print(f"✅ Found download URL from JavaScript: {download_url}")
                return download_url
            
            # Method 4: Look for direct video/file links
            download_url = self._extract_direct_links(html_content)
            if download_url:
                print(f"✅ Found direct download URL: {download_url}")
                return download_url
            
            # Method 5: Try to find API endpoints
            download_url = self._extract_api_endpoints(html_content, page_url)
            if download_url:
                print(f"✅ Found API endpoint: {download_url}")
                return download_url
            
            print("❌ No download URL found using all methods")
            print("💡 Debug: Saving page content for analysis...")
            self._debug_save_page(html_content)
            
            return None
            
        except Exception as e:
            print(f"❌ Error extracting download URL: {e}")
            return None
    
    def _extract_from_yun_data(self, html_content):
        """Extract download URL from window.yunData JavaScript object"""
        try:
            # Look for window.yunData pattern
            yun_data_patterns = [
                r'window\.yunData\s*=\s*({[^;]+});',
                r'var\s+yunData\s*=\s*({[^;]+});',
                r'window\.data\s*=\s*({[^;]+});',
            ]
            
            for pattern in yun_data_patterns:
                match = re.search(pattern, html_content, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    # Clean the JSON string
                    json_str = self._clean_json_string(json_str)
                    
                    try:
                        data = json.loads(json_str)
                        return self._find_download_url_in_data(data)
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON decode error: {e}")
                        # Try to extract dlink directly from string
                        dlink_match = re.search(r'"dlink"\s*:\s*"([^"]+)"', json_str)
                        if dlink_match:
                            return dlink_match.group(1).replace('\\/', '/')
            
            return None
        except Exception as e:
            print(f"⚠️ Error in yunData extraction: {e}")
            return None
    
    def _extract_from_json_ld(self, html_content):
        """Extract download URL from JSON-LD structured data"""
        try:
            json_ld_pattern = r'<script type="application/ld\+json">\s*({[^<]+})\s*</script>'
            match = re.search(json_ld_pattern, html_content, re.DOTALL)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                
                # Look for contentUrl in JSON-LD
                if 'contentUrl' in data:
                    return data['contentUrl']
                elif 'url' in data:
                    return data['url']
                
        except Exception as e:
            print(f"⚠️ Error in JSON-LD extraction: {e}")
        
        return None
    
    def _extract_from_javascript(self, html_content):
        """Extract download URL from various JavaScript patterns"""
        try:
            # Common JavaScript patterns for file URLs
            js_patterns = [
                r'fileUrl\s*=\s*["\']([^"\']+)["\']',
                r'downloadUrl\s*=\s*["\']([^"\']+)["\']',
                r'videoUrl\s*=\s*["\']([^"\']+)["\']',
                r'src\s*:\s*["\']([^"\']+)["\']',
                r'url\s*:\s*["\']([^"\']+)["\']',
                r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
                r'window\.open\(["\']([^"\']+)["\']',
            ]
            
            for pattern in js_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for url in matches:
                    if self._is_valid_download_url(url):
                        return url.replace('\\/', '/')
        
        except Exception as e:
            print(f"⚠️ Error in JavaScript extraction: {e}")
        
        return None
    
    def _extract_direct_links(self, html_content):
        """Extract direct download links from HTML"""
        try:
            # Video/file specific patterns
            patterns = [
                r'src="(https?://[^"]*?\.mp4[^"]*)"',
                r'src="(https?://[^"]*?\.mkv[^"]*)"',
                r'src="(https?://[^"]*?\.avi[^"]*)"',
                r'src="(https?://[^"]*?\.mov[^"]*)"',
                r'href="(https?://[^"]*?\.mp4[^"]*)"',
                r'href="(https?://[^"]*?\.mkv[^"]*)"',
                r'data-src="(https?://[^"]*?\.mp4[^"]*)"',
                r'data-url="(https?://[^"]*?\.mp4[^"]*)"',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for url in matches:
                    clean_url = url.replace('\\/', '/')
                    if self._is_valid_download_url(clean_url):
                        return clean_url
        
        except Exception as e:
            print(f"⚠️ Error in direct links extraction: {e}")
        
        return None
    
    def _extract_api_endpoints(self, html_content, page_url):
        """Extract API endpoints that might provide download links"""
        try:
            # Common API patterns
            api_patterns = [
                r'"/api/[^"]*"',
                r'"/download/[^"]*"',
                r'"/file/[^"]*"',
                r'"/v1/[^"]*"',
                r'"/v2/[^"]*"',
            ]
            
            # Extract base domain
            parsed_url = urlparse(page_url)
            base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            for pattern in api_patterns:
                matches = re.findall(pattern, html_content)
                for endpoint in matches:
                    endpoint = endpoint.strip('"')
                    full_url = base_domain + endpoint
                    if self._is_valid_download_url(full_url):
                        return full_url
        
        except Exception as e:
            print(f"⚠️ Error in API endpoints extraction: {e}")
        
        return None
    
    def _find_download_url_in_data(self, data):
        """Recursively search for download URL in data structure"""
        if isinstance(data, dict):
            # Check common keys for download URLs
            for key in ['dlink', 'downloadUrl', 'url', 'fileUrl', 'videoUrl', 'contentUrl']:
                if key in data and isinstance(data[key], str) and data[key].startswith('http'):
                    return data[key].replace('\\/', '/')
            
            # Recursively search in values
            for value in data.values():
                result = self._find_download_url_in_data(value)
                if result:
                    return result
        
        elif isinstance(data, list):
            for item in data:
                result = self._find_download_url_in_data(item)
                if result:
                    return result
        
        return None
    
    def _clean_json_string(self, json_str):
        """Clean JSON string before parsing"""
        # Remove trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        # Fix common JSON issues
        json_str = json_str.replace('\\/', '/')
        return json_str
    
    def _is_valid_download_url(self, url):
        """Check if URL looks like a valid download URL"""
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Exclude common non-download URLs
        excluded_patterns = [
            '.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg',
            'google', 'facebook', 'twitter', 'analytics', 'ads', 'tracking',
            'bootstrap', 'jquery', 'font-awesome'
        ]
        
        for pattern in excluded_patterns:
            if pattern in url.lower():
                return False
        
        # Include patterns that indicate download URLs
        included_patterns = [
            'download', 'file', 'video', 'stream', 'cdn', 'terabox',
            '.mp4', '.mkv', '.avi', '.mov', '.pdf', '.zip', '.rar'
        ]
        
        for pattern in included_patterns:
            if pattern in url.lower():
                return True
        
        return len(url) > 20  # Basic length check
    
    def _debug_save_page(self, html_content):
        """Save page content for debugging"""
        try:
            debug_dir = "debug_pages"
            os.makedirs(debug_dir, exist_ok=True)
            filename = f"{debug_dir}/terabox_page_{int(time.time())}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"💾 Debug page saved: {filename}")
        except Exception as e:
            print(f"⚠️ Could not save debug page: {e}")
    
    def download_file(self, download_url, filename, download_folder, chunk_size=8192):
        """
        Download the file from the provided URL
        """
        try:
            # Full file path
            filepath = os.path.join(download_folder, filename)
            
            print(f"⬇️ Starting download from: {download_url}")
            print(f"💾 Saving to: {filepath}")
            
            # Add referer header
            headers = {
                'Referer': 'https://www.terabox.com/',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Range': 'bytes=0-',  # Support resume
            }
            
            response = self.session.get(
                download_url, 
                stream=True, 
                timeout=60,
                headers=headers
            )
            
            # Check if we got a valid response
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.reason}"
                }
            
            # Check content type and size
            content_type = response.headers.get('content-type', '')
            content_length = int(response.headers.get('content-length', 0))
            
            print(f"📊 Content-Type: {content_type}")
            print(f"📏 Content-Length: {content_length} bytes")
            
            # Check if it's a small HTML page (likely error)
            if 'text/html' in content_type and content_length < 5000:
                error_text = response.text[:500]
                print(f"❌ Received HTML error page: {error_text}")
                return {
                    'success': False,
                    'error': "Received error page instead of file. The link might be invalid or restricted."
                }
            
            downloaded = 0
            with open(filepath, 'wb') as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        
                        # Show progress
                        if content_length:
                            progress = (downloaded / content_length) * 100
                            print(f"\r📈 Download progress: {progress:.1f}% ({downloaded}/{content_length} bytes)", end='', flush=True)
            
            print(f"\n✅ Download completed: {downloaded} bytes")
            
            # Verify file was actually downloaded
            if downloaded == 0:
                if os.path.exists(filepath):
                    os.remove(filepath)
                return {
                    'success': False,
                    'error': "Downloaded file is 0 bytes - likely invalid download URL"
                }
            
            # Verify file exists and has content
            if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                return {
                    'success': False,
                    'error': "Downloaded file is empty or missing"
                }
            
            return {
                'success': True,
                'filepath': filepath,
                'file_size': downloaded
            }
            
        except Exception as e:
            print(f"❌ Error downloading file: {e}")
            # Clean up partially downloaded file
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
            return {
                'success': False,
                'error': str(e)
            }