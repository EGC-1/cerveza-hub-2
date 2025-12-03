from flask import Flask, jsonify, request, render_template_string
import datetime

app = Flask(__name__)
DEPOSITS = {}

# --- HTML TEMPLATE (Para que se vea bonito) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fakenodo Record {{ id }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f4f4f4; padding-top: 40px; }
        .header-zenodo { background-color: #0069d9; color: white; padding: 15px; margin-bottom: 20px; }
        .doi-badge { background-color: #ffc107; color: #000; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
        .file-box { background: white; border: 1px solid #ddd; padding: 15px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card shadow-sm">
            <div class="header-zenodo rounded-top">
                <h3 class="m-0">Fakenodo Repository (Simulation)</h3>
            </div>
            <div class="card-body">
                <span class="badge bg-secondary mb-2">Open Access</span>
                <span class="badge bg-success mb-2">Published</span>
                
                <h1 class="card-title mt-2">{{ metadata.get('title', 'Untitled') }}</h1>
                <p class="text-muted">Uploaded on {{ created }}</p>

                <hr>

                <h5>Description</h5>
                <p class="card-text">{{ metadata.get('description', 'No description provided.') }}</p>

                <div class="alert alert-light border mt-4">
                    <strong>DOI:</strong> <span class="doi-badge">{{ doi }}</span>
                    <br><small class="text-muted">This is a simulated DOI.</small>
                </div>

                <h5 class="mt-4">Files</h5>
                <div class="file-box">
                    {% if files %}
                        <ul class="list-group list-group-flush">
                        {% for file in files %}
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                📄 {{ file.filename }}
                                <span class="badge bg-primary rounded-pill">Download</span>
                            </li>
                        {% endfor %}
                        </ul>
                    {% else %}
                        <p class="text-muted m-0">No files uploaded.</p>
                    {% endif %}
                </div>
            </div>
            <div class="card-footer text-center text-muted">
                <small>Running on Fakenodo Local Server - Port 5000</small>
            </div>
        </div>
    </div>
</body>
</html>
"""

# --- RUTAS DE API (Para las máquinas - JSON) ---

@app.route('/api/deposit/depositions', methods=['POST'])
def create_deposit():
    new_id = str(len(DEPOSITS) + 1000)
    record = {
        "id": int(new_id),
        "metadata": request.json.get('metadata', {}),
        "state": "unsubmitted",
        "submitted": False,
        "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files": [],
        "links": {
            "bucket": f"http://fakenodo:5000/api/files/{new_id}",
            "publish": f"http://fakenodo:5000/api/deposit/depositions/{new_id}/actions/publish",
            "self": f"http://fakenodo:5000/api/deposit/depositions/{new_id}"
        },
        "doi": "",
        "conceptdoi": f"10.5281/zenodo.{int(new_id)-1}"
    }
    DEPOSITS[new_id] = record
    return jsonify(record), 201

@app.route('/api/deposit/depositions/<id>', methods=['GET'])
def get_deposit(id):
    return jsonify(DEPOSITS.get(id, {"message": "Not found"})), 200 if id in DEPOSITS else 404

@app.route('/api/deposit/depositions/<id>/files', methods=['POST'])
def upload_file(id):
    if id not in DEPOSITS: return jsonify({"message": "Not found"}), 404
    filename = request.files['file'].filename
    DEPOSITS[id]['files'].append({"filename": filename, "checksum": "md5:fake"})
    return jsonify({"key": filename}), 201

@app.route('/api/deposit/depositions/<id>/actions/publish', methods=['POST'])
def publish(id):
    if id not in DEPOSITS: return jsonify({"message": "Not found"}), 404
    DEPOSITS[id]['submitted'] = True
    if not DEPOSITS[id]['doi']:
        DEPOSITS[id]['doi'] = f"10.5281/zenodo.{id}"
    return jsonify(DEPOSITS[id]), 202

# --- RUTA VISUAL (Para ti - HTML) ---

@app.route('/records/<id>', methods=['GET'])
def view_record_html(id):
    """Muestra una página web bonita simulando Zenodo"""
    if id not in DEPOSITS:
        return "<h1>404 - Record Not Found in Fakenodo</h1>", 404
    
    record = DEPOSITS[id]
    return render_template_string(HTML_TEMPLATE, 
                                  id=id, 
                                  metadata=record['metadata'], 
                                  doi=record['doi'],
                                  created=record['created'],
                                  files=record['files'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  