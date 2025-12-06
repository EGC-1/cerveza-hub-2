from flask import Flask, jsonify, request, render_template_string
import datetime
import sys

app = Flask(__name__)
DEPOSITS = {}

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Fakenodo Record {{ id }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f4f4f4; padding-top: 40px; }
        .header-zenodo { background-color: #0069d9; color: white; padding: 15px; margin-bottom: 20px; }
        .doi-badge { background-color: #ffc107; color: #000; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card shadow-sm">
            <div class="header-zenodo rounded-top">
                <h3 class="m-0">Fakenodo Repository</h3>
            </div>
            <div class="card-body">
                <span class="badge bg-success mb-2">Published</span>
                <h1 class="card-title mt-2">{{ metadata.get('title', 'Untitled') }}</h1>
                <p class="text-muted">Uploaded on {{ created }}</p>
                <hr>
                <h5>Description</h5>
                <p>{{ metadata.get('description', 'No description') | safe }}</p>
                <div class="alert alert-light border mt-4">
                    <strong>DOI:</strong> <span class="doi-badge">{{ doi }}</span>
                </div>
                <h5 class="mt-4">Files</h5>
                <ul class="list-group">
                {% for file in files %}
                    <li class="list-group-item">📄 {{ file.filename }}</li>
                {% endfor %}
                </ul>
            </div>
            <div class="card-footer text-center text-muted">Fakenodo Local Server :5000</div>
        </div>
    </div>
</body>
</html>
"""

# --- API ENDPOINTS ---

@app.route('/api/deposit/depositions', methods=['POST'])
def create_deposit():
    print(f"FAKENODO: Creando depósito...", file=sys.stderr)
    new_id = str(len(DEPOSITS) + 1000)
    
    # Recibimos metadata
    meta = request.json.get('metadata', {})
    
    record = {
        "id": int(new_id),
        "metadata": meta,
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
    print(f"FAKENODO: Depósito {new_id} creado con éxito.", file=sys.stderr)
    return jsonify(record), 201

@app.route('/api/deposit/depositions/<id>', methods=['GET'])
def get_deposit(id):
    if id not in DEPOSITS: return jsonify({"message": "Not found"}), 404
    return jsonify(DEPOSITS[id]), 200

@app.route('/api/deposit/depositions/<id>/files', methods=['POST'])
def upload_file(id):
    print(f"FAKENODO: Intentando subir archivo al ID {id}...", file=sys.stderr)
    
    if id not in DEPOSITS: 
        print("FAKENODO: ID no encontrado", file=sys.stderr)
        return jsonify({"message": "Not found"}), 404
    
    # Validación robusta del archivo
    if 'file' not in request.files:
        print("FAKENODO: No se recibió la key 'file' en la petición", file=sys.stderr)
        return jsonify({"message": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        print("FAKENODO: Nombre de archivo vacío", file=sys.stderr)
        return jsonify({"message": "No selected file"}), 400

    filename = file.filename
    DEPOSITS[id]['files'].append({"filename": filename, "checksum": "md5:fake"})
    
    print(f"FAKENODO: Archivo {filename} subido correctamente.", file=sys.stderr)
    return jsonify({"key": filename}), 201

@app.route('/api/deposit/depositions/<id>/actions/publish', methods=['POST'])
def publish(id):
    print(f"FAKENODO: Publicando ID {id}...", file=sys.stderr)
    if id not in DEPOSITS: return jsonify({"message": "Not found"}), 404
    
    DEPOSITS[id]['submitted'] = True
    if not DEPOSITS[id]['doi']:
        DEPOSITS[id]['doi'] = f"10.5281/zenodo.{id}"
        
    print(f"FAKENODO: Publicado con DOI {DEPOSITS[id]['doi']}", file=sys.stderr)
    return jsonify(DEPOSITS[id]), 202

# --- VISTA WEB ---
@app.route('/records/<id>', methods=['GET'])
def view_record_html(id):
    if id not in DEPOSITS:
        return "<h1>404 - Record Not Found</h1>", 404
    rec = DEPOSITS[id]
    return render_template_string(HTML_TEMPLATE, 
                                  id=id, 
                                  metadata=rec['metadata'], 
                                  doi=rec['doi'], 
                                  created=rec['created'], 
                                  files=rec['files'])

if __name__ == '__main__':
    # Debug=True ayuda a ver errores si explota
    app.run(host='0.0.0.0', port=5000, debug=True)