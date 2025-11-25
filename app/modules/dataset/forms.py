from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, SelectField, StringField, ValidationError, SelectMultipleField, SubmitField, TextAreaField
from wtforms.validators import URL, DataRequired, Optional, Length
from flask_wtf.file import FileField, FileAllowed, FileRequired
from app.modules.dataset.models import PublicationType, DataSet, Community
import pandas as pd

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
        validators=[DataRequired(message='El logo es obligatorio.'),
                    FileAllowed(['jpg', 'png', 'jpeg'], 'Solo se permiten imágenes JPG, JPEG o PNG!')] 
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
    
    authors = FieldList(FormField(AuthorForm), min_entries=1)
    
    csv_file = FileField(
        'Archivo CSV del Dataset',
        validators=[
            FileRequired(message='¡No has seleccionado ningún archivo!'),
            FileAllowed(['csv'], message='¡Solo se permiten archivos .csv!')
        ]
    )

    submit = SubmitField("Submit")

    def validate_csv_file(self, field):
        if not field.data:
            return

        beer_keywords = {
            # Identificadores
            'name', 'nombre', 'id', 'beer_name', 'cerveza', 'brand', 'marca',
            
            # Métricas Químicas/Físicas
            'abv', 'alcohol', 'ibu', 'srm', 'ebc', 'og', 'fg', 'gravity', 
            'ph', 'color', 'bitterness', 'amargor', 'clarity',
            
            # Ingredientes
            'hops', 'lupulo', 'hop', 'malt', 'malta', 'grain', 'grano', 
            'yeast', 'levadura', 'adjuncts', 'ingredients', 'ingredientes',
            
            # Clasificación
            'style', 'estilo', 'category', 'categoria', 'type', 'tipo',
            
            # Producción/Origen
            'brewery', 'cerveceria', 'brewed', 'location', 'city', 'country', 
            'pais', 'region', 'state', 'batch', 'lote',
            
            # Cata/Reseñas
            'aroma', 'taste', 'sabor', 'palate', 'mouthfeel', 'cuerpo', 
            'finish', 'review', 'rating', 'score', 'puntuacion', 'notes', 'notas',
            
            # Envase/Comercial
            'oz', 'ml', 'volume', 'volumen', 'size', 'price', 'precio'
        }

        try:
            df = pd.read_csv(field.data, nrows=0)
            
            csv_columns = set([col.lower() for col in df.columns])

            if not csv_columns.intersection(beer_keywords):
                raise ValidationError(
                    f"El CSV no parece ser de cervezas. No se encontraron columnas como: {', '.join(list(beer_keywords)[:5])}..."
                )

            field.data.seek(0)

        except pd.errors.EmptyDataError:
            raise ValidationError("El archivo CSV está vacío.")
        except Exception as e:
            raise ValidationError(f"Error al leer el CSV: {str(e)}")

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
