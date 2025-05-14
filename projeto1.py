import pandas as pd
import streamlit as st
import re
import streamlit.components.v1 as components

st.markdown("""
<style>
body {
    background-color: #f8f9fa;
    font-family: 'Segoe UI', sans-serif;
}
[data-testid="stAppViewContainer"] > .main {
    padding: 2rem;
}
h1, h2, h3, h4 {
    color: #0d47a1;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def carregar_dados():
    df = pd.read_excel("empreendimentosfortaleza.xlsx", usecols=[
        "Nome do Empreendimento", "Construtora", "Status", "Previsão de Entrega",
        "Segmento", "VGV Médio", "Média  m²", "Bairro/Cidade", "Endereço",
        "Tipologia", "Atualização google earth "
    ])

    df.columns = [
        "nome", "construtora", "status", "entrega", "segmento", "vgv",
        "media_m2", "bairro", "endereco", "tipologia", "link"
    ]

    df["entrega_dt"] = pd.to_datetime(df["entrega"], errors="coerce")
    df["entrega"] = df["entrega_dt"].dt.strftime('%b/%Y')

    df["vgv"] = pd.to_numeric(
        df["vgv"].astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip(),
        errors="coerce"
    ).fillna(0)

    df["segmento"] = df["segmento"].astype(str).str.strip().str.title()

    def extrair_metragens(m):
        if pd.isna(m):
            return []
        return [float(x) for x in re.findall(r"\d+\.?\d*", str(m).replace(",", "."))]

    df["metragem_lista"] = df["media_m2"].apply(extrair_metragens)
    df["metragem_min"] = df["metragem_lista"].apply(lambda x: min(x) if x else 0)
    df["metragem_max"] = df["metragem_lista"].apply(lambda x: max(x) if x else 0)

    return df

df = carregar_dados()

# Sidebar - filtros
st.sidebar.header("🎯 Filtros de Busca")
enderecos = st.sidebar.multiselect("Bairros", sorted(df["bairro"].dropna().unique()))
empreendimentos = st.sidebar.multiselect("Empreendimentos", sorted(df["nome"].dropna().unique()))
construtoras = st.sidebar.multiselect("Construtoras", sorted(df["construtora"].dropna().unique()))
segmentos = st.sidebar.multiselect("Segmentos", sorted(df["segmento"].dropna().unique()))

st.sidebar.markdown("### Faixa de VGV")
vgv_min = st.sidebar.number_input("VGV mínimo (R$)", min_value=0, value=int(df["vgv"].min()), step=50000)
vgv_max = st.sidebar.number_input("VGV máximo (R$)", min_value=0, value=int(df["vgv"].max()), step=50000)

st.sidebar.markdown("### Faixa de M²")
m2_min = st.sidebar.number_input("Mínimo M²", min_value=0, value=int(df["metragem_min"].min()), step=5)
m2_max = st.sidebar.number_input("Máximo M²", min_value=0, value=int(df["metragem_max"].max()), step=5)

st.sidebar.markdown("### Entrega (Previsão)")
min_data = df["entrega_dt"].min()
max_data = df["entrega_dt"].max()

data_inicio, data_fim = st.sidebar.date_input("Período de entrega", value=(min_data, max_data), min_value=min_data, max_value=max_data)

meses_unicos = sorted(df["entrega"].dropna().unique().tolist())
meses_escolhidos = st.sidebar.multiselect("Ou escolha meses específicos:", options=meses_unicos)

if st.sidebar.button("🔄 Limpar filtros"):
    st.rerun()

# Título e logo
col1, col2 = st.columns([5, 1])
with col1:
    st.markdown("### Painel de Empreendimentos")
with col2:
    st.image("logo.png", width=70)

# Aplicar filtros
filtrado = df.copy()

if enderecos:
    filtrado = filtrado[filtrado["bairro"].isin(enderecos)]
if empreendimentos:
    filtrado = filtrado[filtrado["nome"].isin(empreendimentos)]
if construtoras:
    filtrado = filtrado[filtrado["construtora"].isin(construtoras)]
if segmentos:
    filtrado = filtrado[filtrado["segmento"].isin(segmentos)]

filtrado = filtrado[(filtrado["vgv"] >= vgv_min) & (filtrado["vgv"] <= vgv_max)]
filtrado = filtrado[(filtrado["metragem_max"] >= m2_min) & (filtrado["metragem_min"] <= m2_max)]
filtrado = filtrado[(filtrado["entrega_dt"] >= pd.to_datetime(data_inicio)) & (filtrado["entrega_dt"] <= pd.to_datetime(data_fim))]

if meses_escolhidos:
    filtrado = filtrado[filtrado["entrega"].isin(meses_escolhidos)]

# Resultado
col1, _, _ = st.columns(3)
col1.metric("Empreendimentos", len(filtrado))

st.markdown("---")

# Exibir cards com botão de mapa
if len(filtrado) > 0:
    for _, row in filtrado.iterrows():
        with st.container():
            st.markdown(f"""
            <div style='background-color: #ffffff; padding: 20px; margin-bottom: 20px;
                        border-left: 6px solid #0d47a1; border-radius: 10px;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.07); width: 100%;'>
                <div style='font-size: 18px; font-weight: bold;'>🏢 {row.nome}</div>
                <div style='font-size: 14px; margin-top: 8px; line-height: 1.5;'>
                    <b>Construtora:</b> {row.construtora}<br>
                    <b>Status:</b> {row.status}<br>
                    <b>Segmento:</b> {row.segmento}<br>
                    <b>Tipologia:</b> {row.tipologia}<br>
                    <b>VGV Médio:</b> R$ {row.vgv:,.0f}<br>
                    <b>Bairro:</b> {row.bairro}<br>
                    <b>📍 Localização:</b> {row.endereco}<br>
                    <b>Média  m²:</b> {", ".join(f"{m:.0f}m²" for m in row.metragem_lista) if row.metragem_lista else "N/D"}<br>
                    <b>Previsão de entrega:</b> {row.entrega}<br>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("📍 Ver mapa"):
                endereco_url = f"{row.endereco}, {row.bairro}, Fortaleza"
                mapa_html = f"""
                <iframe width="100%" height="250" frameborder="0" style="border:0; border-radius: 10px;"
                    src="https://maps.google.com/maps?q={endereco_url.replace(' ', '+')}&z=16&output=embed" allowfullscreen>
                </iframe>
                """
                components.html(mapa_html, height=250)
else:
    st.info("🔍 Aplique filtros para visualizar os empreendimentos.")
