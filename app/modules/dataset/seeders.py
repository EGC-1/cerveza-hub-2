import os
import shutil
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

from app.modules.auth.models import User
from app.modules.dataset.models import Author, DataSet, DSMetaData, PublicationType
from core.seeders.BaseSeeder import BaseSeeder

logger = logging.getLogger(__name__)

DUMMY_CSV_CONTENT = """brand,type,abv,country
Estrella Galicia,Lager,5.5,Spain
Mahou Cinco Estrellas,Lager,5.5,Spain
Cruzcampo,Pilsner,4.8,Spain
Voll-Damm,Märzen,7.2,Spain
"""
DUMMY_CSV_FILENAME = "spanish_beers.csv"
DUMMY_ROW_COUNT = 4
DUMMY_COLUMN_NAMES = "brand,type,abv,country"


class DataSetSeeder(BaseSeeder):

    priority = 2

    def run(self):
        logger.info("Iniciando Seeder de DataSet para CervezaCsvHub...")
        
        # 1. Recuperar usuarios
        user1 = User.query.filter_by(email="user1@example.com").first()
        user2 = User.query.filter_by(email="user2@example.com").first()

        if not user1 or not user2:
            logger.error("Usuarios no encontrados. Por favor, ejecuta el UserSeeder primero.")
            raise Exception("Users not found. Please seed users first.")

        # 3. Crear DSMetaData (sin métricas de UVL)
        ds_meta_data_list = [
            DSMetaData(
                deposition_id=12345,
                title="Spanish Beers Sample",
                description="Un conjunto de datos CSV de cervezas populares de España.",
                publication_type=PublicationType.NONE,
                publication_doi="10.1234/cerveza.1",
                dataset_doi="10.5281/zenodo.12345", # DOI de ejemplo
                tags="cerveza, españa, lager",
                
            ),
            DSMetaData(
                deposition_id=67890,
                title="Local Test Dataset",
                description="Un dataset local sin sincronizar con Zenodo.",
                publication_type=PublicationType.NONE,
                publication_doi=None,
                dataset_doi=None, # Sin DOI
                tags="test, local",
            ),
        ]
        seeded_ds_meta_data = self.seed(ds_meta_data_list)

        # 4. Crear Autores
        authors = [
            Author(
                name="Lidia Cervezas",
                affiliation="Universidad de CervezaHub",
                orcid="0000-0000-0000-0001",
                ds_meta_data_id=seeded_ds_meta_data[0].id,
            ),
             Author(
                name="Admin User",
                affiliation="Local Testing",
                orcid="0000-0000-0000-0002",
                ds_meta_data_id=seeded_ds_meta_data[1].id,
            )
        ]
        self.seed(authors)

        # 5. Crear DataSet (con los nuevos campos CSV)
        datasets = [
            DataSet(
                user_id=user1.id,
                ds_meta_data_id=seeded_ds_meta_data[0].id,
                created_at=datetime.now(timezone.utc),
                download_count=0, 
            
                row_count=DUMMY_ROW_COUNT,
                column_names=DUMMY_COLUMN_NAMES,
                csv_file_path=None 
            ),
            DataSet(
                user_id=user2.id,
                ds_meta_data_id=seeded_ds_meta_data[1].id,
                created_at=datetime.now(timezone.utc),
                download_count=0,
              
                row_count=DUMMY_ROW_COUNT,
                column_names=DUMMY_COLUMN_NAMES,
                csv_file_path=None 
            )
        ]
        seeded_datasets = self.seed(datasets)
        
        load_dotenv()
        working_dir = os.getenv("WORKING_DIR", os.getcwd())
        
        for dataset in seeded_datasets:
            try:
                
                dest_folder = os.path.join(working_dir, "uploads", f"user_{dataset.user_id}", f"dataset_{dataset.id}")
                os.makedirs(dest_folder, exist_ok=True)
                
                file_path = os.path.join(dest_folder, DUMMY_CSV_FILENAME)
                with open(file_path, "w") as f:
                    f.write(DUMMY_CSV_CONTENT)
                
             
                dataset.csv_file_path = file_path
                self.db.session.commit()
                
                logger.info(f"Creado archivo CSV de prueba en: {file_path}")

            except Exception as e:
                logger.error(f"Fallo al crear el archivo CSV de prueba para el dataset {dataset.id}: {e}")
                self.db.session.rollback()

        logger.info("DataSetSeeder para CervezaCsvHub completado.")