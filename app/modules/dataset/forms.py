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

        # Palabras clave (todo en minúsculas)
        beer_keywords = {
            'name', 'nombre', 'id', 'beer_name', 'cerveza', 'brand', 'marca', 'origen', 'year', 'año',
            'abv', 'alcohol', 'ibu', 'srm', 'ebc', 'og', 'fg', 'gravity', 
            'ph', 'color', 'bitterness', 'amargor', 'clarity',
            'hops', 'lupulo', 'hop', 'malt', 'malta', 'grain', 'grano', 
            'yeast', 'levadura', 'adjuncts', 'ingredients', 'ingredientes',
            'style', 'estilo', 'category', 'categoria', 'type', 'tipo',
            'brewery', 'cerveceria', 'brewed', 'location', 'city', 'country', 
            'pais', 'region', 'state', 'batch', 'lote',
            'aroma', 'taste', 'sabor', 'palate', 'mouthfeel', 'cuerpo', 
            'finish', 'review', 'rating', 'score', 'puntuacion', 'notes', 'notas',
            'oz', 'ml', 'volume', 'volumen', 'size', 'price', 'precio'
        }

        # Función para intentar leer (auto-detectando separador ; o ,)
        def try_read(encoding):
            field.data.seek(0)
            try:
                # sep=None y engine='python' detectan automáticamente ; o ,
                return pd.read_csv(field.data, nrows=0, encoding=encoding, sep=None, engine='python')
            except Exception:
                return None

        # 1. Intentar UTF-8
        df = try_read('utf-8')
        # 2. Si falla, intentar Latin-1 (común en España)
        if df is None:
            df = try_read('latin-1')

        if df is None:
            raise ValidationError("No se pudo leer el archivo. Verifica que sea un CSV válido.")

        # --- VALIDACIÓN DE COLUMNAS (LÓGICA PARCIAL) ---
        try:
            # Limpiamos los nombres de las columnas del CSV
            csv_columns = [str(col).lower().strip() for col in df.columns]
            
            # IMPRIMIR EN CONSOLA DOCKER (Para depurar)
            print(f"DEBUG - Columnas leídas: {csv_columns}", flush=True)

            found_match = False
            # Buscamos si ALGUNA palabra clave está DENTRO de ALGUNA columna
            # Ejemplo: "precio" está dentro de "precio día" -> ¡Éxito!
            for col in csv_columns:
                for keyword in beer_keywords:
                    if keyword in col: 
                        found_match = True
                        break # Salir del bucle interno
                if found_match: break # Salir del bucle externo

            if not found_match:
                detected_cols = ", ".join(csv_columns[:5])
                raise ValidationError(
                    f"El CSV no parece ser de cervezas. No encontré palabras clave en: [{detected_cols}]"
                )

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Error procesando columnas: {str(e)}")
        finally:
            field.data.seek(0)

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