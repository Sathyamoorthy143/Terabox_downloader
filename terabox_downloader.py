import requests
import re
import os
from urllib.parse import unquote
import time
import ssl
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

class TeraBoxDownloader:
    def __init__(self):
        self.session = requests.Session()
        
        # Add SSL adapter that ignores certificate verification
        self.session.mount('https://', SSLAdapter())
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
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
        
        # Disable SSL verification for the entire session
        self.session.verify = False
    
    def extract_file_info(self, terabox_url):
        """
        Extract file information from TeraBox share link
        """
        try:
            print(f"Processing URL: {terabox_url}")
            
            # Follow redirects to get the actual page with SSL verification disabled
            response = self.session.get(
                terabox_url, 
                allow_redirects=True, 
                timeout=30,
                verify=False  # Disable SSL verification
            )
            response.raise_for_status()
            
            print(f"Final URL: {response.url}")
            print(f"Status Code: {response.status_code}")
            
            # Enhanced filename extraction
            filename = self._extract_filename(response.text)
            
            if not filename:
                filename = f"terabox_file_{int(time.time())}.bin"
            
            return {
                'success': True,
                'filename': filename,
                'final_url': response.url,
                'content_length': len(response.text)
            }
            
        except Exception as e:
            print(f"Error extracting file info: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_filename(self, html_content):
        """Enhanced filename extraction with multiple patterns"""
        patterns = [
            r'"filename":"([^"]+)"',
            r'"server_filename":"([^"]+)"',
            r'<title>([^<]+)</title>',
            r'<meta property="og:title" content="([^"]+)"',
            r'file_name["\']?:\s*["\']([^"\']+)["\']',
            r'download_filename["\']?:\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                filename = match.group(1).strip()
                if filename and len(filename) > 1:  # Basic validation
                    print(f"Found filename with pattern {pattern}: {filename}")
                    filename = unquote(filename)
                    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                    if not '.' in filename:
                        # Try to guess extension from content
                        if 'video' in html_content.lower():
                            filename += '.mp4'
                        elif 'image' in html_content.lower():
                            filename += '.jpg'
                        else:
                            filename += '.bin'
                    return filename
        return None
    
    def get_download_url(self, page_url):
        """
        Extract actual download URL from TeraBox page with enhanced patterns
        """
        try:
            response = self.session.get(
                page_url, 
                timeout=30,
                verify=False  # Disable SSL verification
            )
            response.raise_for_status()
            
            # Enhanced patterns for download URLs
            url_patterns = [
                r'"dlink":"([^"]+)"',
                r'"downloadUrl":"([^"]+)"',
                r'"url":"([^"]+)"',
                r'downloadUrl["\']?:\s*["\']([^"\']+)["\']',
                r'dlink["\']?:\s*["\']([^"\']+)["\']',
                r'href="(https?://[^"]*?download[^"]*)"',
                r'href="(https?://[^"]*?file[^"]*)"',
                r'src="(https?://[^"]*?stream[^"]*)"',
                r'"(https?://[^"]*?terabox[^"]*?stream[^"]*)"',
                r'"(https?://[^"]*?cdn[^"]*?file[^"]*)"',
            ]
            
            for pattern in url_patterns:
                matches = re.findall(pattern, response.text)
                for match in matches:
                    # Clean and validate the URL
                    download_url = match.replace('\\/', '/')
                    if any(keyword in download_url.lower() for keyword in 
                          ['terabox', 'download', 'stream', 'file', 'cdn', 'dlink']):
                        print(f"Found download URL with pattern {pattern}: {download_url}")
                        return download_url
            
            # Try to find in JavaScript variables
            js_patterns = [
                r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
                r'window\.open\(["\']([^"\']+)["\']',
            ]
            
            for pattern in js_patterns:
                matches = re.findall(pattern, response.text)
                for match in matches:
                    if 'http' in match:
                        print(f"Found JS redirect URL: {match}")
                        return match
            
            print("No download URL found in page content")
            return None
            
        except Exception as e:
            print(f"Error extracting download URL: {e}")
            return None
    
    def download_file(self, download_url, filename, download_folder, chunk_size=8192):
        """
        Download the file from the provided URL with SSL verification disabled
        """
        try:
            # Full file path
            filepath = os.path.join(download_folder, filename)
            
            print(f"Starting download from: {download_url}")
            print(f"Saving to: {filepath}")
            
            # Stream download with SSL verification disabled
            response = self.session.get(
                download_url, 
                stream=True, 
                timeout=60,
                verify=False  # Disable SSL verification
            )
            response.raise_for_status()
            
            # Get file size if available
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
                            print(f"\rDownload progress: {progress:.1f}%", end='', flush=True)
            
            print(f"\nDownload completed: {downloaded} bytes")
            
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