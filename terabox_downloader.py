import requests
import re
import os
import json
import time
from urllib.parse import unquote, urlparse, parse_qs
import urllib3
from requests.adapters import HTTPAdapter

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TeraBoxDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
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
            print(f"Processing URL: {terabox_url}")
            
            # Follow redirects to get the actual page
            response = self.session.get(
                terabox_url, 
                allow_redirects=True, 
                timeout=30
            )
            response.raise_for_status()
            
            print(f"Final URL: {response.url}")
            print(f"Status Code: {response.status_code}")
            
            # Extract filename from page title or meta tags
            filename = self._extract_filename(response.text, response.url)
            
            return {
                'success': True,
                'filename': filename,
                'final_url': response.url,
                'content': response.text,
                'content_length': len(response.text)
            }
            
        except Exception as e:
            print(f"Error extracting file info: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_filename(self, html_content, url):
        """Extract filename from HTML content"""
        patterns = [
            r'<title>([^<]+)</title>',
            r'<meta property="og:title" content="([^"]+)"',
            r'"filename":"([^"]+)"',
            r'"server_filename":"([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                filename = match.group(1).strip()
                if filename and len(filename) > 1:
                    print(f"Found filename: {filename}")
                    # Clean filename
                    filename = unquote(filename)
                    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                    # Ensure it has an extension
                    if not re.search(r'\.[a-zA-Z0-9]{2,4}$', filename):
                        filename += '.mp4'  # Default to mp4 for videos
                    return filename
        
        # Fallback: generate filename from URL
        return f"terabox_file_{int(time.time())}.mp4"
    
    def get_download_url(self, page_url, html_content=None):
        """
        Extract actual download URL from TeraBox page
        """
        try:
            if not html_content:
                response = self.session.get(page_url, timeout=30)
                html_content = response.text
            
            print("Searching for download URLs in page content...")
            
            # Method 1: Look for JSON data in script tags
            download_url = self._extract_from_json(html_content)
            if download_url:
                return download_url
            
            # Method 2: Look for direct download links
            download_url = self._extract_direct_links(html_content)
            if download_url:
                return download_url
            
            # Method 3: Look for video sources
            download_url = self._extract_video_sources(html_content)
            if download_url:
                return download_url
            
            # Method 4: Try to find API endpoints
            download_url = self._extract_api_endpoints(html_content)
            if download_url:
                return download_url
            
            print("No download URL found using all methods")
            return None
            
        except Exception as e:
            print(f"Error extracting download URL: {e}")
            return None
    
    def _extract_from_json(self, html_content):
        """Extract download URL from JSON data in script tags"""
        try:
            # Look for window.yunData or similar JSON objects
            json_patterns = [
                r'window\.yunData\s*=\s*({[^;]+});',
                r'var\s+yunData\s*=\s*({[^;]+});',
                r'window\.data\s*=\s*({[^;]+});',
                r'"server_filename"[^}]*"dlink"[^}]*}',
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, html_content, re.DOTALL)
                for match in matches:
                    try:
                        # Clean the JSON string
                        json_str = match.replace('\\/', '/').replace('\\"', '"')
                        data = json.loads(json_str)
                        
                        # Try different key combinations
                        if isinstance(data, dict):
                            # Check for direct dlink
                            if 'dlink' in data:
                                return data['dlink']
                            
                            # Check for file list
                            if 'file_list' in data and isinstance(data['file_list'], list) and len(data['file_list']) > 0:
                                file_data = data['file_list'][0]
                                if 'dlink' in file_data:
                                    return file_data['dlink']
                            
                            # Check for info
                            if 'info' in data and isinstance(data['info'], dict):
                                if 'dlink' in data['info']:
                                    return data['info']['dlink']
                    
                    except json.JSONDecodeError:
                        # Try to extract dlink directly from the string
                        dlink_match = re.search(r'"dlink"\s*:\s*"([^"]+)"', match)
                        if dlink_match:
                            return dlink_match.group(1).replace('\\/', '/')
                        
        except Exception as e:
            print(f"Error extracting from JSON: {e}")
        
        return None
    
    def _extract_direct_links(self, html_content):
        """Extract direct download links from HTML"""
        patterns = [
            r'href="(https?://[^"]*?\.mp4[^"]*)"',
            r'href="(https?://[^"]*?\.mkv[^"]*)"',
            r'href="(https?://[^"]*?\.avi[^"]*)"',
            r'href="(https?://[^"]*?\.mov[^"]*)"',
            r'href="(https?://[^"]*?download[^"]*)"',
            r'href="(https?://[^"]*?file[^"]*)"',
            r'src="(https?://[^"]*?\.mp4[^"]*)"',
            r'src="(https?://[^"]*?\.mkv[^"]*)"',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for url in matches:
                clean_url = url.replace('\\/', '/')
                if self._is_valid_download_url(clean_url):
                    print(f"Found direct download URL: {clean_url}")
                    return clean_url
        
        return None
    
    def _extract_video_sources(self, html_content):
        """Extract video source URLs"""
        # Look for video tags
        video_pattern = r'<video[^>]*>\s*<source[^>]*src="([^"]*)"'
        matches = re.findall(video_pattern, html_content, re.IGNORECASE | re.DOTALL)
        for url in matches:
            clean_url = url.replace('\\/', '/')
            if self._is_valid_download_url(clean_url):
                print(f"Found video source URL: {clean_url}")
                return clean_url
        
        return None
    
    def _extract_api_endpoints(self, html_content):
        """Extract API endpoints that might provide download links"""
        patterns = [
            r'"/api/[^"]*file[^"]*download[^"]*"',
            r'"/api/[^"]*download[^"]*"',
            r'"/file/[^"]*download[^"]*"',
        ]
        
        base_domain = "https://www.terabox.com"
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            for endpoint in matches:
                endpoint = endpoint.strip('"')
                full_url = base_domain + endpoint
                if self._is_valid_download_url(full_url):
                    print(f"Found API endpoint: {full_url}")
                    return full_url
        
        return None
    
    def _is_valid_download_url(self, url):
        """Check if URL looks like a valid download URL"""
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Check if it's not a common static file
        excluded_patterns = [
            '.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.ico',
            'google', 'facebook', 'twitter', 'analytics'
        ]
        
        for pattern in excluded_patterns:
            if pattern in url.lower():
                return False
        
        return True
    
    def download_file(self, download_url, filename, download_folder, chunk_size=8192):
        """
        Download the file from the provided URL
        """
        try:
            # Full file path
            filepath = os.path.join(download_folder, filename)
            
            print(f"Starting download from: {download_url}")
            print(f"Saving to: {filepath}")
            
            # Stream download
            headers = {
                'Referer': 'https://www.terabox.com/',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
            
            # Check content type to ensure it's a video/file
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type and len(response.content) < 1024:
                # Probably got an error page instead of the file
                error_text = response.text[:500]
                return {
                    'success': False,
                    'error': f"Received HTML page instead of file. Content: {error_text}"
                }
            
            # Get file size
            total_size = int(response.headers.get('content-length', 0))
            
            downloaded = 0
            with open(filepath, 'wb') as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        
                        # Show progress in console
                        if total_size:
                            progress = (downloaded / total_size) * 100
                            print(f"\rDownload progress: {progress:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)
            
            print(f"\nDownload completed: {downloaded} bytes")
            
            # Verify file was actually downloaded
            if downloaded == 0:
                if os.path.exists(filepath):
                    os.remove(filepath)
                return {
                    'success': False,
                    'error': "Downloaded file is 0 bytes - likely invalid download URL"
                }
            
            return {
                'success': True,
                'filepath': filepath,
                'file_size': downloaded
            }
            
        except Exception as e:
            print(f"Error downloading file: {e}")
            # Clean up partially downloaded file
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
            return {
                'success': False,
                'error': str(e)
            }