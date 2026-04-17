from flask import Flask, request, jsonify
import yt_dlp
import os
import tempfile
import base64
import re

app = Flask(__name__)

def extrair_shortcode(url):
    match = re.search(r'/p/([^/]+)|/reel/([^/]+)', url)
    if match:
        return match.group(1) or match.group(2)
    return None

@app.route('/download', methods=['GET'])
def download():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL obrigatória"}), 400

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
                'writeinfojson': True,
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            arquivos = []
            legenda = info.get('description', '') or info.get('title', '')
            tipo = 'Reels' if info.get('ext') == 'mp4' else 'Foto'

            for f in os.listdir(tmpdir):
                if f.endswith('.json'):
                    continue
                filepath = os.path.join(tmpdir, f)
                with open(filepath, 'rb') as file:
                    conteudo = base64.b64encode(file.read()).decode('utf-8')
                ext = f.split('.')[-1].lower()
                mime = 'video/mp4' if ext == 'mp4' else f'image/{ext}'
                arquivos.append({
                    "nome": f,
                    "ext": ext,
                    "mime": mime,
                    "base64": conteudo
                })

            if len(arquivos) > 1:
                tipo = 'Carrossel'

            return jsonify({
                "sucesso": True,
                "tipo": tipo,
                "legenda": legenda,
                "total_arquivos": len(arquivos),
                "arquivos": arquivos
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
