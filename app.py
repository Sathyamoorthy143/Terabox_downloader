from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import os
import threading
from terabox_downloader import TeraBoxDownloader
import uuid
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure download directory exists
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# Store download status
download_status = {}

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    terabox_url = data.get('url', '').strip()
    
    if not terabox_url:
        return jsonify({'error': 'Please provide a TeraBox URL'}), 400
    
    # Validate URL format
    if not terabox_url.startswith(('http://', 'https://')):
        return jsonify({'error': 'Please enter a valid HTTP/HTTPS URL'}), 400
    
    # Check if it's a TeraBox domain
    if 'terabox' not in terabox_url.lower():
        return jsonify({'error': 'Please provide a valid TeraBox URL'}), 400
    
    # Generate unique download ID
    download_id = str(uuid.uuid4())
    
    # Start download in background thread
    download_thread = DownloadThread(download_id, terabox_url)
    download_thread.start()
    
    return jsonify({
        'download_id': download_id,
        'message': 'Download started successfully!'
    })

@app.route('/status/<download_id>')
def get_status(download_id):
    status = download_status.get(download_id, {})
    return jsonify(status)

@app.route('/download-file/<download_id>')
def download_file(download_id):
    status = download_status.get(download_id, {})
    
    if status.get('status') != 'completed':
        return jsonify({'error': 'File not ready for download'}), 400
    
    filepath = status.get('filepath')
    filename = status.get('filename')
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    @after_this_request
    def remove_file(response):
        try:
            # Clean up file after download (optional)
            # os.remove(filepath)
            pass
        except Exception as error:
            app.logger.error("Error removing file", error)
        return response
    
    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='application/octet-stream'
    )

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Clean up old download files"""
    try:
        data = request.get_json()
        filepath = data.get('filepath')
        
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'message': 'File cleaned up successfully'})
        
        return jsonify({'error': 'File not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)