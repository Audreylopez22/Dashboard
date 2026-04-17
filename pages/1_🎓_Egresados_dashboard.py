import streamlit as st
import requests
import pandas as pd
import plotly.express as px

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
ENTITY_ID = "dcNJ3cGmndWOxcMCknpmo9"

@st.cache_data
def fetch_quintadb_data():
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

# --- UI SETUP ---
st.set_page_config(page_title="Conecta Unicamacho", layout="wide")
st.title("🎓 Conecta Unicamacho - Dashboard")

# Inicialización de datos en el estado de la sesión
if 'master_df' not in st.session_state:
    try:
        base_df = fetch_quintadb_data()
        if not base_df.empty:
            st.session_state.master_df = base_df
    except Exception as e:
        st.error(f"Error al procesar datos: {e}")

# --- FILTER LOGIC ---
if 'master_df' in st.session_state:
    original_df = st.session_state.master_df
    filtered_df = original_df.copy()
    
    st.sidebar.header("🔍 Filtros Globales")
    
    # Filtro: Año de Graduación
    year_col = 'Año de graduación'
    if year_col in original_df.columns:
        years_raw = original_df[year_col].dropna().unique()
        available_years = sorted([str(int(y) if isinstance(y, float) else y) for y in years_raw], reverse=True)
        selected_years = st.sidebar.multiselect("Año de Graduación:", available_years, default= available_years)
        if selected_years :
            filtered_df = filtered_df[filtered_df[year_col].isin(selected_years)]

    # Filtro: Estado Laboral
    job_col = '¿Trabaja actualmente?'
    if job_col in original_df.columns:
        job_status = st.sidebar.selectbox(
            "¿Trabaja actualmente?", 
            ["Todos", "Sí (Tiempo completo)", "Sí (Medio tiempo)", "Sí (Freelance / Independiente)", "No"]
        )
        if job_status != "Todos":
            filtered_df = filtered_df[filtered_df[job_col] == job_status]

    # Filtro: Continuidad de Estudios
    studies_col = '¿Continuó con sus estudios?'
    if studies_col in original_df.columns:
        studies_status = st.sidebar.selectbox("¿Continuó con sus estudios?", ["Todos", "Sí", "No"])
        if studies_status != "Todos":
            filtered_df = filtered_df[filtered_df[studies_col] == studies_status]

    # Filtro: Emprendimiento
    startup_col = '¿Ha creado empresa o emprendimiento?'
    if startup_col in original_df.columns:
        startup_status = st.sidebar.selectbox(
            "¿Ha creado empresa o emprendimiento?", 
            ["Todos", "Sí", "No", "Actualmente estoy en el proceso"]
        )
        if startup_status != "Todos":
            filtered_df = filtered_df[filtered_df[startup_col] == startup_status]
    
    # Filtro: unidad académica
    unit_col = 'Unidad Academica'
    if unit_col in original_df.columns:
        available_units = sorted(original_df[unit_col].unique())
        selected_units = st.sidebar.multiselect("Unidad Academica", available_units, placeholder="Todos")
        if selected_units:
            filtered_df = filtered_df[filtered_df[unit_col].isin(selected_units)]
            
    # Filtro: Nombre del programa
    program_col = 'Nombre del programa'
    if program_col in original_df.columns:
        available_programs = sorted(original_df[program_col].unique())
        selected_program = st.sidebar.multiselect("Nombre del programa", available_programs, placeholder="Todos")
        if selected_program:
            filtered_df = filtered_df[filtered_df[program_col].isin(selected_program)]
            
    # Para hacer el calculo para el grafico de edad. 
    if not filtered_df.empty and 'Fecha de nacimiento' in filtered_df.columns:
        born_date= pd.to_datetime(filtered_df['Fecha de nacimiento'], errors = 'coerce')
        filtered_df['Edad'] = (pd.Timestamp.now()-born_date).dt.days // 365
    

    # --- DASHBOARD VISUALIZATION ---
    st.subheader(f"📊 Total de egresados: {len(filtered_df)}")
    
    st.divider()

    # Gráficos Principales
    tab1, tab2, tab3, tab4 = st.tabs([
    "📊 General",
    "🎓 Académico",
    "💼 Laboral",
    "🚀 Emprendimiento"
    ])
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            if 'Género' in filtered_df.columns and not filtered_df.empty:
                st.write("### Distribución por Género")
                gender_data = filtered_df['Género'].value_counts().reset_index()
                gender_data.columns = ['Género', 'Cantidad']
                fig_gender = px.bar(
                gender_data, x='Género', y='Cantidad', color='Género',
                text_auto=True, color_discrete_sequence=px.colors.qualitative.Safe
            )
            fig_gender.update_layout(showlegend=False)
            st.plotly_chart(fig_gender, width='stretch')

        with col2:
            if 'Estrato social' in filtered_df.columns:
                st.write("### Estrato Social")
                estrato_data = filtered_df['Estrato social'].value_counts().reset_index()
                estrato_data.columns = ['Estrato', 'Cantidad']

                fig = px.bar(estrato_data, x='Estrato', y='Cantidad', text_auto=True)
                st.plotly_chart(fig, width='stretch')
    
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            if 'Edad' in filtered_df.columns and not filtered_df.empty:
                st.write("### Distribución por Edad")
                fig_edad = px.histogram(
                    filtered_df, 
                    x='Edad', 
                    nbins=20, 
                    labels={'Edad': 'Años', 'count': 'Frecuencia'},
                    color_discrete_sequence=['#636EFA']
                )
                fig_edad.update_layout(yaxis_title="Cantidad de Egresados", bargap=0.1)
                st.plotly_chart(fig_edad, width='stretch')

        with chart_col2:
            if year_col in filtered_df.columns and not filtered_df.empty:
                st.write("### Histórico de Graduaciones")
                # Usamos original_df para mantener la línea de tiempo completa como referencia
                timeline_data = original_df[year_col].value_counts().reset_index().sort_values(year_col)
                timeline_data.columns = ['Año', 'Cantidad']
                fig_timeline = px.line(timeline_data, x='Año', y='Cantidad', markers=True)
                st.plotly_chart(fig_timeline, width='stretch')    
        
        st.write("### Distribución Institucional por Unidad Académica")
        unit_col = 'Unidad Academica' 
        
        if unit_col in filtered_df.columns and not filtered_df.empty:
            unit_data = filtered_df[unit_col].value_counts().reset_index()
            unit_data.columns = [unit_col, 'Cantidad']
            
            fig_unit = px.bar(
                unit_data, 
                x=unit_col, 
                y='Cantidad', 
                text_auto=True,
                color=unit_col,
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            # Al estar fuera del bloque 'with', ocupará todo el ancho disponible
            fig_unit.update_layout(xaxis_title="Unidad Académica", showlegend=False)
            st.plotly_chart(fig_unit, width='stretch')
        else:
            st.info("No hay datos disponibles para Unidades Académicas.")

    # Tabla de detalles
    with st.expander("🔍 Ver tabla detallada"):
        st.dataframe(filtered_df, width='stretch')

with tab2:
    if filtered_df.empty:
        st.warning("No hay datos para mostrar en la sección académica.")
    else:
        # --- FILA 1: CONTINUIDAD Y NIVEL ALCANZADO ---
        col_ac1, col_ac2 = st.columns(2)

        with col_ac1:
            st.markdown("#### ¿Continuó con sus estudios?")
            cont_col = '¿Continuó con sus estudios?'
            if cont_col in filtered_df.columns:
                # Limpieza rápida
                cont_data = filtered_df[cont_col].fillna('No reporta').str.upper().str.strip()
                df_cont = cont_data.value_counts().reset_index()
                df_cont.columns = ['Estado', 'Cantidad']
                
                fig_cont = px.pie(
                    df_cont, names='Estado', values='Cantidad', 
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                st.plotly_chart(fig_cont, width='stretch')

        with col_ac2:
            st.markdown("#### Nivel Académico Alcanzado")
            # Vamos a consolidar las columnas de "Tiene..."
            niveles = {
                'Especialización': filtered_df['¿Tiene especialización?'].str.upper().str.strip().isin(['SÍ', 'SI']).sum(),
                'Maestría': filtered_df['¿Tiene maestría?'].str.upper().str.strip().isin(['SÍ', 'SI']).sum(),
                'Doctorado': filtered_df['¿Tiene doctorado?'].str.upper().str.strip().isin(['SÍ', 'SI']).sum(),
                'Segunda Carrera': filtered_df['¿Tiene segunda carrera universitaria?'].str.upper().str.strip().isin(['SÍ', 'SI']).sum()
            }
            df_niveles = pd.DataFrame(list(niveles.items()), columns=['Nivel', 'Cantidad'])
            
            fig_niv = px.bar(
                df_niveles, x='Nivel', y='Cantidad', 
                text_auto=True,
                color='Nivel',
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_niv.update_layout(showlegend=False)
            st.plotly_chart(fig_niv, width='stretch')

        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### ¿Quiere participar en un semillero?")
            if '¿Quiere participar en un semillero?' in filtered_df.columns:
                data = filtered_df['¿Quiere participar en un semillero?'].value_counts().reset_index()
                fig = px.pie(
                    data,
                    names='¿Quiere participar en un semillero?',  # Corrected: use the column with categories
                    values='count',  # Corrected: use the 'count' column for values
                    hole=0.5,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                st.plotly_chart(fig, width='stretch')

        with col2:
            st.markdown("#### ¿Piensa estudiar en 5 años?")
            if '¿Piensa estudiar en 5 años?' in filtered_df.columns:
                data = filtered_df['¿Piensa estudiar en 5 años?'].value_counts().reset_index()
                fig = px.pie(data, names='¿Piensa estudiar en 5 años?', values='count', hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig, width='stretch')

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("#### ¿Haría un posgrado en UNICAMACHO?")
            # Insight Senior: Este es el KPI de "Retención de Cliente" o Lealtad de marca.
            if '¿Haría un posgrado en UNICAMACHO?' in filtered_df.columns:
                data = filtered_df['¿Haría un posgrado en UNICAMACHO?'].value_counts().reset_index()
                fig = px.pie(data, names='¿Haría un posgrado en UNICAMACHO?', values='count', hole=0.5,
                            color_discrete_sequence=['#00CC96', '#EF553B', '#AB63FA'])
                st.plotly_chart(fig, width='stretch')
        
        with col4:
            st.markdown("#### Forma de estudio ")
            # Insight Senior: Este es el KPI de "Retención de Cliente" o Lealtad de marca.
            if 'Forma de estudio' in filtered_df.columns:
                data = filtered_df['Forma de estudio'].value_counts().reset_index()
                fig = px.pie(data, names='Forma de estudio', values='count', hole=0.5,
                            color_discrete_sequence=['#00CC96', '#EF553B', '#AB63FA'])
                st.plotly_chart(fig, width='stretch')

        st.divider()

        # --- FILA 2: FORMACIÓN ACUMULADA E IDIOMAS ---
        col5, col6 = st.columns(2)

        with col5:
            st.markdown("#### ¿Cuántos estudios ha realizado?")
            if '¿Cuántos estudios ha realizado?' in filtered_df.columns:
                # Senior Data Tip: Forzamos a que el eje X sea discreto (1, 2, 3...)
                fig = px.histogram(
                    filtered_df, 
                    x='¿Cuántos estudios ha realizado?', 
                    nbins=10, 
                    text_auto=True,
                    color_discrete_sequence=['#636EFA'])
                fig.update_layout(bargap=0.2, xaxis_title="Cantidad de estudios extras", yaxis_title="Cantidad")
                st.plotly_chart(fig, width='stretch')

        with col6:
            st.markdown("#### ¿Tiene certificaciones de idiomas?")
            if '¿Tiene certificaciones de idiomas?' in filtered_df.columns:
                data = filtered_df['¿Tiene certificaciones de idiomas?'].value_counts().reset_index()
                fig = px.bar(
                    data, 
                    x='¿Tiene certificaciones de idiomas?', 
                    y='count', 
                    text_auto=True, 
                    color='¿Tiene certificaciones de idiomas?', 
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig.update_layout(
                    showlegend=False, 
                    xaxis_title="", 
                    yaxis_title="Cantidad",
                    xaxis={'type': 'category'} # Esto evita que la barra se "estire"
                )
                fig.update_traces(width=0.5)            
                st.plotly_chart(fig, width='stretch')

        st.divider()

        # --- FILA 3: INTERÉS EN EDUCACIÓN FUTURA (COMPUESTO) ---
        st.markdown("#### Demanda Potencial por Tipo de Formación")
        
        # Ingeniería de Datos: Transformamos múltiples columnas en un DF largo para Plotly
        intereses = {
            'Posgrados': '¿Está interesado en posgrados (especialización, maestría, doctorado)?',
            'Idiomas': '¿Está interesado en idiomas?',
            'Diplomados': '¿Está interesado en diplomados?',
            'Cursos Cortos': '¿Está interesado en cursos cortos?'
        }
        
        list_data = []
        for label, col in intereses.items():
            if col in filtered_df.columns:
                counts = filtered_df[col].value_counts()
                for resp in ['Sí', 'No']:
                    list_data.append({
                        'Categoría': label,
                        'Interés': resp,
                        'Cantidad': counts.get(resp, 0) + counts.get(resp.upper(), 0)
                    })
        
        df_interes = pd.DataFrame(list_data)
        
        if not df_interes.empty:
            fig = px.bar(df_interes, x='Cantidad', y='Categoría', color='Interés',
                        barmode='group', orientation='h',
                        color_discrete_map={'Sí': '#00CC96', 'No': '#EF553B'},
                        text_auto=True)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, width='stretch')
        st.divider()

with tab3:
        if filtered_df.empty:
            st.warning("No hay datos disponibles con los filtros seleccionados.")
        else:
            
            # --- FILA 2: Distribución y Salarios ---
            col_main1, col_main2 = st.columns(2) # El boxplot necesita más espacio

            with col_main1:
                st.markdown("#### ¿Trabaja actualmente?")
                # Gráfico de Dona (más moderno que el Pie simple)
                fig_job = px.pie(
                    filtered_df, names='¿Trabaja actualmente?', 
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_job.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2))
                st.plotly_chart(fig_job, width='stretch')


            with col_main2:
                if 'Ingreso mensual aproximado ' in filtered_df.columns:
                    st.write("### Distribución de Ingresos (Mensual)")
                    salary_col = 'Ingreso mensual aproximado '
                    filtered_df[salary_col] = filtered_df[salary_col].astype(str)

                    salary_data = filtered_df[salary_col].value_counts().reset_index()
                    salary_data.columns = ['Ingreso', 'Cantidad']

                    fig = px.bar(salary_data, x='Ingreso', y='Cantidad', text_auto=True)
                    st.plotly_chart(fig, width='stretch')

            # --- FILA 3: Inserción y Experiencia ---
            st.divider()
            col_ins1, col_ins2 = st.columns(2)

            with col_ins1:
                st.markdown("#### ¿Cuánto tardó en encontrar un empleo después de graduarse?")
                col_name = '¿Cuánto tardó en encontrar un empleo después de graduarse?'
                if col_name in filtered_df.columns and not filtered_df.empty:
                    # 1. Definimos el orden lógico manual
                    # SUSTITUYE estos textos por los que aparecen exactamente en tu Excel/CSV
                    orden_personalizado = [
                        "Ya tenía un empleo relacionado a la carrera cuando se graduó",
                        "N/A",
                        "De 1 a 3 meses",
                        "De 3 a 6 meses",
                        "De 6 a 12 meses",
                        "Más de 1 año"
                    ]

                    fig_time = px.histogram(
                        filtered_df, 
                        x=col_name,
                        text_auto=True,
                        color_discrete_sequence=['#FFA500'],
                        # 2. Aplicamos el orden aquí:
                        category_orders={col_name: orden_personalizado}
                    )
                    
                    fig_time.update_layout(
                        bargap=0.2, 
                        xaxis_title="Tiempo de espera",
                        yaxis_title="Cantidad de Egresados"
                    )
                    
                    st.plotly_chart(fig_time, width='stretch')

            with col_ins2:
                st.markdown("#### Años de Experiencia Laboral")
                if '¿Cuántos años de experiencia laboral tiene?' in filtered_df.columns:
                    fig_exp = px.histogram(
                        filtered_df, x='¿Cuántos años de experiencia laboral tiene?',
                        nbins=15,
                        marginal="rug", # Añade una alfombra de densidad abajo
                        color_discrete_sequence=['#636EFA']
                    )
                    st.plotly_chart(fig_exp, width='stretch')

            # --- FILA 4: Detalles de la Empresa y Cargo ---
            st.divider()
            col_det1, col_det2 = st.columns(2)

            with col_det1:
                if '¿Tiene tarjeta profesional? ' in filtered_df.columns:
                    st.write("### ¿Tiene tarjeta profesional?")
                    profesional_card_col = '¿Tiene tarjeta profesional? '
                    filtered_df[profesional_card_col] = filtered_df[profesional_card_col].astype(str)

                    salary_data = filtered_df[profesional_card_col].value_counts().reset_index()
                    salary_data.columns = ['Tarjeta profesional', 'Cantidad']

                    fig = px.bar(salary_data, x='Tarjeta profesional', y='Cantidad', text_auto=True)
                    st.plotly_chart(fig, width='stretch')

            with col_det2:
                st.markdown("#### ¿Ha ascendido o cambiado de cargo?")
                ascenso_data = filtered_df['¿Ha ascendido o cambiado de cargo?'].value_counts()
                fig_asc = px.pie(
                    names=ascenso_data.index, 
                    values=ascenso_data.values, 
                    hole=0.5,
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4']
                )
                st.plotly_chart(fig_asc, width='stretch')

            # --- FILA 5: El Insight Maestro (Relación Estudio vs Empleo) ---
            st.divider()
            st.markdown("### 📈 Análisis de Formalidad Laboral")

            # --- GRÁFICO 1: EL UNIVERSO TOTAL ---
            col_uni1, col_uni2 = st.columns([1, 1.5])

            with col_uni1:
                st.markdown("#### ¿Cotiza en el sistema de seguridad de Colombia?")
                # Normalización y conteo
                if '¿Cotiza en el sistema de seguridad de Colombia?' in filtered_df.columns:
                    # Limpiamos los datos para asegurar que 'Sí' y 'Si' sean lo mismo
                    cotiza_status = filtered_df['¿Cotiza en el sistema de seguridad de Colombia?'].fillna('No reporta').str.upper().str.strip()
                    cotiza_status = cotiza_status.replace({'SI': 'SÍ'})
                    
                    df_cotiza = cotiza_status.value_counts().reset_index()
                    df_cotiza.columns = ['Estado', 'Cantidad']
                    
                    fig_pie_cotiza = px.pie(
                        df_cotiza, names='Estado', values='Cantidad',
                        hole=0.5,
                        color='Estado',
                        color_discrete_map={'SÍ': '#00CC96', 'NO': '#EF553B', 'NO REPORTA': '#AFAFAF'}
                    )
                    st.plotly_chart(fig_pie_cotiza, width='stretch')

            # --- GRÁFICO 2: DESGLOSE DE BENEFICIOS (Solo para los que SÍ cotizan) ---
            with col_uni2:
                st.markdown("#### Beneficios de quienes sí cotizan")
                
                # Filtramos el dataframe: Solo personas que marcaron "SÍ" en cotización
                mask_cotizantes = filtered_df['¿Cotiza en el sistema de seguridad de Colombia?'].fillna('').str.upper().str.strip().isin(['SÍ', 'SI'])
                df_solo_cotizantes = filtered_df[mask_cotizantes]
                
                if not df_solo_cotizantes.empty:
                    # Columnas de beneficios
                    cols_beneficios = ['EPS', 'Pensión', 'ARL', 'Caja de compensación']
                    
                    beneficios_data = []
                    for col in cols_beneficios:
                        if col in df_solo_cotizantes.columns:
                            # Contamos cuántos de este grupo tienen el beneficio (marcado como SÍ)
                            con_beneficio = df_solo_cotizantes[col].astype(str).str.upper().str.strip().isin(['SÍ', 'SI']).sum()
                            beneficios_data.append({'Beneficio': col, 'Cantidad': con_beneficio})
                    
                    df_ben_plot = pd.DataFrame(beneficios_data)
                    
                    fig_ben = px.bar(
                        df_ben_plot, 
                        x='Beneficio', 
                        y='Cantidad',
                        text_auto=True,
                        color='Beneficio',
                        color_discrete_sequence=px.colors.qualitative.Safe
                    )
                    
                    fig_ben.update_layout(showlegend=False, yaxis_title="Número de personas")
                    st.plotly_chart(fig_ben, width='stretch')
                else:
                    st.info("No hay datos de beneficios para mostrar (nadie cotiza en este filtro).")

with tab4: 
    if filtered_df.empty:
            st.warning("No hay datos disponibles con los filtros seleccionados.")
    else:
    
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### ¿Ha creado empresa?")
            if '¿Ha creado empresa o emprendimiento?' in filtered_df.columns:
                data_pie = filtered_df['¿Ha creado empresa o emprendimiento?'].value_counts().reset_index()
                fig_pie = px.pie(
                    data_pie, 
                    values='count', 
                    names='¿Ha creado empresa o emprendimiento?',
                    hole=0.4, # Estilo Donut (más moderno UI)
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4']
                )
                fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_pie, width='stretch')

        with col2:
            st.markdown("#### Etapa del emprendimiento")
            if '¿En qué etapa se encuentra la empresa o emprendimiento?' in filtered_df.columns:
                data_etapa = filtered_df['¿En qué etapa se encuentra la empresa o emprendimiento?'].value_counts().reset_index()
                fig_etapa = px.bar(
                    data_etapa,
                    x='¿En qué etapa se encuentra la empresa o emprendimiento?',
                    y='count',
                    text_auto=True,
                    color='¿En qué etapa se encuentra la empresa o emprendimiento?',
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_etapa.update_layout(showlegend=False, xaxis_title="", yaxis_title="Cantidad", xaxis={'categoryorder':'total descending'})
                st.plotly_chart(fig_etapa, width='stretch')

        # --- FILA 2: Actividad y Empleo ---
        col3, col4 = st.columns(2)

        with col3:
            st.markdown("#### Apoyo recibido")
            if '¿Recibió algún tipo de apoyo (formación y/o finanzas) para emprender?' in filtered_df.columns:
                data_apoyo = filtered_df['¿Recibió algún tipo de apoyo (formación y/o finanzas) para emprender?'].value_counts().reset_index()
                fig_apoyo = px.bar(
                    data_apoyo,
                    x='¿Recibió algún tipo de apoyo (formación y/o finanzas) para emprender?',
                    y='count',
                    color='¿Recibió algún tipo de apoyo (formación y/o finanzas) para emprender?',
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_apoyo.update_layout(showlegend=False, xaxis_title="", yaxis_title="Cantidad")
                st.plotly_chart(fig_apoyo, width='stretch')

        with col4:
            st.markdown("#### Generación de empleos")
            if '¿Cuántos empleos ha generado (aparte de usted)?' in filtered_df.columns:
                # Usamos histograma o barra según la distribución
                fig_emp = px.histogram(
                    filtered_df,
                    x='¿Cuántos empleos ha generado (aparte de usted)?',
                    text_auto=True,
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_emp.update_layout(xaxis_title="Número de empleos", yaxis_title="Frecuencia")
                st.plotly_chart(fig_emp, width='stretch')

        # --- FILA 3: Apoyos y Canales (Digitalización Insight) ---
        st.divider()
        st.write(" #### Actividad económica")
        unit_col = '¿Cuál es la actividad económica del emprendimiento o empresa?' 
        
        if unit_col in filtered_df.columns and not filtered_df.empty:
            unit_data = filtered_df[unit_col].value_counts().reset_index()
            unit_data.columns = [unit_col, 'Cantidad']
            
            fig_unit = px.bar(
                unit_data, 
                x=unit_col, 
                y='Cantidad', 
                text_auto=True,
                color=unit_col,
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            # Al estar fuera del bloque 'with', ocupará todo el ancho disponible
            fig_unit.update_layout(xaxis_title="Actividad económica", showlegend=False)
            st.plotly_chart(fig_unit, width='stretch')
        else:
            st.info("No hay datos disponibles para Actividad económica.")


            st.markdown("#### Actividad económica")
            if '¿Cuál es la actividad económica del emprendimiento o empresa?' in filtered_df.columns:
                data_act = filtered_df['¿Cuál es la actividad económica del emprendimiento o empresa?'].value_counts().reset_index()
                fig_act = px.bar(
                    data_act,
                    x='¿Cuál es la actividad económica del emprendimiento o empresa?',
                    y='count',
                    text_auto=True,
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4']
                )
                fig_act.update_layout(xaxis_title="", yaxis_title="Cantidad", xaxis={'categoryorder':'total descending'})
                st.plotly_chart(fig_act, width='stretch')

        st.write(" #### Canales de comunicación")
        column_canales = '¿Su empresa o emprendimiento cuenta con alguno de los siguientes canales de comunicación?'

        if column_canales in filtered_df.columns:
            # Lógica de Data Engineering: Procesar opciones múltiples
            series_canales = filtered_df[column_canales].dropna().astype(str).str.split(',')
            
            # Limpiamos espacios en blanco y aplanamos la lista
            all_canales = [item.strip() for sublist in series_canales for item in sublist if item.strip()]
            
            if all_canales:
                data_canales = pd.Series(all_canales).value_counts().reset_index()
                data_canales.columns = ['Canal', 'count']

                fig_canales = px.bar(
                    data_canales,
                    x='Canal',
                    y='count',
                    text_auto=True,
                    color='Canal',
                    color_discrete_sequence=px.colors.qualitative.Bold
                )

                # Ajustes de diseño para mejorar la legibilidad a ancho completo
                fig_canales.update_layout(
                    showlegend=False, 
                    xaxis_title="", 
                    yaxis_title="Cantidad de respuestas",
                    height=500, # Aumentamos un poco la altura para que destaque
                    xaxis={'categoryorder':'total descending'} # De más usado a menos usado
                )
                
                st.plotly_chart(fig_canales, width='stretch')
            else:
                st.info("No hay datos registrados sobre canales de comunicación.")
