from flask import Flask, request, jsonify
import os
import tempfile
import base64
import re
import instaloader

app = Flask(__name__)

IG_USER = os.environ.get('IG_USER', '')
IG_PASS = os.environ.get('IG_PASS', '')

def get_loader(tmpdir):
    L = instaloader.Instaloader(
        dirname_pattern=tmpdir,
        filename_pattern="{shortcode}_{typename}_{mediaid}",
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
        quiet=True
    )
    if IG_USER and IG_PASS:
        try:
            L.login(IG_USER, IG_PASS)
        except Exception as e:
            print(f"Login failed: {e}")
    return L

def extrair_shortcode(url):
    match = re.search(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)', url)
    return match.group(1) if match else None

@app.route('/download', methods=['GET'])
def download():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL obrigatória"}), 400

    shortcode = extrair_shortcode(url)
    if not shortcode:
        return jsonify({"error": "Shortcode não encontrado na URL"}), 400

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            L = get_loader(tmpdir)
            post = instaloader.Post.from_shortcode(L.context, shortcode)

            legenda = post.caption or ''
            tipo = 'Foto'
            arquivos = []

            if post.typename == 'GraphSidecar':
                tipo = 'Carrossel'
                for i, node in enumerate(post.get_sidecar_nodes()):
                    if node.is_video:
                        ext = 'mp4'
                        mime = 'video/mp4'
                        fname = os.path.join(tmpdir, f'slide_{i+1}.mp4')
                        L.download_pic(fname, node.video_url, post.date_utc)
                    else:
                        ext = 'jpg'
                        mime = 'image/jpeg'
                        fname = os.path.join(tmpdir, f'slide_{i+1}.jpg')
                        L.download_pic(fname, node.display_url, post.date_utc)

                    if os.path.exists(fname):
                        with open(fname, 'rb') as f:
                            arquivos.append({
                                "nome": os.path.basename(fname),
                                "ext": ext,
                                "mime": mime,
                                "base64": base64.b64encode(f.read()).decode('utf-8')
                            })

            elif post.is_video:
                tipo = 'Reels'
                fname = os.path.join(tmpdir, 'video.mp4')
                L.download_pic(fname, post.video_url, post.date_utc)
                if os.path.exists(fname):
                    with open(fname, 'rb') as f:
                        arquivos.append({
                            "nome": "video.mp4",
                            "ext": "mp4",
                            "mime": "video/mp4",
                            "base64": base64.b64encode(f.read()).decode('utf-8')
                        })
            else:
                tipo = 'Foto'
                fname = os.path.join(tmpdir, 'foto.jpg')
                L.download_pic(fname, post.url, post.date_utc)
                if os.path.exists(fname):
                    with open(fname, 'rb') as f:
                        arquivos.append({
                            "nome": "foto.jpg",
                            "ext": "jpg",
                            "mime": "image/jpeg",
                            "base64": base64.b64encode(f.read()).decode('utf-8')
                        })

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
