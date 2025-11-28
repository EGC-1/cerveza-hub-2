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
        
        STRONG_BEER_INDICATORS = {
            'ibu', 'srm', 'ebc', 'style', 'brewery', 'og', 'fg', 'attenuation', 'abv', 'ph'}
        BEER_NAMES_SET = {
    # Marcas Internacionales
    'augberger',
    'becks', 'becks_0_0', 'becks_extra', 'becks_gold', 'becks_ice', 'becks_lager', 'becks_light', 'becks_lite', 'becks_pilsner', 'becks_premium', 'becks_red', 'becks_reservada', 'becks_sin', 'becks_tostada', 'becks_ultra', 'becks_zero',
    'budweiser', 'budweiser_0_0', 'budweiser_extra', 'budweiser_gold', 'budweiser_ice', 'budweiser_lager', 'budweiser_light', 'budweiser_lite', 'budweiser_pilsner', 'budweiser_premium', 'budweiser_red', 'budweiser_reservada', 'budweiser_sin', 'budweiser_tostada', 'budweiser_ultra', 'budweiser_zero',
    'carlsberg', 'carlsberg_0_0', 'carlsberg_extra', 'carlsberg_gold', 'carlsberg_ice', 'carlsberg_lager', 'carlsberg_light', 'carlsberg_lite', 'carlsberg_pilsner', 'carlsberg_premium', 'carlsberg_red', 'carlsberg_reservada', 'carlsberg_sin', 'carlsberg_tostada', 'carlsberg_ultra', 'carlsberg_zero',
    'chimay',
    'coors', 'coors_0_0', 'coors_extra', 'coors_gold', 'coors_ice', 'coors_lager', 'coors_light', 'coors_lite', 'coors_pilsner', 'coors_premium', 'coors_red', 'coors_reservada', 'coors_sin', 'coors_tostada', 'coors_ultra', 'coors_zero',
    'corona', 'corona_0_0', 'corona_extra', 'corona_gold', 'corona_ice', 'corona_lager', 'corona_light', 'corona_lite', 'corona_pilsner', 'corona_premium', 'corona_red', 'corona_reservada', 'corona_sin', 'corona_tostada', 'corona_ultra', 'corona_zero',
    'coronita', 'coronita_0_0', 'coronita_extra', 'coronita_gold', 'coronita_ice', 'coronita_lager', 'coronita_light', 'coronita_lite', 'coronita_pilsner', 'coronita_premium', 'coronita_red', 'coronita_reservada', 'coronita_sin', 'coronita_tostada', 'coronita_ultra', 'coronita_zero',
    'dos_equis', 'dos_equis_0_0', 'dos_equis_extra', 'dos_equis_gold', 'dos_equis_ice', 'dos_equis_lager', 'dos_equis_light', 'dos_equis_lite', 'dos_equis_pilsner', 'dos_equis_premium', 'dos_equis_red', 'dos_equis_reservada', 'dos_equis_sin', 'dos_equis_tostada', 'dos_equis_ultra', 'dos_equis_zero',
    'duvel',
    'erdinger',
    'guinness', 'guinness_0_0', 'guinness_extra', 'guinness_gold', 'guinness_ice', 'guinness_lager', 'guinness_light', 'guinness_lite', 'guinness_pilsner', 'guinness_premium', 'guinness_red', 'guinness_reservada', 'guinness_sin', 'guinness_tostada', 'guinness_ultra', 'guinness_zero',
    'hamms', 'hamms_0_0', 'hamms_extra', 'hamms_gold', 'hamms_ice', 'hamms_lager', 'hamms_light', 'hamms_lite', 'hamms_pilsner', 'hamms_premium', 'hamms_red', 'hamms_reservada', 'hamms_sin', 'hamms_tostada', 'hamms_ultra', 'hamms_zero',
    'heineken', 'heineken_0_0', 'heineken_extra', 'heineken_gold', 'heineken_ice', 'heineken_lager', 'heineken_light', 'heineken_lite', 'heineken_pilsner', 'heineken_premium', 'heineken_red', 'heineken_reservada', 'heineken_sin', 'heineken_tostada', 'heineken_ultra', 'heineken_zero',
    'kirin', 'kirin_0_0', 'kirin_extra', 'kirin_gold', 'kirin_ice', 'kirin_lager', 'kirin_light', 'kirin_lite', 'kirin_pilsner', 'kirin_premium', 'kirin_red', 'kirin_reservada', 'kirin_sin', 'kirin_tostada', 'kirin_ultra', 'kirin_zero',
    'kronenbourg', 'kronenbourg_0_0', 'kronenbourg_extra', 'kronenbourg_gold', 'kronenbourg_ice', 'kronenbourg_lager', 'kronenbourg_light', 'kronenbourg_lite', 'kronenbourg_pilsner', 'kronenbourg_premium', 'kronenbourg_red', 'kronenbourg_reservada', 'kronenbourg_sin', 'kronenbourg_tostada', 'kronenbourg_ultra', 'kronenbourg_zero',
    'lowenbrau', 'lowenbrau_0_0', 'lowenbrau_extra', 'lowenbrau_gold', 'lowenbrau_ice', 'lowenbrau_lager', 'lowenbrau_light', 'lowenbrau_lite', 'lowenbrau_pilsner', 'lowenbrau_premium', 'lowenbrau_red', 'lowenbrau_reservada', 'lowenbrau_sin', 'lowenbrau_tostada', 'lowenbrau_ultra', 'lowenbrau_zero',
    'michelob', 'michelob_0_0', 'michelob_extra', 'michelob_gold', 'michelob_ice', 'michelob_lager', 'michelob_light', 'michelob_lite', 'michelob_pilsner', 'michelob_premium', 'michelob_red', 'michelob_reservada', 'michelob_sin', 'michelob_tostada', 'michelob_ultra', 'michelob_zero',
    'miller_lite',
    'modelo', 'modelo_0_0', 'modelo_extra', 'modelo_gold', 'modelo_ice', 'modelo_lager', 'modelo_light', 'modelo_lite', 'modelo_pilsner', 'modelo_premium', 'modelo_red', 'modelo_reservada', 'modelo_sin', 'modelo_tostada', 'modelo_ultra', 'modelo_zero',
    'old_milwaukee',
    'pabst', 'pabst_0_0', 'pabst_extra', 'pabst_extra_light', 'pabst_gold', 'pabst_ice', 'pabst_lager', 'pabst_light', 'pabst_lite', 'pabst_pilsner', 'pabst_premium', 'pabst_red', 'pabst_reservada', 'pabst_sin', 'pabst_tostada', 'pabst_ultra', 'pabst_zero',
    'sam_adams', 'sam_adams_0_0', 'sam_adams_extra', 'sam_adams_gold', 'sam_adams_ice', 'sam_adams_lager', 'sam_adams_light', 'sam_adams_lite', 'sam_adams_pilsner', 'sam_adams_premium', 'sam_adams_red', 'sam_adams_reservada', 'sam_adams_sin', 'sam_adams_tostada', 'sam_adams_ultra', 'sam_adams_zero',
    'schlitz', 'schlitz_0_0', 'schlitz_extra', 'schlitz_gold', 'schlitz_ice', 'schlitz_lager', 'schlitz_light', 'schlitz_lite', 'schlitz_pilsner', 'schlitz_premium', 'schlitz_red', 'schlitz_reservada', 'schlitz_sin', 'schlitz_tostada', 'schlitz_ultra', 'schlitz_zero',
    'stella_artois', 'stella_artois_0_0', 'stella_artois_extra', 'stella_artois_gold', 'stella_artois_ice', 'stella_artois_lager', 'stella_artois_light', 'stella_artois_lite', 'stella_artois_pilsner', 'stella_artois_premium', 'stella_artois_red', 'stella_artois_reservada', 'stella_artois_sin', 'stella_artois_tostada', 'stella_artois_ultra', 'stella_artois_zero',
    'strohs_bohemian_style',
    'weihenstephan',

    # Marcas Españolas y Variaciones
    'alhambra', 'alhambra_0_0', 'alhambra_blanca', 'alhambra_clasica', 'alhambra_extra', 'alhambra_gold', 'alhambra_ice', 'alhambra_lager', 'alhambra_light', 'alhambra_lite', 'alhambra_negra', 'alhambra_pilsner', 'alhambra_premium', 'alhambra_red', 'alhambra_reservada', 'alhambra_sin', 'alhambra_tostada', 'alhambra_ultra', 'alhambra_zero',
    'alhambra_sin', 
    'amstel', 'amstel_0_0', 'amstel_blanca', 'amstel_clasica', 'amstel_extra', 'amstel_gold', 'amstel_ice', 'amstel_lager', 'amstel_light', 'amstel_lite', 'amstel_negra', 'amstel_pilsner', 'amstel_premium', 'amstel_red', 'amstel_reservada', 'amstel_sin', 'amstel_tostada', 'amstel_ultra', 'amstel_zero',
    'buckler_sin',
    'cruzcampo', 'cruzcampo_0_0', 'cruzcampo_blanca', 'cruzcampo_clasica', 'cruzcampo_extra', 'cruzcampo_gold', 'cruzcampo_ice', 'cruzcampo_lager', 'cruzcampo_light', 'cruzcampo_lite', 'cruzcampo_negra', 'cruzcampo_pilsner', 'cruzcampo_premium', 'cruzcampo_red', 'cruzcampo_reservada', 'cruzcampo_sin', 'cruzcampo_tostada', 'cruzcampo_ultra', 'cruzcampo_zero',
    'cruzcampo_light',
    'estrella', 'estrella_0_0', 'estrella_blanca', 'estrella_clasica', 'estrella_damm', 'estrella_damm_0_0', 'estrella_damm_extra', 'estrella_damm_gold', 'estrella_damm_ice', 'estrella_damm_lager', 'estrella_damm_light', 'estrella_damm_lite', 'estrella_damm_negra', 'estrella_damm_pilsner', 'estrella_damm_premium', 'estrella_damm_red', 'estrella_damm_reservada', 'estrella_damm_sin', 'estrella_damm_tostada', 'estrella_damm_ultra', 'estrella_damm_zero',
    'estrella_extra', 'estrella_galicia', 'estrella_galicia_0_0', 'estrella_galicia_extra', 'estrella_galicia_gold', 'estrella_galicia_ice', 'estrella_galicia_lager', 'estrella_galicia_light', 'estrella_galicia_lite', 'estrella_galicia_negra', 'estrella_galicia_pilsner', 'estrella_galicia_premium', 'estrella_galicia_red', 'estrella_galicia_reservada', 'estrella_galicia_sin', 'estrella_galicia_tostada', 'estrella_galicia_ultra', 'estrella_galicia_zero',
    'estrella_gold', 'estrella_ice', 'estrella_lager', 'estrella_light', 'estrella_lite', 'estrella_negra', 'estrella_pilsner', 'estrella_premium', 'estrella_red', 'estrella_reservada', 'estrella_sin', 'estrella_tostada', 'estrella_ultra', 'estrella_zero',
    'mahou', 'mahou_0_0', 'mahou_5_estrellas', 'mahou_blanca', 'mahou_clasica', 'mahou_extra', 'mahou_gold', 'mahou_ice', 'mahou_lager', 'mahou_light', 'mahou_lite', 'mahou_negra', 'mahou_pilsner', 'mahou_premium', 'mahou_red', 'mahou_reservada', 'mahou_sin', 'mahou_tostada', 'mahou_ultra', 'mahou_zero',
    'marca_blanca', 'marca_blanca_blanca', 'marca_blanca_extra', 'marca_blanca_lager', 'marca_blanca_sin',
    'san_miguel', 'san_miguel_0_0', 'san_miguel_blanca', 'san_miguel_clasica', 'san_miguel_especial', 'san_miguel_extra', 'san_miguel_gold', 'san_miguel_ice', 'san_miguel_lager', 'san_miguel_light', 'san_miguel_lite', 'san_miguel_negra', 'san_miguel_pilsner', 'san_miguel_premium', 'san_miguel_red', 'san_miguel_reservada', 'san_miguel_sin', 'san_miguel_tostada', 'san_miguel_ultra', 'san_miguel_zero',
    'voll_damm', 'voll_damm_0_0', 'voll_damm_blanca', 'voll_damm_clasica', 'voll_damm_extra', 'voll_damm_gold', 'voll_damm_ice', 'voll_damm_lager', 'voll_damm_light', 'voll_damm_lite', 'voll_damm_negra', 'voll_damm_pilsner', 'voll_damm_premium', 'voll_damm_red', 'voll_damm_reservada', 'voll_damm_sin', 'voll_damm_tostada', 'voll_damm_ultra', 'voll_damm_zero', 'Marca_blanca',

    # Estilos y Términos Genéricos
    'ale','barleywine','bock','cider','clara','dunkel','dubbel','esb','extra','gose','imperial','ipa','kolsch','lager','light',
    'negra','pilsner','porter','quadrupel','saison','sin','stout','tostada','tripel','weissbier','wheat',
}
        BEER_KEYWORDS = {
            'abv', 'alcohol', 'ibu', 'srm', 'ebc', 'style', 'brewery', 'name', 
    'calories', 'sodium', 'cost', 'ph', 'color', 'bitterness', 'amargor', 
    'hops', 'malt', 'yeast', 'lupulo', 'malta', 'levadura', 'rating', 
    'score', 'puntuacion', 'country', 'pais', 'origen', 'precio', 'marca',
    'volumen', 'volume', 'og', 'fg', 'attenuation', 'fermentacion', 'fermentation', 
    'tipo', 'type', 'cebada', 'barley', 'tostado', 'clara', 'oscura', 'negra', 'rubia', 'nombre', 'calorias',
    

        }

        MIN_KEYWORDS_REQUIRED = 3     # Mínimo de columnas totales que deben coincidir
        MIN_STRONG_INDICATORS = 1     # Mínimo de indicadores fuertes OBLIGATORIOS (IBU, Style, Brewery, etc.)

        MIN_ROWS_TO_SAMPLE = 50       # Cuántas filas leer para el muestreo de nombres
        CONFIDENCE_THRESHOLD = 0.5    # 60% de los nombres deben coincidir con la lista de referencia
        MIN_CONFIDENCE_FOR_OVERRIDE = 0.7

        def try_read(encoding):
            field.data.seek(0)
            try:
                return pd.read_csv(field.data, nrows=MIN_ROWS_TO_SAMPLE, encoding=encoding, sep=None, engine='python')
            except Exception:
                return None

        df = try_read('utf-8')
        if df is None:
            df = try_read('latin-1')

        if df is None:
            raise ValidationError("El archivo no pudo ser leído. Asegúrate de que es un CSV válido y bien formado.")

        try:
            csv_columns_normalized = {str(col).lower().strip().replace(' ', '_') for col in df.columns}            
            
                
            column_to_validate = None
        
            for col in df.columns:
                if str(col).lower().strip() == 'name' or str(col).lower().strip() == 'nombre':
                    column_to_validate = col # Guardamos el nombre original de la columna
                    break
        
            if column_to_validate is None:
                first_col_name = str(df.columns[0]).lower().strip()
            
                if first_col_name == '' or 'unnamed:' in first_col_name:
                    column_to_validate = df.columns[0]
            
        
            content_confidence = 0.0

            if column_to_validate is not None:
                name_col = df[column_to_validate].astype(str).str.lower().str.strip().str.replace(' ', '_')
            
                total_names = len(name_col)
                match_count_content = 0
            
                for name in name_col:
                    if name in BEER_NAMES_SET:
                        match_count_content += 1
            
                content_confidence = match_count_content / total_names
                if content_confidence >= MIN_CONFIDENCE_FOR_OVERRIDE:
                    return 
            
                if content_confidence < CONFIDENCE_THRESHOLD:
                    col_display_name = f"'{column_to_validate}'" if 'unnamed' not in str(column_to_validate).lower() else "la primera columna sin nombre"
                
                    raise ValidationError(
                        f"El contenido de {col_display_name} no parece ser de cerveza. "
                        f"Solo el {content_confidence:.0%} de los nombres en la muestra coinciden con marcas conocidas. (Umbral: {CONFIDENCE_THRESHOLD:.0%})"
                    )
                
                match_count = len(csv_columns_normalized.intersection(BEER_KEYWORDS))
                for col_name in csv_columns_normalized:
                    if col_name.startswith('precio_'):
                        match_count += 1
            
                if match_count < MIN_KEYWORDS_REQUIRED:
                    raise ValidationError(
                        f"El CSV no tiene suficiente densidad de datos de cerveza. "
                        f"Se encontraron solo {match_count} columnas clave (se requieren {MIN_KEYWORDS_REQUIRED})."
                    )
                
                strong_match_count = len(csv_columns_normalized.intersection(STRONG_BEER_INDICATORS))
                if strong_match_count < MIN_STRONG_INDICATORS:
                    if content_confidence == 0.0 or content_confidence < MIN_CONFIDENCE_FOR_OVERRIDE:
                        missing_strong = STRONG_BEER_INDICATORS - csv_columns_normalized
                        raise ValidationError(
                            f"El CSV no es claramente de cerveza. Le faltan columnas clave únicas ({', '.join(STRONG_BEER_INDICATORS).upper()}). "
                            f"Se requiere un mínimo de {MIN_STRONG_INDICATORS} indicadores fuertes, y la confianza de nombres es muy baja ({content_confidence:.0%})."
                    )
        

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Error al procesar las columnas o el contenido: {str(e)}. Por favor, verifica el formato.")
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
