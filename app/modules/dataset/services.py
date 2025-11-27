import hashlib
import logging
import os
import shutil
import uuid
from typing import Optional

from flask import request

from app.modules.auth.services import AuthenticationService
from app.modules.dataset.models import DataSet, DSMetaData, DSViewRecord, Community
from app.modules.dataset.repositories import (
    AuthorRepository,
    DataSetRepository,
    DOIMappingRepository,
    DSDownloadRecordRepository,
    DSMetaDataRepository,
    DSViewRecordRepository,
    CommunityRepository,
)

from core.services.BaseService import BaseService
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

class CommunityService(BaseService):
    def __init__(self):
        super().__init__(CommunityRepository())

    def create_from_form(self, form, current_user, logo_file) -> Community:
        try:
            community = self.repository.create(
                commit=False, 
                creator_user_id=current_user.id, 
                **form.get_community_data()
            )
            
            self.repository.session.add(community)
            self.repository.session.flush() 


            if logo_file and logo_file.filename != '':
                working_dir = os.getenv("WORKING_DIR", os.path.join(os.getcwd(), "tmp_uploads")) 
                
                original_filename = secure_filename(logo_file.filename)

                filename_extension = os.path.splitext(original_filename)[1] 
                logo_filename = f"{community.id}_{original_filename}" 

    
                logo_dest_dir = os.path.join(working_dir, "community_logos", str(community.id))
                os.makedirs(logo_dest_dir, exist_ok=True)
                
                logo_path = os.path.join(logo_dest_dir, logo_filename) 
                logo_file.save(logo_path)
                community.logo_path = logo_path 
                
            self.repository.session.commit()
            logger.info(f"Comunidad '{community.name}' creada por usuario {current_user.id}.")
            return community
        except Exception as exc:
            self.repository.session.rollback()
            logger.exception(f"Error al crear la comunidad: {exc}")
            raise exc
    def get_all_communities(self):
        return self.repository.get_all_ordered_by_creation()
    
    def update_datasets(self, community_id, new_datasets):
        community = self.get_or_404(community_id)
        community.datasets = new_datasets 
        self.repository.session.commit()
    
def calculate_checksum_and_size(file_path):
    file_size = os.path.getsize(file_path)
    with open(file_path, "rb") as file:
        content = file.read()
        hash_md5 = hashlib.md5(content).hexdigest()
        return hash_md5, file_size


class DataSetService(BaseService):
    def __init__(self):
        super().__init__(DataSetRepository())
        self.author_repository = AuthorRepository()
        self.dsmetadata_repository = DSMetaDataRepository()
        self.dsdownloadrecord_repository = DSDownloadRecordRepository()
        self.dsviewrecord_repostory = DSViewRecordRepository()

    
    def get_synchronized(self, current_user_id: int) -> DataSet:
        return self.repository.get_synchronized(current_user_id)

    def get_unsynchronized(self, current_user_id: int) -> DataSet:
        return self.repository.get_unsynchronized(current_user_id)

    def get_unsynchronized_dataset(self, current_user_id: int, dataset_id: int) -> DataSet:
        return self.repository.get_unsynchronized_dataset(current_user_id, dataset_id)

    def latest_synchronized(self):
        return self.repository.latest_synchronized()

    def count_synchronized_datasets(self):
        return self.repository.count_synchronized_datasets()

    def count_authors(self) -> int:
        return self.author_repository.count()

    def count_dsmetadata(self) -> int:
        return self.dsmetadata_repository.count()

    def total_dataset_downloads(self) -> int:
        return self.dsdownloadrecord_repository.total_dataset_downloads()

    def total_dataset_views(self) -> int:
        return self.dsviewrecord_repostory.total_dataset_views()

    def create_from_form(self, form, current_user) -> DataSet:
        main_author = {
            "name": f"{current_user.profile.surname}, {current_user.profile.name}",
            "affiliation": current_user.profile.affiliation,
            "orcid": current_user.profile.orcid,
        }
        try:
            # 1. Crear DSMetaData y Autores
            logger.info(f"Creating dsmetadata...: {form.get_dsmetadata()}")
            dsmetadata = self.dsmetadata_repository.create(**form.get_dsmetadata())
            for author_data in [main_author] + form.get_authors():
                author = self.author_repository.create(commit=False, ds_meta_data_id=dsmetadata.id, **author_data)
                dsmetadata.authors.append(author)

            # 2. Crear DataSet (padre) y hacer flush para obtener el ID necesario para la carpeta
            dataset = self.create(commit=False, user_id=current_user.id, ds_meta_data_id=dsmetadata.id)
            self.repository.session.flush()

            # 3. MANEJAR SUBIDA DE ARCHIVO CSV (NUEVA LÓGICA)
            csv_file_data = form.csv_file.data
            if csv_file_data and csv_file_data.filename:
                
                # Definir la ruta de almacenamiento
                working_dir = os.getenv("WORKING_DIR", os.path.join(os.getcwd(), "tmp_uploads"))
                dataset_upload_dir = os.path.join(working_dir, "datasets", str(dataset.id))
                os.makedirs(dataset_upload_dir, exist_ok=True)
                
                # Asegurar el nombre del archivo y la ruta completa
                filename = secure_filename(csv_file_data.filename)
                csv_file_path = os.path.join(dataset_upload_dir, filename)

                # Guardar el archivo en el disco
                csv_file_data.seek(0)
                csv_file_data.save(csv_file_path)
                
                # Calcular Checksum y Tamaño
                checksum, size = calculate_checksum_and_size(csv_file_path)

                # Actualizar el objeto DataSet con la metadata del archivo CSV
                dataset.csv_file_path = csv_file_path
                dataset.checksum = checksum
                dataset.size = size
                # Se establece el nombre del dataset basado en el nombre del archivo subido
                dataset.name = filename 
            # FIN MANEJO CSV

            self.repository.session.commit()
        except Exception as exc:
            logger.info(f"Exception creating dataset from form...: {exc}")
            # Si la subida falla, limpiamos la sesión
            self.repository.session.rollback()
            # para no registrar el dataset en la DB.
            raise exc
        return dataset


    def update_dsmetadata(self, id, **kwargs):
        return self.dsmetadata_repository.update(id, **kwargs)

    def get_uvlhub_doi(self, dataset: DataSet) -> str:
        domain = os.getenv("DOMAIN", "localhost")
        return f"http://{domain}/doi/{dataset.ds_meta_data.dataset_doi}"


class AuthorService(BaseService):
    def __init__(self):
        super().__init__(AuthorRepository())


class DSDownloadRecordService(BaseService):
    def __init__(self):
        super().__init__(DSDownloadRecordRepository())


class DSMetaDataService(BaseService):
    def __init__(self):
        super().__init__(DSMetaDataRepository())

    def update(self, id, **kwargs):
        return self.repository.update(id, **kwargs)

    def filter_by_doi(self, doi: str) -> Optional[DSMetaData]:
        return self.repository.filter_by_doi(doi)


class DSViewRecordService(BaseService):
    def __init__(self):
        super().__init__(DSViewRecordRepository())

    def the_record_exists(self, dataset: DataSet, user_cookie: str):
        return self.repository.the_record_exists(dataset, user_cookie)

    def create_new_record(self, dataset: DataSet, user_cookie: str) -> DSViewRecord:
        return self.repository.create_new_record(dataset, user_cookie)

    def create_cookie(self, dataset: DataSet) -> str:

        user_cookie = request.cookies.get("view_cookie")
        if not user_cookie:
            user_cookie = str(uuid.uuid4())

        existing_record = self.the_record_exists(dataset=dataset, user_cookie=user_cookie)

        if not existing_record:
            self.create_new_record(dataset=dataset, user_cookie=user_cookie)

        return user_cookie


class DOIMappingService(BaseService):
    def __init__(self):
        super().__init__(DOIMappingRepository())

    def get_new_doi(self, old_doi: str) -> str:
        doi_mapping = self.repository.get_new_doi(old_doi)
        if doi_mapping:
            return doi_mapping.dataset_doi_new
        else:
            return None


class SizeService:

    def __init__(self):
        pass

    def get_human_readable_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024**2:
            return f"{round(size / 1024, 2)} KB"
        elif size < 1024**3:
            return f"{round(size / (1024 ** 2), 2)} MB"
        else:
            return f"{round(size / (1024 ** 3), 2)} GB"
