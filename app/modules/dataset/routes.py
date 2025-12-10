
import logging
import os
import shutil
import tempfile
import uuid
import pandas as pd
from datetime import datetime, timezone, timedelta
from zipfile import ZipFile
from werkzeug.utils import secure_filename

from flask import (
    abort,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
    flash,
    current_app,
)
from flask_login import current_user, login_required

from app.modules.dataset import dataset_bp
from app import db
from app.modules.dataset.forms import DataSetForm, CommunityForm, CommunityDatasetForm
from app.modules.dataset.models import DSDownloadRecord, DSMetaData, DataSet, DSViewRecord, Author
from app.modules.dataset.services import (
    AuthorService,
    DataSetService,
    DOIMappingService,
    DSDownloadRecordService,
    DSMetaDataService,
    DSViewRecordService,
    CommunityService,
)
from app.modules.zenodo.services import ZenodoService

logger = logging.getLogger(__name__)


dataset_service = DataSetService()
author_service = AuthorService()
dsmetadata_service = DSMetaDataService()
zenodo_service = ZenodoService()
doi_mapping_service = DOIMappingService()
ds_view_record_service = DSViewRecordService()
community_service = CommunityService()

@dataset_bp.route("/dataset/upload", methods=["GET", "POST"])
@login_required 
def create_dataset():
    form = DataSetForm()
    
    if form.validate_on_submit():
        f = form.csv_file.data
        filename = secure_filename(f.filename)
        upload_to_zenodo = request.form.get('upload_to_zenodo') == 'true'
        
        try:
            # --- MANTENEMOS TU LÓGICA DE CSV (ORIGINAL DE ahh.txt) ---
            f.seek(0) 
            try:
                df = pd.read_csv(f, encoding='utf-8', sep=None, engine='python')
            except Exception:
                f.seek(0)
                df = pd.read_csv(f, encoding='latin-1', sep=None, engine='python')
            
            csv_row_count = len(df)
            csv_column_names = ','.join(list(df.columns))
            
            f.seek(0)
            
            metadata_dict = form.get_dsmetadata()
            meta_data = DSMetaData(**metadata_dict)
            
            authors_list = form.get_authors()
            for author_data in authors_list:
                meta_data.authors.append(Author(**author_data))
                
            dataset = DataSet(
                user_id=current_user.id,
                ds_meta_data=meta_data,
                row_count=csv_row_count,
                column_names=csv_column_names,
            )
            
            db.session.add(meta_data)
            db.session.add(dataset)
            db.session.commit() 

            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            dataset_folder = os.path.join(
                upload_folder, 
                f'user_{current_user.id}', 
                f'dataset_{dataset.id}'
            )
            os.makedirs(dataset_folder, exist_ok=True)
            file_path = os.path.join(dataset_folder, filename)
            f.save(file_path)

            dataset.csv_file_path = file_path
            db.session.commit()
            
            logger.info(f"CSV dataset created: {dataset.id}")

        except Exception as exc:
            db.session.rollback()
            logger.exception(f"Exception while creating local CSV dataset {exc}")
            flash(f"Error creating local dataset: {exc}", "danger")
            return render_template("dataset/upload_dataset.html", form=form)

        
        # --- AQUÍ EMPIEZAN LOS CAMBIOS BASADOS EN "ahh ellos.txt" ---
        # Objetivo: Usar la lógica limpia que recupera el DOI directamente de la respuesta
        # y eliminar el "hack" del DOI simulado manual.
        
        if upload_to_zenodo:
            try:
                # 1. Crear deposición (Igual que antes)
                zenodo_response_json = zenodo_service.create_new_deposition(dataset)
                data = json.loads(json.dumps(zenodo_response_json))
                
                if data.get("id"):
                    deposition_id = data.get("id")
                    dataset_service.update_dsmetadata(dataset.ds_meta_data_id, deposition_id=deposition_id)
                    logger.info(f"Uploading {file_path} to Zenodo (Deposition ID: {deposition_id})...")
                    
                    # 2. Subir archivo (Mantenemos tu lógica de CSV, 'ellos' usaban feature models)
                    zenodo_service.upload_file(dataset, deposition_id, file_path, filename)
                    
                    # 3. Publicar y OBTENER DOI (Lógica traída de 'ahh ellos.txt' )
                    # En lugar de llamar a get_doi() aparte, confiamos en la respuesta de publish
                    zenodo_response = zenodo_service.publish_deposition(deposition_id)
                    
                    doi = zenodo_response.get("doi")
                    
                    if doi:
                        dataset_service.update_dsmetadata(dataset.ds_meta_data_id, dataset_doi=doi)
                        logger.info(f"Dataset {dataset.id} published on Zenodo with DOI {doi}")
                        flash('Your Dataset has been uploaded and published on Zenodo!', 'success')
                    else:
                        # Fallback por si la respuesta no trae DOI (raro si es Zenodo/Fakenodo real)
                        logger.error(f"DOI not found in publish response for deposition {deposition_id}")
                        # Intentamos recuperarlo explícitamente como último recurso
                        deposition_doi = zenodo_service.get_doi(deposition_id)
                        if deposition_doi:
                             dataset_service.update_dsmetadata(dataset.ds_meta_data_id, dataset_doi=deposition_doi)
                             flash('Your Dataset has been uploaded and published on Zenodo!', 'success')
                        else:
                             flash('Dataset created locally, but DOI retrieval from Zenodo failed.', 'warning')

                else:
                    logger.error(f"Zenodo deposition creation failed for dataset {dataset.id}: {data}")
                    flash('Dataset created locally, but connection with Zenodo failed.', 'warning')        
            
            except Exception as exc:
                msg = f"Dataset created locally (id: {dataset.id}), but Zenodo synchronization failed: {exc}"
                logger.exception(msg)
                flash(msg, 'warning')
                
                # --- IMPORTANTE: HEMOS ELIMINADO EL BLOQUE DE "SIMULATED DOI" ---
                # Tus compañeros no tenían el bloque que empezaba con:
                # temp_id = str(uuid.uuid4()).split('-')[0] ...
                # Porque ahora confían en que Fakenodo haga su trabajo.

        # Refrescar para ver si tenemos DOI (ya sea real o de Fakenodo)
        db.session.refresh(dataset.ds_meta_data)
        final_doi = dataset.ds_meta_data.dataset_doi

        if final_doi:
            doi_only = final_doi.replace("https://doi.org/", "")
            return redirect(url_for('dataset.subdomain_index', doi=doi_only))
        else:
             return redirect(url_for('dataset.get_unsynchronized_dataset', dataset_id=dataset.id))
        
    return render_template("dataset/upload_dataset.html", form=form)

@dataset_bp.route("/dataset/list", methods=["GET", "POST"])
@login_required
def list_dataset():
    return render_template(
        "dataset/list_datasets.html",
        datasets=dataset_service.get_synchronized(current_user.id),
        local_datasets=dataset_service.get_unsynchronized(current_user.id),
    )


@dataset_bp.route("/dataset/file/upload", methods=["POST"])
@login_required
def upload():
    file = request.files["file"]
    temp_folder = current_user.temp_folder()

    if not file or not file.filename.endswith(".csv"):
        return jsonify({"message": "Invalid file. Only .csv allowed"}), 400

    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)
    file_path = os.path.join(temp_folder, file.filename)
    if os.path.exists(file_path):
        base_name, extension = os.path.splitext(file.filename)
        i = 1
        while os.path.exists(os.path.join(temp_folder, f"{base_name} ({i}){extension}")):
            i += 1
        new_filename = f"{base_name} ({i}){extension}"
        file_path = os.path.join(temp_folder, new_filename)
    else:
        new_filename = file.filename
    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({"message": str(e)}), 500

    return (
        jsonify(
            {
                "message": "CSV uploaded and validated successfully",
                "filename": new_filename,
            }
        ),
        200,
    )


@dataset_bp.route("/dataset/file/delete", methods=["POST"])
def delete():
    data = request.get_json()
    filename = data.get("file")
    temp_folder = current_user.temp_folder()
    filepath = os.path.join(temp_folder, filename)

    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"message": "File deleted successfully"})

    return jsonify({"error": "Error: File not found"})


@dataset_bp.route("/dataset/download/<int:dataset_id>", methods=["GET"])
def download_dataset(dataset_id):
    dataset = dataset_service.get_or_404(dataset_id)

    if not dataset.csv_file_path or not os.path.exists(dataset.csv_file_path):
        flash("Error: CSV file for this dataset not found.", "danger")
        try:
            doi_only = dataset.ds_meta_data.dataset_doi.replace("https://doi.org/", "")
            return redirect(url_for('dataset.subdomain_index', doi=doi_only))
        except Exception:
            return redirect(url_for('dataset.list_dataset'))

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, f"dataset_{dataset_id}.zip")

    with ZipFile(zip_path, "w") as zipf:
        filename = os.path.basename(dataset.csv_file_path)
        zipf.write(dataset.csv_file_path, arcname=filename)

    user_cookie = request.cookies.get("download_cookie")
    if not user_cookie:
        user_cookie = str(uuid.uuid4())
        resp = make_response(
            send_from_directory(
                temp_dir,
                f"dataset_{dataset_id}.zip",
                as_attachment=True,
                mimetype="application/zip",
            )
        )
        resp.set_cookie("download_cookie", user_cookie)
    else:
        resp = send_from_directory(
            temp_dir,
            f"dataset_{dataset_id}.zip",
            as_attachment=True,
            mimetype="application/zip",
        )

    existing_record = DSDownloadRecord.query.filter_by(
        user_id=current_user.id if current_user.is_authenticated else None,
        dataset_id=dataset_id,
        download_cookie=user_cookie,
    ).first()

    if not existing_record:
        DSDownloadRecordService().create(
            user_id=current_user.id if current_user.is_authenticated else None,
            dataset_id=dataset_id,
            download_date=datetime.now(timezone.utc),
            download_cookie=user_cookie,
        )
        
        try:
            dataset.download_count += 1
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error incrementing download counter: {e}")

    return resp


@dataset_bp.route("/dataset/<int:dataset_id>/stats", methods=["GET"])
def get_dataset_stats(dataset_id):
    dataset = dataset_service.get_or_404(dataset_id)

    total_views = DSViewRecord.query.filter_by(dataset_id=dataset_id).count()
    total_downloads = dataset.download_count
    dataset_age_in_days = (datetime.now(timezone.utc).replace(tzinfo=None) - dataset.created_at).days
    authors_number = len(dataset.ds_meta_data.authors)
    filas_count = dataset.row_count or 0
    columnas_count = len(dataset.column_names.split(',')) if dataset.column_names else 0
    seven_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    download_rate = 0
    if total_views > 0:
        download_rate = round((total_downloads / total_views) * 100, 2)
    views_last_week = DSViewRecord.query.filter(
        DSViewRecord.dataset_id == dataset_id,
        DSViewRecord.view_date >= seven_days_ago).count()
    downloads_last_week = DSDownloadRecord.query.filter(
        DSDownloadRecord.dataset_id == dataset_id,
        DSDownloadRecord.download_date >= seven_days_ago).count()

    return render_template(
        "dataset/statistics.html",
        dataset=dataset,
        total_views=total_views,
        total_downloads=total_downloads,
        dataset_age_in_days=dataset_age_in_days,
        authors_number=authors_number,
        filas_count=filas_count,
        columnas_count=columnas_count,
        download_rate=download_rate,
        views_last_week=views_last_week,
        downloads_last_week=downloads_last_week
    )


@dataset_bp.route("/doi/<path:doi>/", methods=["GET"])
def subdomain_index(doi):
    new_doi = doi_mapping_service.get_new_doi(doi)
    if new_doi:
        return redirect(url_for("dataset.subdomain_index", doi=new_doi), code=302)

    ds_meta_data = dsmetadata_service.filter_by_doi(doi)
    if not ds_meta_data:
        abort(404)

    dataset = ds_meta_data.data_set
    if not dataset:
        logger.error(f"No DataSet found for metadata with DOI {doi}")
        abort(404)

    user_cookie = None 
    try:
        user_cookie = request.cookies.get("view_cookie")
        if not user_cookie:
            user_cookie = str(uuid.uuid4())
        
        existing_record = DSViewRecord.query.filter_by(
            user_id=current_user.id if current_user.is_authenticated else None,
            dataset_id=dataset.id,
            view_cookie=user_cookie,
        ).first()

        if not existing_record:
            ds_view_record_service.create( 
                user_id=current_user.id if current_user.is_authenticated else None,
                dataset_id=dataset.id,
                view_date=datetime.now(timezone.utc),
                view_cookie=user_cookie,
            )
    except Exception as e:
        logger.warning(f"Could not save view record for dataset {dataset.id}: {e}")


    csv_header = []
    csv_preview = []
    try:
        if dataset.csv_file_path and os.path.exists(dataset.csv_file_path):
            try:
                df = pd.read_csv(dataset.csv_file_path, encoding='utf-8', sep=None, engine='python')
            except Exception:
                df = pd.read_csv(dataset.csv_file_path, encoding='latin-1', sep=None, engine='python')
            
            csv_header = df.columns.tolist()
            csv_preview = df.head(10).values.tolist()
    except Exception as e:
        logger.exception(f"CSV preview generation failed for {dataset.id}: {e}")
        pass 
    
    resp = make_response(render_template(
        "dataset/view_dataset.html", 
        dataset=dataset,
        csv_header=csv_header,   
        csv_preview=csv_preview   
    ))
    
    if user_cookie:
        resp.set_cookie("view_cookie", user_cookie) 

    return resp


@dataset_bp.route("/dataset/unsynchronized/<int:dataset_id>/", methods=["GET"])
@login_required
def get_unsynchronized_dataset(dataset_id):
    
    dataset = dataset_service.get_or_404(dataset_id)
    if not dataset:
        abort(404)
        
    if dataset.ds_meta_data.dataset_doi:
        doi_only = dataset.ds_meta_data.dataset_doi.replace("https://doi.org/", "")
        return redirect(url_for('dataset.subdomain_index', doi=doi_only), code=301)

    user_cookie = None 
    try:
        user_cookie = request.cookies.get("view_cookie")
        if not user_cookie:
            user_cookie = str(uuid.uuid4())
        
        existing_record = DSViewRecord.query.filter_by(
            user_id=current_user.id if current_user.is_authenticated else None,
            dataset_id=dataset.id,
            view_cookie=user_cookie,
        ).first()

        if not existing_record:
            ds_view_record_service.create( 
                user_id=current_user.id if current_user.is_authenticated else None,
                dataset_id=dataset.id,
                view_date=datetime.now(timezone.utc),
                view_cookie=user_cookie,
            )
    except Exception as e:
        logger.warning(f"Could not save view record for dataset {dataset.id}: {e}")
 

    csv_header = []
    csv_preview = []
    try:
        if dataset.csv_file_path and os.path.exists(dataset.csv_file_path):
            try:
                df = pd.read_csv(dataset.csv_file_path, encoding='utf-8', sep=None, engine='python')
            except Exception:
                df = pd.read_csv(dataset.csv_file_path, encoding='latin-1', sep=None, engine='python')

            csv_header = df.columns.tolist()
            csv_preview = df.head(10).values.tolist()
    except Exception as e:
        logger.exception(f"CSV preview generation failed for {dataset.id}: {e}")
        pass 

    resp = make_response(render_template(
        "dataset/view_dataset.html", 
        dataset=dataset,
        csv_header=csv_header,     
        csv_preview=csv_preview    
    ))
    
    if user_cookie: 
        resp.set_cookie("view_cookie", user_cookie)
    return resp


@dataset_bp.route("/community/create", methods=["GET", "POST"])
@login_required
def create_community():
    form = CommunityForm()
    if form.validate_on_submit():

        logo_file = request.files.get("logo")
        if logo_file and logo_file.filename != '':
            try:
                if not form.logo.validate(form, extra_validators=form.logo.validators):
                    if not form.logo.errors:
                        form.logo.errors.append("Logo file type not allowed.")
                    pass 

            except Exception:
                form.logo.errors.append("Error processing logo file.")
                pass
                
        else:
            logo_file = None 
        if not form.errors:
            try:
                community = community_service.create_from_form(
                    form=form, 
                    current_user=current_user, 
                    logo_file=logo_file
                )
                return redirect(url_for('dataset.view_community', community_id=community.id))

            except Exception as exc:
                logger.exception(f"Exception while creating community: {exc}")
                form.name.errors.append("A community with this name already exists. Please choose another.")
                
    return render_template("community/create_community.html", form=form)


@dataset_bp.route("/community/<int:community_id>/", methods=["GET"])
def view_community(community_id):
    community = community_service.get_or_404(community_id)
    return render_template("community/view_community.html", community=community)


@dataset_bp.route("/communities/", methods=["GET"])
def list_communities():
    """Shows a list of all created communities."""
    
    try:
        communities = community_service.get_all_communities()
        
        return render_template("community/list_communities.html", communities=communities)
        
    except Exception as exc:
        logger.exception(f"Exception while listing communities: {exc}")
        return jsonify({"Error": "Could not load the communities list."}), 500
    
    
@dataset_bp.route("/community/<int:community_id>/logo", methods=["GET"])
def serve_community_logo(community_id):

    community = community_service.get_or_404(community_id)
    full_path = community.logo_path
    
    if not full_path or not os.path.exists(full_path):
        return redirect(url_for('static', filename='images/default_community_logo.png'))

    working_dir = os.getenv("WORKING_DIR", os.path.join(os.getcwd(), "tmp_uploads")) 
    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path) 
    
    return send_from_directory(directory, filename)


@dataset_bp.route("/community/<int:community_id>/manage_datasets", methods=["GET", "POST"])
@login_required 
def manage_community_datasets(community_id):

    community = community_service.get_or_404(community_id)
    form = CommunityDatasetForm()
    all_datasets = DataSet.query.order_by(DataSet.created_at.desc()).all()
    dataset_choices = [(str(ds.id), f"{ds.name()} (ID: {ds.id})") for ds in all_datasets] 
    form.datasets.choices = dataset_choices 

    if form.validate_on_submit():

        try:
            selected_dataset_ids = form.datasets.data 
            selected_datasets = DataSet.query.filter(DataSet.id.in_(selected_dataset_ids)).all()

            community_service.update_datasets(community.id, selected_datasets)

            flash(f"Datasets updated for community '{community.name}'.", 'success')
            return redirect(url_for('dataset.view_community', community_id=community.id))
        
        except Exception as exc:
            community_service.repository.session.rollback() 
            flash('Error saving dataset relationship.', 'danger')

    elif request.method == 'GET':
        current_dataset_ids = [str(ds.id) for ds in community.datasets] 
        form.datasets.data = current_dataset_ids
    
    return render_template("community/manage_datasets.html", 
                           community=community, 
                           form=form)
