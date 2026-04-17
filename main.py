from flask import Flask, request, jsonify
import yt_dlp
import os
import tempfile
import base64

app = Flask(__name__)

def get_cookies_file(tmpdir):
    cookies = os.environ.get('IG_COOKIES', '')
    if not cookies:
        return None
    cookies_path = os.path.join(tmpdir, 'cookies.txt')
    with open(cookies_path, 'w') as f:
        f.write(cookies)
    return cookies_path

@app.route('/download', methods=['GET'])
def download():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL obrigatória"}), 400

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            cookies_file = get_cookies_file(tmpdir)

            ydl_opts = {
                'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
                'writeinfojson': True,
                'quiet': True,
                'no_warnings': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
                }
            }

            if cookies_file:
                ydl_opts['cookiefile'] = cookies_file

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            arquivos = []
            legenda = info.get('description', '') or info.get('title', '')
            tipo = 'Reels'

            for f in sorted(os.listdir(tmpdir)):
                if f.endswith('.json') or f == 'cookies.txt':
                    continue
                filepath = os.path.join(tmpdir, f)
                ext = f.split('.')[-1].lower()
                if ext not in ['mp4', 'jpg', 'jpeg', 'png', 'webp']:
                    continue
                with open(filepath, 'rb') as file:
                    conteudo = base64.b64encode(file.read()).decode('utf-8')
                mime = 'video/mp4' if ext == 'mp4' else f'image/{"jpeg" if ext == "jpg" else ext}'
                arquivos.append({
                    "nome": f,
                    "ext": ext,
                    "mime": mime,
                    "base64": conteudo
                })

            imagens = [a for a in arquivos if a['ext'] != 'mp4']
            if len(imagens) > 1:
                tipo = 'Carrossel'
            elif len(imagens) == 1:
                tipo = 'Foto'

            return jsonify({
                "sucesso": True,
                "tipo": tipo,
                "legenda": legenda,
                "total_arquivos": len(arquivos),
                "arquivos": arquivos
            })

    except Exception as e:
        return jsonify({"error": str(e), "sucesso": False}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
