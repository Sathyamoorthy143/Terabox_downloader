import requests
import re
import os
from urllib.parse import unquote
import time

class TeraBoxDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def extract_file_info(self, terabox_url):
        """
        Extract file information from TeraBox share link
        """
        try:
            print(f"Processing URL: {terabox_url}")
            
            # Follow redirects to get the actual page
            response = self.session.get(terabox_url, allow_redirects=True, timeout=30)
            response.raise_for_status()
            
            print(f"Final URL: {response.url}")
            
            # Look for file information in the page content
            patterns = [
                r'"filename":"([^"]+)"',
                r'file_name["\']?:\s*["\']([^"\']+)["\']',
                r'<title>([^<]+)</title>',
                r'<meta property="og:title" content="([^"]+)"',
            ]
            
            filename = None
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    filename = match.group(1).strip()
                    print(f"Found filename with pattern {pattern}: {filename}")
                    break
            
            # Clean filename
            if filename:
                filename = unquote(filename)
                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                # Add extension if missing
                if not '.' in filename:
                    filename += '.bin'
            else:
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
    
    def get_download_url(self, page_url):
        """
        Extract actual download URL from TeraBox page
        """
        try:
            response = self.session.get(page_url, timeout=30)
            response.raise_for_status()
            
            # Common patterns for download URLs
            url_patterns = [
                r'"downloadUrl":"([^"]+)"',
                r'"url":"([^"]+)"',
                r'downloadUrl["\']?:\s*["\']([^"\']+)["\']',
                r'href="(https?://[^"]*?download[^"]*)"',
                r'href="(https?://[^"]*?file[^"]*)"',
                r'src="(https?://[^"]*?stream[^"]*)"',
                r'"(https?://[^"]*?terabox[^"]*?stream[^"]*)"',
            ]
            
            for pattern in url_patterns:
                matches = re.findall(pattern, response.text)
                for match in matches:
                    # Clean the URL
                    download_url = match.replace('\\/', '/')
                    if any(keyword in download_url.lower() for keyword in ['terabox', 'download', 'stream', 'file']):
                        print(f"Found download URL: {download_url}")
                        return download_url
            
            print("No download URL found in page content")
            return None
            
        except Exception as e:
            print(f"Error extracting download URL: {e}")
            return None
    
    def download_file(self, download_url, filename, download_folder, chunk_size=8192):
        """
        Download the file from the provided URL
        """
        try:
            # Full file path
            filepath = os.path.join(download_folder, filename)
            
            print(f"Starting download from: {download_url}")
            print(f"Saving to: {filepath}")
            
            # Stream download to handle large files
            response = self.session.get(download_url, stream=True, timeout=60)
            response.raise_for_status()
            
            # Get file size if available
            total_size = int(response.headers.get('content-length', 0))
            
            downloaded = 0
            with open(filepath, 'wb') as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
            
            print(f"Download completed: {downloaded} bytes")
            
            return {
                'success': True,
                'filepath': filepath,
                'file_size': downloaded
            }
            
        except Exception as e:
            print(f"Error downloading file: {e}")
            # Clean up partially downloaded file
            if os.path.exists(filepath):
                os.remove(filepath)
            return {
                'success': False,
                'error': str(e)
            }