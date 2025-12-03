from flask import Flask, jsonify, request

app = Flask(__name__)
DEPOSITS = {}

@app.route('/api/deposit/depositions', methods=['POST'])
def create_deposit():
    new_id = str(len(DEPOSITS) + 1000)
    record = {
        "id": int(new_id),
        "metadata": request.json.get('metadata', {}),
        "state": "unsubmitted",
        "submitted": False,
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)