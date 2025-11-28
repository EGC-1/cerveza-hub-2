from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, SelectField, StringField, ValidationError, SelectMultipleField, SubmitField, TextAreaField
from wtforms.validators import URL, DataRequired, Optional, Length
from flask_wtf.file import FileField, FileAllowed, FileRequired
from app.modules.dataset.models import PublicationType, DataSet, Community
import pandas as pd

class CommunityDatasetForm(FlaskForm):
    datasets = SelectMultipleField(
        label='Available Datasets',
        description="Hold Ctrl/Cmd to select multiple datasets."
    )
    submit = SubmitField('Save Datasets')
    
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
        "Community Name", 
        validators=[DataRequired(message="Name is required."), Length(min=5, max=120)]
    )
    description = TextAreaField(
        "Description", 
        validators=[DataRequired(message="Description is required.")]
    )
    logo = FileField(
        "Community Logo", 
        validators=[DataRequired(message='Logo is required.'),
                    FileAllowed(['jpg', 'png', 'jpeg'], 'Only JPG, JPEG or PNG images are allowed!')] 
    )
    submit = SubmitField("Create Community")
    
    def get_community_data(self):
        """Returns the form text data."""
        return {
            "name": self.name.data,
            "description": self.description.data,
        }

    def validate_name(self, name):
        if Community.query.filter_by(name=name.data).first():
            raise ValidationError('A community with this name already exists. Please choose another.')

class DataSetForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    desc = TextAreaField("Description", validators=[DataRequired()])
    

    publication_type = SelectField(
        "Publication Type",
        choices=[(pt.value, pt.name.replace("_", " ").title()) for pt in PublicationType],
        validators=[DataRequired()],
    )
    
    tags = StringField("Tags (separated by commas)")
    

    authors = FieldList(FormField(AuthorForm), min_entries=1)
    
    csv_file = FileField(
        'Dataset CSV File',
        validators=[
            FileRequired(message='You did not select any file!'),
            FileAllowed(['csv'], message='Only .csv files are allowed!')
        ]
    )

    submit = SubmitField("Submit")

    def validate_csv_file(self, field):
        if not field.data:
            return

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

        def try_read(encoding):
            field.data.seek(0)
            try:
                return pd.read_csv(field.data, nrows=0, encoding=encoding, sep=None, engine='python')
            except Exception:
                return None

  
        df = try_read('utf-8')
        
        if df is None:
            df = try_read('latin-1')

        if df is None:
            raise ValidationError("The file could not be read. Make sure it is a valid CSV.")

     
        try:
      
            csv_columns = [str(col).lower().strip() for col in df.columns]

            found_match = False
        
            for col in csv_columns:
                for keyword in beer_keywords:
                    if keyword in col: 
                        found_match = True
                        break 
                if found_match: break 

            if not found_match:
                detected_cols = ", ".join(csv_columns[:5])
                raise ValidationError(
                    f"The CSV does not appear to be beer-related. No keywords found in: [{detected_cols}]"
                )

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Error processing columns: {str(e)}")
        finally:
            field.data.seek(0)

    def get_dsmetadata(self):
        publication_type_converted = self.convert_publication_type(self.publication_type.data)
        return {
            "title": self.title.data,
            "description": self.desc.data,
            "publication_type": publication_type_converted,
            "tags": self.tags.data,
        }

    def convert_publication_type(self, value):
        for pt in PublicationType:
            if pt.value == value:
                return pt.name
        return "NONE"

    def get_authors(self):
        return [author.get_author() for author in self.authors]
