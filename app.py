class DownloadThread(threading.Thread):
    def __init__(self, download_id, terabox_url):
        threading.Thread.__init__(self)
        self.download_id = download_id
        self.terabox_url = terabox_url
        self.downloader = TeraBoxDownloader()
        
    def run(self):
        try:
            download_status[self.download_id] = {
                'status': 'processing',
                'message': 'Extracting file information from TeraBox...',
                'filename': None,
                'filepath': None
            }
            
            # Step 1: Extract file information
            file_info = self.downloader.extract_file_info(self.terabox_url)
            if not file_info['success']:
                download_status[self.download_id] = {
                    'status': 'error',
                    'message': f"Error extracting file info: {file_info['error']}"
                }
                return
            
            download_status[self.download_id] = {
                'status': 'processing',
                'message': 'Finding download URL... This may take a moment.',
                'filename': file_info['filename']
            }
            
            # Step 2: Get download URL using the extracted HTML content
            download_url = self.downloader.get_download_url(
                file_info['final_url'], 
                file_info.get('content')
            )
            
            if not download_url:
                download_status[self.download_id] = {
                    'status': 'error',
                    'message': 'Could not find download URL. The link might be: password protected, expired, or require premium account.'
                }
                return
            
            download_status[self.download_id] = {
                'status': 'downloading',
                'message': 'Starting download...',
                'filename': file_info['filename']
            }
            
            # Step 3: Download the file
            result = self.downloader.download_file(
                download_url, 
                file_info['filename'], 
                app.config['DOWNLOAD_FOLDER']
            )
            
            if result['success']:
                size_mb = result['file_size'] / (1024 * 1024)
                download_status[self.download_id] = {
                    'status': 'completed',
                    'message': f'Download completed successfully! File size: {size_mb:.2f} MB',
                    'filename': file_info['filename'],
                    'filepath': result['filepath'],
                    'file_size': result['file_size']
                }
            else:
                download_status[self.download_id] = {
                    'status': 'error',
                    'message': f"Download failed: {result['error']}"
                }
                
        except Exception as e:
            download_status[self.download_id] = {
                'status': 'error',
                'message': f"Unexpected error: {str(e)}"
            }