from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, SelectField, StringField, ValidationError, SelectMultipleField, SubmitField, TextAreaField
from wtforms.validators import URL, DataRequired, Optional, Length
from flask_wtf.file import FileField, FileAllowed, FileRequired
from app.modules.dataset.models import PublicationType, DataSet, Community

class CommunityDatasetForm(FlaskForm):

    datasets = SelectMultipleField(
        label='Datasets Disponibles',
        description="Mantén presionada Ctrl/Cmd para seleccionar múltiples datasets."
    )
    submit = SubmitField('Guardar Datasets')
class AuthorForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    affiliation = StringField("Affiliation")
    orcid = StringField("ORCID")
    gnd = StringField("GND")

    class Meta:
        csrf = False  # disable CSRF because is subform

    def get_author(self):
        return {
            "name": self.name.data,
            "affiliation": self.affiliation.data,
            "orcid": self.orcid.data,
        }

class CommunityForm(FlaskForm):
    name = StringField(
        "Nombre de la Comunidad", 
        validators=[DataRequired(message="El nombre es obligatorio."), Length(min=5, max=120)]
    )
    description = TextAreaField(
        "Descripción", 
        validators=[DataRequired(message="La descripción es obligatoria.")]
    )
    logo = FileField(
        "Logo de la Comunidad", 
        validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Solo se permiten imágenes JPG, JPEG o PNG!')] 
    )
    submit = SubmitField("Crear Comunidad")
    
    def get_community_data(self):
        """Retorna los datos de texto del formulario."""
        return {
            "name": self.name.data,
            "description": self.description.data,
        }
    def validate_name(self, name):
        if Community.query.filter_by(name=name.data).first():
            raise ValidationError('Ya existe una comunidad con este nombre. Por favor, elige otro.')

class DataSetForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    desc = TextAreaField("Description", validators=[DataRequired()])
    publication_type = SelectField(
        "Publication type",
        choices=[(pt.value, pt.name.replace("_", " ").title()) for pt in PublicationType],
        validators=[DataRequired()],
    )
    publication_doi = StringField("Publication DOI", validators=[Optional(), URL()])
    dataset_doi = StringField("Dataset DOI", validators=[Optional(), URL()])
    tags = StringField("Tags (separated by commas)")
    authors = FieldList(FormField(AuthorForm))
    
    csv_file = FileField(
        'Archivo CSV del Dataset',
        validators=[
            FileRequired(message='¡No has seleccionado ningún archivo!'),
            FileAllowed(['csv'], message='¡Solo se permiten archivos .csv!')
        ]
    )

    submit = SubmitField("Submit")

    def get_dsmetadata(self):

        publication_type_converted = self.convert_publication_type(self.publication_type.data)

        return {
            "title": self.title.data,
            "description": self.desc.data,
            "publication_type": publication_type_converted,
            "publication_doi": self.publication_doi.data,
            "dataset_doi": self.dataset_doi.data,
            "tags": self.tags.data,
        }

    def convert_publication_type(self, value):
        for pt in PublicationType:
            if pt.value == value:
                return pt.name
        return "NONE"

    def get_authors(self):
        return [author.get_author() for author in self.authors]
