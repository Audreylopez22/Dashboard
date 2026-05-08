import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
import plotly.io as pio
from io import BytesIO

if (
    "authentication_status" not in st.session_state
    or st.session_state.authentication_status is None
    or st.session_state.authentication_status is False
):
    st.warning("You must login to access this page.")
    st.markdown(
        f'<meta http-equiv="refresh" content="0;url={st.secrets.urls.login}">',
        unsafe_allow_html=True,
    )
    st.stop()

# --- CONFIGURATION ---
API_KEY = st.secrets["QUINTADB_API_KEY"]
APP_ID = st.secrets["APP_ID"]
ENTITY_ID = "cObmkYWRndWQPVoCkCWP5c"

colors = [
    '#4ad0f2',
    '#bf51b2',
    '#5E35B1', 
    '#E93166',  
    '#00ACC1',  
    '#F0842E',  
    '#689F38', 
    '#E0E0E0', 
    '#D72727', 
    '#263238',  
    '#C0D930',  
    '#FBC02D',  
    '#1A237E',
    '#D32F2F',  
    '#4FC3F7', 
    '#AFB42B',
    '#CE93D8',  
    '#A1887F', 
    '#FFEB3B'   
]

pio.templates.default = "plotly_white"

st.set_page_config(page_title="Conecta Unicamacho", layout="wide")

def formalizar_grafico(fig, titulo, n_valid=None, n_total=None):

    for trace in fig.data:
        trace_type = trace.type

        if trace_type == "bar":
            trace.textposition = "outside"

        elif trace_type == "scatter":
            trace.textposition = "top center"

        elif trace_type == "pie":
            trace.textposition = "inside"

        if "textfont" in trace:
            trace.textfont = dict(
                color="black",
                size=13
            )

        if "cliponaxis" in trace:
            trace.cliponaxis = False

    eje_style = dict(
        title_font=dict(color="black", size=16),
        tickfont=dict(color="black", size=12),
        mirror=True,
        automargin=True
    )

    fig.update_xaxes(**eje_style)
    fig.update_yaxes(**eje_style)

    layout_args = {
        'title': {
            'text': titulo,
            'font': {'size': 24, 'color': 'black'}
        },
        'margin': dict(t=90),
        'bargap': 0.1,
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'paper_bgcolor': 'white',
        'uniformtext_minsize': 10,
        'uniformtext_mode': 'hide'
    }

    if n_valid is not None and n_total is not None:
        layout_args['title']['subtitle'] = {
            'text': f"Muestra: {n_valid} de {n_total} registros analizados",
            'font': {'color': "#000000"}
        }

    fig.update_layout(**layout_args)

    return fig

#@st.cache_data
def fetch_quintadb_data_companies():
    """Obtiene todos los registros de QuintaDB con paginación optimizada."""
    all_records = []
    current_page = 1
    has_next_page = True

    while has_next_page:
        records_url = f"https://quintadb.com/apps/{APP_ID}/dtypes/entity/{ENTITY_ID}.json"
        query_params = {
            "rest_api_key": API_KEY,
            "page": current_page,
            "name_value": 1,
            "fetch_all": True,
            "per_page": 500 
        }
        
        try:
            response = requests.get(records_url, params=query_params).json()
            records = response.get('records', [])
            
            if not records:
                break
            
            for rec in records:
                row = {}
                for key, value in rec.get('values', {}).items():
                    if isinstance(value, str):
                        clean_value = value.strip()
                        if clean_value:
                            row[key] = clean_value
                all_records.append(row)
            
            # Si recibimos menos del límite, es la última página
            if len(records) < 500:
                has_next_page = False
            else:
                current_page += 1 
                
        except Exception as e:
            st.error(f"Error en la petición API: {e}")
            break

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    
    # Limpieza: Eliminar columnas estáticas/metadatos
    for col in df.columns:
        if df[col].nunique() <= 1:
            df = df.drop(columns=[col])
    
    return df


df_companies = fetch_quintadb_data_companies()

# --- LÓGICA DEL DASHBOARD DE EMPRESAS (CON CONTEO DE DATOS N) ---

if not df_companies.empty:
    st.title("🏢 Dashboard de Empresas")
    
    total_count = len(df_companies)
    
    def count_positive_responses(column_name):
        if column_name in df_companies.columns:
            return df_companies[column_name].str.upper().str.strip().isin(['SÍ', 'SI']).sum()
        return 0

    active_links = count_positive_responses('Ha mantenido vínculos con Unicamacho durante los últimos 5 años')
    investment_interest = count_positive_responses('¿Está interesado en invertir en el sector educativo?')
    has_graduates = count_positive_responses('¿Actualmente en su empresa trabajan egresados o practicantes de Unicamacho?')
    
    st.subheader(f"📊 Total de empresas: {total_count}")
    #kpi_col2.metric("Con Vínculo Activo", active_links, f"{(active_links/total_count)*100:.1f}%")
    #kpi_col3.metric("Tienen Egresados", has_graduates)
    #kpi_col4.metric("Potencial Inversión", investment_interest)

    st.divider()

    # 2. SISTEMA DE PESTAÑAS (TABS)
    tab_general, tab_loyalty, tab_opportunities = st.tabs([
        "📊 Perfil Corporativo", 
        "🤝 Fidelización y Desempeño", 
        "🚀 Oportunidades y Mejora"
    ])

    # --- PESTAÑA: PERFIL CORPORATIVO ---
    with tab_general:
        # Gráfico 1: Sector Económico
        #st.markdown("#### Composición por Sector Económico")
        sector_column = 'Actividad económica'
        if sector_column in df_companies.columns:
            # Calculamos N para este gráfico (datos no nulos)
            exclude_list = ['N/A', 'Otro', 'Otros', 'No reporta', 'Sin información']
            df_filtered = df_companies[df_companies[sector_column].notna() & 
            ~df_companies[sector_column].isin(exclude_list)
            ]
            n_total = df_companies.shape[0]
            n_sector = len(df_filtered)
            #st.caption(f"Muestra: {n_sector} de {n_total} registros analizados")
            
            sector_counts = df_filtered[sector_column].fillna('No reporta').value_counts().head(12).reset_index()
            sector_counts.columns = ['Sector', 'Cantidad']
            
            fig_sector = px.bar(
                sector_counts, x='Cantidad', y='Sector', 
                orientation='h', text_auto=True,
                color='Sector'
            )
            fig_sector.update_layout(yaxis={'categoryorder':'total ascending'},showlegend=False, coloraxis_showscale=False, height=500)
            formalizar_grafico(fig_sector, "Composición por Sector Económico", n_sector, n_total)
            st.plotly_chart(fig_sector, width="stretch")

        st.divider()

        # Gráfico 2: Tamaño de Empresa
        #st.markdown("#### Distribución por Tamaño de Empresa")
        size_column = 'Tamaño de la empresa'
        if size_column in df_companies.columns:
            # Filtramos nulos y contamos N
            clean_size_df = df_companies[df_companies[size_column].notna() & (df_companies[size_column] != "")].copy()
            n_size = len(clean_size_df)
            n_total = df_companies.shape[0]
            #st.caption(f"Muestra: {n_size} de {n_total} empresas.")
            
            size_summary = clean_size_df[size_column].value_counts().reset_index()
            size_summary.columns = ['Tamaño', 'Total']
            
            fig_size = px.pie(
                size_summary, names='Tamaño', values='Total', 
                hole=0.5, color = 'Tamaño'
            )
            fig_size.update_layout(height=500)
            formalizar_grafico(fig_size, "Distribución por Tamaño de Empresa", n_size, n_total)
            st.plotly_chart(fig_size, use_container_width=True)
            
            st.divider()
        # --- SECCIÓN: MAPA DE DISTRIBUCIÓN GLOBAL ---

        st.markdown("#### 🌍 Cobertura Internacional de Empresas Aliadas")
        
        map_script = """
        <div id='mapheightasadldH8jkuAddPSoYW7Wg' style='display:none'></div>
        <div id='mth-maprhasadldH8jkuAddPSoYW7Wg' style='width: 100%; min-height: 500px;'>Cargando mapa...</div>

        <script type='text/javascript'>
            var mapurl_height = 'https://quintadb.com/widgets/bAcSo4W7PcQjKBDvldHmkk/get_map_height/asadldH8jkuAddPSoYW7Wg.js';
            var maprhasadldH8jkuAddPSoYW7Wg;
            
            (function(d, t) {
                var s = d.createElement(t), 
                options = {
                    'userName':'',
                    'mapHashURL':'/apps/bAcSo4W7PcQjKBDvldHmkk/gmaps/asadldH8jkuAddPSoYW7Wg/widget',
                    'mapHash':'maprhasadldH8jkuAddPSoYW7Wg', 
                    'autoResize':true,
                    'height': '500px', 
                    'width': '100%', // FORZAMOS EL ANCHO AL 100% AQUÍ
                    'heightURL': mapurl_height, 
                    'formID': 'asadldH8jkuAddPSoYW7Wg',
                    'async':true,
                    'host':'quintadb.com',
                    'header':'show',
                    'ssl':true
                };
                
                s.src = 'https://quintadb.com/scripts/map.js';
                
                s.onload = s.onreadystatechange = function() {
                    var rs = this.readyState; 
                    if (rs) if (rs != 'complete') if (rs != 'loaded') return;
                    try { 
                        maprhasadldH8jkuAddPSoYW7Wg = new mthMap();
                        maprhasadldH8jkuAddPSoYW7Wg.initialize(options);
                        maprhasadldH8jkuAddPSoYW7Wg.display();
                        maprhasadldH8jkuAddPSoYW7Wg.addResizeScript(); 
                    } catch (e) {
                        console.error("Error al inicializar el mapa:", e);
                    }
                };
                var scr = d.getElementsByTagName(t)[0], par = scr.parentNode; 
                par.insertBefore(s, scr);
            })(document, 'script');
        </script>
        """
        components.html(map_script, height=720)


    # --- PESTAÑA: FIDELIZACIÓN ---
    with tab_loyalty:
        # Gráfico 3: Desempeño
        #st.markdown("#### Calificación del Desempeño")
        performance_column = '¿Cómo califica el desempeño de los practicantes o egresados de Unicamacho?'
        if performance_column in df_companies.columns:
            exclude_list = ['N/A', 'Otro', 'Otros', 'No reporta', 'Sin información']
            # N para desempeño
            clean_perf = df_companies[df_companies[performance_column].notna() & 
            ~df_companies[performance_column].isin(exclude_list)].copy()
            n_perf = len(clean_perf)
            n_total = df_companies.shape[0]
            #st.caption(f"Muestra: {n_perf} de {n_total} evaluaciones de empresas")
            
            performance_data = clean_perf[performance_column].value_counts().reset_index()
            performance_data.columns = ['Calificación', 'Cantidad']
            
            fig_performance = px.bar(
                performance_data, x='Cantidad', y='Calificación', 
                orientation='h', text_auto=True, 
                color='Calificación'
            )
            fig_performance.update_layout(showlegend=False, coloraxis_showscale=False,yaxis={'categoryorder':'total ascending'}, yaxis_title="", height=400)
            formalizar_grafico(fig_performance, "Calificación del Desempeño", n_perf, n_total)
            st.plotly_chart(fig_performance, use_container_width=True)

        st.divider()

        # Gráfico 4: Convenios
        #st.markdown("#### Modalidades de Convenio Existentes")
        agreement_column = '¿Qué modalidad de convenio ha tenido con Unicamacho?'
        if agreement_column in df_companies.columns:
            exclude_list = ['N/A', 'Otro', 'Otros', 'No reporta', 'Sin información']
            df_filtered = df_companies[
                df_companies[agreement_column].notna() & 
                ~df_companies[agreement_column].isin(exclude_list)
            ]
            n_agree = len(df_filtered)
            n_total = df_companies.shape[0]
            #st.caption(f"Muestra: {n_agree} de {n_total} empresas. ")
            
            agreement_data = df_filtered[agreement_column].value_counts().reset_index()
            agreement_data.columns = ['Modalidad', 'Cantidad']
            
            fig_agreement = px.bar(
                agreement_data, x='Cantidad', 
                orientation='h',
                y='Modalidad', 
                text_auto=True, color='Modalidad'
            )
            fig_agreement.update_layout(
                showlegend=False, 
                coloraxis_showscale=False,         # Oculta la barra de color lateral
                yaxis={'categoryorder':'total ascending'}, 
                xaxis_title="Número de empresas",
                yaxis_title="",
                height=500,
                margin=dict(l=0, r=50, t=30, b=0)   # Ajuste de márgenes
            )
            formalizar_grafico(fig_agreement, "Modalidades de Convenio Existentes", n_agree, n_total)
            st.plotly_chart(fig_agreement, use_container_width=True)

    # --- PESTAÑA: OPORTUNIDADES ---
    with tab_opportunities:
        # Gráfico 5: Áreas de Interés
        #st.markdown("#### Áreas de Interés para Colaboración")
        interest_column = '¿En qué áreas estaría interesado en colaborar con Unicamacho?'
        if interest_column in df_companies.columns:
            # En este caso N es el número de empresas que respondieron, aunque marquen varias áreas
            exclude_list = ['N/A', 'Otro', 'Otros', 'No reporta', 'Sin información']
            df_filtered = df_companies[
                df_companies[interest_column].notna() & 
                ~df_companies[interest_column].isin(exclude_list)
            ]
            n_interest = len(df_filtered)
            n_total = df_companies.shape[0]
            #st.caption(f"Muestra: {n_interest} de {n_total} empresas.")
            
            interests_list = df_filtered[interest_column].str.split(',').explode().str.strip()
            interests_summary = interests_list.value_counts().head(15).reset_index()
            interests_summary.columns = ['Área', 'Empresas']
            
            fig_interests = px.bar(
                interests_summary, x='Empresas', y='Área', 
                orientation='h', text_auto=True, 
                color='Área'
            )
            fig_interests.update_layout(coloraxis_showscale=False, yaxis={'categoryorder':'total ascending'},showlegend=False,  height=600)
            formalizar_grafico(fig_interests, "Áreas de Interés para Colaboración", n_interest, n_total)
            st.plotly_chart(fig_interests, use_container_width=True)

    # 3. SECCIÓN DE DATOS CRUDOS
    st.divider()
    with st.expander("🔍 Directorio y Tabla Detallada"):

        authorized_users = ["admin", "vgonzalezv"]
        
        if st.session_state.get("username") in authorized_users:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_companies.to_excel(writer, index=False, sheet_name='Directorio')
            
            excel_data = output.getvalue()

            st.download_button(
                label="📥 Descargar tabla en Excel",
                data=excel_data,
                file_name="directorio_empresas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        st.dataframe(df_companies, use_container_width=True)

else:
    st.info("No se encontraron registros de empresas para mostrar.")