from datetime import datetime
from enum import Enum

from flask import request
from sqlalchemy import Enum as SQLAlchemyEnum

from app import db
import os


class PublicationType(Enum):
    NONE = "none"
    ANNOTATION_COLLECTION = "annotationcollection"
    BOOK = "book"
    BOOK_SECTION = "section"
    CONFERENCE_PAPER = "conferencepaper"
    DATA_MANAGEMENT_PLAN = "datamanagementplan"
    JOURNAL_ARTICLE = "article"
    PATENT = "patent"
    PREPRINT = "preprint"
    PROJECT_DELIVERABLE = "deliverable"
    PROJECT_MILESTONE = "milestone"
    PROPOSAL = "proposal"
    REPORT = "report"
    SOFTWARE_DOCUMENTATION = "softwaredocumentation"
    TAXONOMIC_TREATMENT = "taxonomictreatment"
    TECHNICAL_NOTE = "technicalnote"
    THESIS = "thesis"
    WORKING_PAPER = "workingpaper"
    OTHER = "other"


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    affiliation = db.Column(db.String(120))
    orcid = db.Column(db.String(120))
    ds_meta_data_id = db.Column(db.Integer, db.ForeignKey("ds_meta_data.id"))

    def to_dict(self):
        return {"name": self.name, "affiliation": self.affiliation, "orcid": self.orcid}

class DSMetaData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deposition_id = db.Column(db.Integer)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    publication_type = db.Column(SQLAlchemyEnum(PublicationType), nullable=False)
    publication_doi = db.Column(db.String(120))
    dataset_doi = db.Column(db.String(120))
    tags = db.Column(db.String(120))
    storage_service = db.Column(db.String(50), nullable=False, default="none")
    storage_record_url = db.Column(db.String(255))

    authors = db.relationship("Author", backref="ds_meta_data", lazy=True, cascade="all, delete")
    def generate_fake_doi_for_github(self, dataset_id: int) -> str:

        return f"10.9999/cervezahub.github.dataset.{dataset_id}"



class DataSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    ds_meta_data_id = db.Column(db.Integer, db.ForeignKey("ds_meta_data.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0, nullable=False)

    ds_meta_data = db.relationship("DSMetaData", backref=db.backref("data_set", uselist=False))
    
    csv_file_path = db.Column(db.String(500), nullable=True)
    row_count = db.Column(db.Integer)
    column_names = db.Column(db.Text)

    
    # El nombre se establece desde el servicio, usando el nombre del archivo CSV
    name = db.Column(db.String(255), nullable=True)


    def name(self):
        return self.ds_meta_data.title

    def files(self):
        if self.csv_file_path:
            return [self.csv_file_path]
        return []
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def get_cleaned_publication_type(self):
        return self.ds_meta_data.publication_type.name.replace("_", " ").title()

    def get_zenodo_url(self):
        return f"https://zenodo.org/record/{self.ds_meta_data.deposition_id}" if self.ds_meta_data.dataset_doi else None

    def get_storage_url(self):
        if getattr(self.ds_meta_data, "storage_record_url", None):
            return self.ds_meta_data.storage_record_url
        return self.get_zenodo_url()
    
    def get_files_count(self):
        return 1 if self.csv_file_path else 0

    def get_file_total_size(self):
        try:
            if self.csv_file_path and os.path.exists(self.csv_file_path):
                return os.path.getsize(self.csv_file_path)
        except Exception:
            pass
        return 0

    def get_file_total_size_for_human(self):
        from app.modules.dataset.services import SizeService

        return SizeService().get_human_readable_size(self.get_file_total_size())

    def get_uvlhub_doi(self):
        from app.modules.dataset.services import DataSetService

        return DataSetService().get_uvlhub_doi(self)

    def to_dict(self):
        return {
            "title": self.ds_meta_data.title,
            "id": self.id,
            "created_at": self.created_at,
            "created_at_timestamp": int(self.created_at.timestamp()),
            "description": self.ds_meta_data.description,
            "authors": [author.to_dict() for author in self.ds_meta_data.authors],
            "publication_type": self.get_cleaned_publication_type(),
            "publication_doi": self.ds_meta_data.publication_doi,
            "dataset_doi": self.ds_meta_data.dataset_doi,
            "tags": self.ds_meta_data.tags.split(",") if self.ds_meta_data.tags else [],
            "url": self.get_storage_url(),
            "download": f'{request.host_url.rstrip("/")}/dataset/download/{self.id}',

            # ANTIGUO (backwards compatible)
            "zenodo": self.get_zenodo_url(),

            # NUEVO
            "storage_service": getattr(self.ds_meta_data, "storage_service", "none") or "none",
            "storage_record_url": self.get_storage_url(),

            "files": [{
                "name": os.path.basename(self.csv_file_path) if self.csv_file_path else "N/A",
                "size_in_bytes": self.get_file_total_size()
            }] if self.csv_file_path else [],
            "files_count": self.get_files_count(),
            "total_size_in_bytes": self.get_file_total_size(),
            "total_size_in_human_format": self.get_file_total_size_for_human(),
            "download_count": self.download_count,
            "csv_metrics": {
                "row_count": self.row_count,
                "columns": self.column_names.split(',') if self.column_names else []
            }
        }


    def __repr__(self):
        return f"DataSet<{self.id}>"



community_dataset_association = db.Table(
    "community_dataset_association",
    db.Column("community_id", db.Integer, db.ForeignKey("community.id"), primary_key=True),
    db.Column("dataset_id", db.Integer, db.ForeignKey("data_set.id"), primary_key=True),
    db.Column("added_at", db.DateTime, default=datetime.utcnow),
)

class Community(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    logo_path = db.Column(db.String(255), nullable=True) 
    
    creator_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    datasets = db.relationship(
        "DataSet", secondary=community_dataset_association, backref=db.backref("communities", lazy="dynamic"), lazy="dynamic")

    def __repr__(self):
        return f"Community<{self.id} - {self.name}>"

class DSDownloadRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("data_set.id"))
    download_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    download_cookie = db.Column(db.String(36), nullable=False)  # Assuming UUID4 strings

    def __repr__(self):
        return (
            f"<Download id={self.id} "
            f"dataset_id={self.dataset_id} "
            f"date={self.download_date} "
            f"cookie={self.download_cookie}>"
        )


class DSViewRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("data_set.id"))
    view_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    view_cookie = db.Column(db.String(36), nullable=False)  # Assuming UUID4 strings

    def __repr__(self):
        return f"<View id={self.id} dataset_id={self.dataset_id} date={self.view_date} cookie={self.view_cookie}>"


class DOIMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dataset_doi_old = db.Column(db.String(120))
    dataset_doi_new = db.Column(db.String(120))
