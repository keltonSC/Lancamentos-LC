import pandas as pd
import streamlit as st
import re
from datetime import date
import requests

st.markdown("""
<style>
body { background-color: #f8f9fa; font-family: 'Segoe UI', sans-serif; }
[data-testid="stAppViewContainer"] > .main { padding: 2rem; }
h1, h2, h3, h4 { color: #0d47a1; }
@media (max-width: 768px) {
  .element-container { padding-left: 0 !important; padding-right: 0 !important; }
  div[data-testid="column"] { width: 100% !important; display: block; }
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
        "nome", "construtora", "status", "entrega_raw", "segmento", "vgv",
        "media_m2", "bairro", "endereco", "tipologia", "link"
    ]

    def limpar_vgv(valor):
        if isinstance(valor, str):
            valor_limpo = re.sub(r"[^\d,]", "", valor).replace(",", ".")
            return pd.to_numeric(valor_limpo, errors="coerce")
        elif isinstance(valor, (int, float)) and valor > 10_000_000:
            return valor / 10
        return valor

    df["vgv"] = df["vgv"].apply(limpar_vgv).fillna(0)
    df["entrega_dt"] = pd.to_datetime(df["entrega_raw"], errors="coerce")
    df["entrega"] = df["entrega_dt"].dt.strftime('%b/%Y')
    df["pronto"] = df["entrega_dt"].isna()
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

# Título
col1, col2 = st.columns([5, 1])
with col1:
    st.markdown("### Painel de Empreendimentos")
with col2:
    st.image("logo.png", width=70)

# Caixa de sugestão com formulário interno
with st.expander("✉️ Caso você encontre algum erro ou tenha alguma sugestão, clique aqui para nos enviar", expanded=False):
    if "form_enviado" not in st.session_state:
        st.session_state.form_enviado = False

    if st.session_state.form_enviado:
        st.success("✅ Obrigado! Sua sugestão foi enviada com sucesso. Agradecemos sua colaboração.")
    else:
        with st.form("formulario_sugestao"):
            mensagem = st.text_area("Digite sua sugestão ou correção:", placeholder="Descreva aqui...")
            enviado = st.form_submit_button("📩 Enviar")
            if enviado and mensagem.strip():
                requests.post("https://formspree.io/f/xvgadydd", data={"message": mensagem})
                st.session_state.form_enviado = True

# Sidebar com filtros
st.sidebar.header("🎯 Filtros de Busca")
enderecos = st.sidebar.multiselect("Bairros", sorted(df["bairro"].dropna().unique()))
empreendimentos = st.sidebar.multiselect("Empreendimentos", sorted(df["nome"].dropna().unique()))
construtoras = st.sidebar.multiselect("Construtoras", sorted(df["construtora"].dropna().unique()))
segmentos = st.sidebar.multiselect("Segmentos", sorted(df["segmento"].dropna().unique()))

st.sidebar.markdown("### Faixa de VGV")
vgv_min = st.sidebar.number_input("VGV mínimo (R$)", min_value=0, value=0, step=50000)
vgv_max = st.sidebar.number_input("VGV máximo (R$)", min_value=0, value=0, step=50000)

st.sidebar.markdown("### Faixa de M²")
m2_min = st.sidebar.number_input("Mínimo M²", min_value=0, value=0, step=5)
m2_max = st.sidebar.number_input("Máximo M²", min_value=0, value=0, step=5)

st.sidebar.markdown("### Previsão de Entrega")
mostrar_prontos = st.sidebar.checkbox("✅ Incluir PRONTOS", value=True)
usar_data = st.sidebar.checkbox("Filtrar por data específica")
if usar_data:
    periodo = st.sidebar.date_input("Período de entrega (dd/mm/aaaa)", [])
    if isinstance(periodo, tuple) and len(periodo) == 2:
        data_inicio, data_fim = periodo
        st.sidebar.markdown(f"🗓️ Período selecionado: **{data_inicio.strftime('%d/%m/%Y')}** até **{data_fim.strftime('%d/%m/%Y')}**")
    else:
        data_inicio = data_fim = None
else:
    data_inicio = data_fim = None

if st.sidebar.button("🔄 Limpar filtros"):
    st.query_params.clear()
    st.rerun()

# Filtros aplicados
filtrado = df.copy()
if enderecos:
    filtrado = filtrado[filtrado["bairro"].isin(enderecos)]
if empreendimentos:
    filtrado = filtrado[filtrado["nome"].isin(empreendimentos)]
if construtoras:
    filtrado = filtrado[filtrado["construtora"].isin(construtoras)]
if segmentos:
    filtrado = filtrado[filtrado["segmento"].isin(segmentos)]
if vgv_min > 0:
    filtrado = filtrado[filtrado["vgv"] >= vgv_min]
if vgv_max > 0:
    filtrado = filtrado[filtrado["vgv"] <= vgv_max]
if m2_min > 0:
    filtrado = filtrado[filtrado["metragem_max"] >= m2_min]
if m2_max > 0:
    filtrado = filtrado[filtrado["metragem_min"] <= m2_max]
if not mostrar_prontos:
    filtrado = filtrado[filtrado["pronto"] == False]
if data_inicio and data_fim:
    inicio_dt = pd.to_datetime(data_inicio)
    fim_dt = pd.to_datetime(data_fim)
    filtrado = filtrado[(filtrado["entrega_dt"] >= inicio_dt) & (filtrado["entrega_dt"] <= fim_dt)]

# Métrica
st.metric("Empreendimentos", len(filtrado))
st.markdown("---")

# Cards dos empreendimentos
if len(filtrado) > 0:
    for _, row in filtrado.iterrows():
        link_html = f"<a href='{row.link}' target='_blank' style='text-decoration: none; color: #1565c0;'>🔗</a>" if pd.notna(row.link) else ""
        maps_url = f"https://www.google.com/maps/search/?api=1&query={str(row.endereco).replace(' ', '+')},{str(row.bairro).replace(' ', '+')},Fortaleza"

        with st.container():
            st.markdown(f"""
            <div style='background-color: #ffffff; padding: 20px; margin-bottom: 20px;
                        border-left: 6px solid #0d47a1; border-radius: 10px;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.07); width: 100%;'>
                <div style='font-size: 18px; font-weight: bold;'>🏢 {row.nome} {link_html}</div>
                <div style='font-size: 14px; margin-top: 8px; line-height: 1.5;'>
                    <b>Construtora:</b> {row.construtora}<br>
                    <b>Status:</b> {row.status}<br>
                    <b>Segmento:</b> {row.segmento}<br>
                    <b>Tipologia:</b> {row.tipologia}<br>
                    <b>VGV Médio:</b> R$ {row.vgv:,.0f}<br>
                    <b>Bairro:</b> {row.bairro}<br>
                    <b>📍 Localização:</b> {row.endereco}<br>
                    <b>Média  m²:</b> {", ".join(f"{m:.0f}m²" for m in row.metragem_lista) if row.metragem_lista else "N/D"}<br>
                    <b>Previsão de entrega:</b> {row.entrega if not row.pronto else "PRONTO"}<br>
                    <a href='{maps_url}' target='_blank' style='color:#1565c0;'>📍 Ver no Google Maps</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("🔍 Nenhum empreendimento encontrado com os filtros selecionados.")
