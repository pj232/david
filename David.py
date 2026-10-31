# -*- coding: utf-8 -*-
"""
GC Bâtiment Pro — Collecte, analyse et gestion de données d'un projet de génie civil (bâtiment)
Lancement :  streamlit run App.py

Outil d'aide au pré-dimensionnement et au suivi de chantier. Les résultats de calcul sont
indicatifs (Eurocodes simplifiés) et doivent être validés par un ingénieur / bureau d'études.
"""
import io
import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="GC Bâtiment Pro",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================================
# 0. THÈME (blanc nuancé jaune, jaune dynamique, bleu nuit très contrasté)
# =====================================================================
JAUNE = "#FFC400"
JAUNE_CLAIR = "#FFF3B0"
CREME = "#FFFBE6"
NOIR = "#14213D"
ROUGE = "#D62828"
VERT = "#2A9D4F"
ORANGE = "#F77F00"
BLEU = "#1D4ED8"
GRIS = "#6B7280"
PALETTE = [NOIR, JAUNE, ROUGE, BLEU, VERT, ORANGE, GRIS]

CSS = f"""
<style>
.stApp {{ background: linear-gradient(180deg,#FFFEF5 0%,{CREME} 55%,#FFF6CC 100%); color:{NOIR}; }}
h1,h2,h3,h4,h5 {{ color:{NOIR} !important; font-weight:800 !important; }}
[data-testid="stSidebar"] {{ background:{NOIR}; border-right:5px solid {JAUNE}; }}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] div, [data-testid="stSidebar"] small {{ color:{JAUNE_CLAIR} !important; }}
.brand {{ background:{JAUNE}; color:{NOIR}; font-weight:900; font-size:1.25rem; padding:12px 14px;
          border-radius:12px; text-align:center; margin-bottom:8px; border:2px solid {JAUNE_CLAIR}; }}
.hero {{ background:linear-gradient(110deg,{JAUNE} 0%,#FFE35C 60%,{JAUNE_CLAIR} 100%);
         border:3px solid {NOIR}; border-radius:16px 16px 0 0; padding:16px 26px; }}
.hero h1 {{ margin:0; color:{NOIR} !important; font-size:1.9rem; }}
.hero p {{ margin:4px 0 0; color:{NOIR}; font-weight:600; }}
.hazard {{ height:12px; border:3px solid {NOIR}; border-top:0; border-radius:0 0 16px 16px; margin-bottom:18px;
           background:repeating-linear-gradient(45deg,{NOIR} 0 14px,{JAUNE} 14px 28px); background-size:40px 100%;
           animation:slide 1.2s linear infinite; }}
@keyframes slide {{ from {{ background-position:0 0; }} to {{ background-position:40px 0; }} }}
[data-testid="stMetric"] {{ background:#FFFFFF; border:2px solid {NOIR}; border-left:10px solid {JAUNE};
          padding:10px 16px; border-radius:12px; box-shadow:4px 4px 0 {NOIR}22; }}
[data-testid="stMetricValue"] {{ color:{NOIR}; font-weight:800; }}
.stButton>button, .stDownloadButton>button, [data-testid="stFormSubmitButton"]>button {{
    background:{JAUNE}; color:{NOIR}; border:2px solid {NOIR}; font-weight:800; border-radius:10px; }}
.stButton>button:hover, .stDownloadButton>button:hover, [data-testid="stFormSubmitButton"]>button:hover {{
    background:{NOIR}; color:{JAUNE}; border-color:{JAUNE}; }}
.stTabs [data-baseweb="tab-list"] {{ gap:6px; }}
.stTabs [data-baseweb="tab"] {{ background:#FFFFFF; border:2px solid {NOIR}; border-radius:10px 10px 0 0;
    padding:8px 16px; font-weight:700; color:{NOIR}; }}
.stTabs [aria-selected="true"] {{ background:{JAUNE}; }}
.note {{ background:{NOIR}; color:{JAUNE_CLAIR}; padding:10px 16px; border-radius:10px; border-left:8px solid {JAUNE};
         margin:8px 0 14px; font-size:0.95rem; }}
.badge-ok {{ background:{VERT}; color:white; padding:2px 10px; border-radius:20px; font-weight:700; }}
.badge-ko {{ background:{ROUGE}; color:white; padding:2px 10px; border-radius:20px; font-weight:700; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# =====================================================================
# 1. OUTILS GÉNÉRAUX
# =====================================================================
_PN = [0]


def hero(titre, sous_titre=""):
    st.markdown(
        f"<div class='hero'><h1>{titre}</h1><p>{sous_titre}</p></div><div class='hazard'></div>",
        unsafe_allow_html=True,
    )


def note(txt):
    st.markdown(f"<div class='note'>{txt}</div>", unsafe_allow_html=True)


def fmt(x, nd=2):
    try:
        return f"{x:,.{nd}f}".replace(",", " ")
    except Exception:
        return str(x)


def verdict(cond, ok_msg, ko_msg):
    if cond:
        st.success("✅ " + ok_msg)
    else:
        st.error("❌ " + ko_msg)


def pplot(fig, height=420):
    _PN[0] += 1
    fig.update_layout(
        height=height,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFDF2",
        font=dict(color=NOIR),
        colorway=PALETTE,
        margin=dict(l=20, r=20, t=55, b=20),
        title_font=dict(size=16, color=NOIR),
    )
    fig.update_xaxes(gridcolor="#EADFA6", zerolinecolor="#C9B96A")
    fig.update_yaxes(gridcolor="#EADFA6", zerolinecolor="#C9B96A")
    try:
        st.plotly_chart(fig, width="stretch", key=f"pl{_PN[0]}")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, key=f"pl{_PN[0]}")


def show_df(df, **kw):
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kw)
    except TypeError:
        st.dataframe(df, use_container_width=True, hide_index=True, **kw)


def editor(key, config=None, dynamic=True):
    S = st.session_state
    kwargs = dict(
        key=f"ed_{key}",
        column_config=config or {},
        num_rows="dynamic" if dynamic else "fixed",
        hide_index=True,
    )
    try:
        out = st.data_editor(S[key], width="stretch", **kwargs)
    except TypeError:
        out = st.data_editor(S[key], use_container_width=True, **kwargs)
    S[key] = out
    return out


# =====================================================================
# 2. DONNÉES, SCHÉMAS ET ÉTAT
# =====================================================================
COLS = {
    "releves": ["Date", "Zone", "Paramètre", "Valeur", "Unité", "Opérateur", "Remarque"],
    "journal": ["Date", "Météo", "Effectif", "Activités", "Observations"],
    "essais": ["Date", "Élément", "Classe", "Âge (j)", "Résistance (MPa)"],
    "metre": ["Lot", "Désignation", "Unité", "Quantité", "PU"],
    "taches": ["Tâche", "Début", "Durée (j)", "Avancement (%)", "Responsable", "Prédécesseurs"],
    "risques": ["Risque", "Phase", "Probabilité", "Gravité", "Mesure de maîtrise"],
    "ev": ["Mois", "PV cumulé", "EV cumulée", "AC cumulé"],
    "acier": ["Repère", "Élément", "Nb éléments", "Diamètre (mm)", "Nb barres / élément", "Longueur (m)"],
}
DATES = {"releves": ["Date"], "journal": ["Date"], "essais": ["Date"], "taches": ["Début"]}
NUMS = {
    "releves": ["Valeur"],
    "journal": ["Effectif"],
    "essais": ["Âge (j)", "Résistance (MPa)"],
    "metre": ["Quantité", "PU"],
    "taches": ["Durée (j)", "Avancement (%)"],
    "risques": ["Probabilité", "Gravité"],
    "ev": ["Mois", "PV cumulé", "EV cumulée", "AC cumulé"],
    "acier": ["Nb éléments", "Diamètre (mm)", "Nb barres / élément", "Longueur (m)"],
}
LABELS = {
    "releves": "Relevés et mesures",
    "journal": "Journal de chantier",
    "essais": "Essais béton",
    "metre": "Métré",
    "taches": "Planning",
    "risques": "Risques HSE",
    "ev": "Suivi coûts",
    "acier": "Nomenclature aciers",
}

CLASSES_BETON = ["C20/25", "C25/30", "C30/37", "C35/45", "C40/50", "C45/55", "C50/60"]
USAGES = {
    "Habitation (cat. A)": 1.5,
    "Bureaux (cat. B)": 2.5,
    "Établissement scolaire (cat. C1)": 3.0,
    "Commerce (cat. D)": 5.0,
    "Parking véhicules légers (cat. F)": 2.5,
    "Balcons": 3.5,
}
PARAMS = {
    "Affaissement (slump)": "mm",
    "Température béton": "°C",
    "Tassement": "mm",
    "Désaplomb poteau": "mm",
    "Flèche dalle": "mm",
    "Fissure (ouverture)": "mm",
    "Humidité support": "%",
    "Niveau topographique": "m",
}
TOLERANCES = {
    "Température béton": (5, 30),
    "Désaplomb poteau": (-10, 10),
    "Fissure (ouverture)": (None, 0.3),
    "Tassement": (None, 25),
}
ZONES = ["Terrassement", "Fondations", "RDC", "R+1", "R+2", "R+3", "R+4", "Toiture", "Extérieurs / VRD"]
METEO = ["Ensoleillé", "Nuageux", "Pluie légère", "Pluie forte", "Vent fort", "Forte chaleur"]
USAGE_PROJET = ["Habitation collectif", "Maison individuelle", "Bureaux", "Commerce",
                "Équipement public", "Industriel léger", "Mixte"]


def coerce(df, key):
    d = df.copy()
    for c in COLS[key]:
        if c not in d.columns:
            d[c] = None
    d = d[COLS[key]]
    for c in DATES.get(key, []):
        d[c] = pd.to_datetime(d[c], errors="coerce").dt.date
        d[c] = d[c].where(d[c].notna(), None)
    for c in NUMS.get(key, []):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d.reset_index(drop=True)


def num(df, col):
    return pd.to_numeric(df[col], errors="coerce").fillna(0.0)


def cpm(df):
    """Méthode du chemin critique (durées en jours calendaires)."""
    d = df.dropna(subset=["Tâche"]).copy()
    d["Tâche"] = d["Tâche"].astype(str)
    d = d.drop_duplicates("Tâche").reset_index(drop=True)
    d["Durée (j)"] = pd.to_numeric(d["Durée (j)"], errors="coerce").fillna(0).clip(lower=0)
    names = d["Tâche"].tolist()
    dur = dict(zip(names, d["Durée (j)"]))
    preds = {}
    for n, p in zip(names, d["Prédécesseurs"].fillna("")):
        preds[n] = [x.strip() for x in str(p).split(";") if x.strip() in dur and x.strip() != n]
    order, state = [], {}

    def visit(n):
        if state.get(n) == 2:
            return
        if state.get(n) == 1:
            raise ValueError(f"Boucle de dépendances détectée autour de « {n} »")
        state[n] = 1
        for p in preds[n]:
            visit(p)
        state[n] = 2
        order.append(n)

    for n in names:
        visit(n)
    ES, EF = {}, {}
    for n in order:
        ES[n] = max([EF[p] for p in preds[n]], default=0.0)
        EF[n] = ES[n] + dur[n]
    T = max(EF.values(), default=0.0)
    succ = {n: [m for m in names if n in preds[m]] for n in names}
    LS, LF = {}, {}
    for n in reversed(order):
        LF[n] = min([LS[s] for s in succ[n]], default=T)
        LS[n] = LF[n] - dur[n]
    d["ES"] = d["Tâche"].map(ES)
    d["EF"] = d["Tâche"].map(EF)
    d["Marge (j)"] = d["Tâche"].map(lambda n: LS[n] - ES[n])
    d["Critique"] = d["Marge (j)"].abs() < 1e-9
    return d, T


def init_state():
    S = st.session_state
    if "init" in S:
        return
    today = date.today()
    rng = np.random.default_rng(42)
    S.projet = dict(
        nom="Résidence Les Acacias R+4", moa="SCI Horizon", lieu="", usage="Habitation collectif",
        niveaux=5, surface=1250.0, budget=1_800_000.0,
        debut=today - timedelta(days=75), fin=today + timedelta(days=300), devise="€",
    )

    # Relevés
    rows = []
    for i in range(14):
        p = list(PARAMS.keys())[i % 5]
        base = {"Affaissement (slump)": 110, "Température béton": 23, "Tassement": 6,
                "Désaplomb poteau": 2, "Flèche dalle": 4}[p]
        sd = {"Affaissement (slump)": 12, "Température béton": 3, "Tassement": 1.5,
              "Désaplomb poteau": 3, "Flèche dalle": 1.2}[p]
        rows.append({
            "Date": today - timedelta(days=28 - 2 * i), "Zone": ZONES[1 + (i // 3) % 5], "Paramètre": p,
            "Valeur": round(float(base + rng.normal(0, sd)), 1), "Unité": PARAMS[p],
            "Opérateur": "Topographe" if "Tassement" in p or "Désaplomb" in p else "Labo chantier",
            "Remarque": "",
        })
    S.releves = coerce(pd.DataFrame(rows), "releves")

    # Journal
    jr = []
    acts = ["Coulage semelles axe A-C", "Ferraillage poteaux RDC", "Coffrage plancher RDC",
            "Bétonnage dalle RDC", "Montage poteaux R+1", "Ferraillage plancher R+1"]
    for i, a in enumerate(acts):
        jr.append({"Date": today - timedelta(days=10 - 2 * i), "Météo": METEO[i % 3],
                   "Effectif": int(20 + rng.integers(0, 15)), "Activités": a,
                   "Observations": "RAS" if i % 2 == 0 else "Retard livraison acier de 1 jour"})
    S.journal = coerce(pd.DataFrame(jr), "journal")

    # Essais béton
    er = []
    for i in range(7):
        er.append({"Date": today - timedelta(days=60 - 5 * i), "Élément": f"Semelles S{i+1}", "Classe": "C25/30",
                   "Âge (j)": 28.0, "Résistance (MPa)": round(float(32.5 + rng.normal(0, 2.2)), 1)})
    for i in range(5):
        er.append({"Date": today - timedelta(days=30 - 5 * i), "Élément": f"Poteaux RDC P{i+1}", "Classe": "C30/37",
                   "Âge (j)": 28.0, "Résistance (MPa)": round(float(39.0 + rng.normal(0, 2.0)), 1)})
    for i in range(4):
        er.append({"Date": today - timedelta(days=30 - 6 * i), "Élément": f"Poteaux RDC P{i+1}", "Classe": "C30/37",
                   "Âge (j)": 7.0, "Résistance (MPa)": round(float(28.0 + rng.normal(0, 1.5)), 1)})
    S.essais = coerce(pd.DataFrame(er), "essais")

    # Métré
    mt = [
        ("01 Terrassement", "Fouilles en rigole et pleine masse", "m³", 950, 18),
        ("01 Terrassement", "Évacuation des terres", "m³", 700, 12),
        ("02 Fondations", "Béton de propreté", "m³", 35, 120),
        ("02 Fondations", "Béton armé semelles C25/30", "m³", 180, 310),
        ("02 Fondations", "Acier HA fondations", "kg", 14000, 1.6),
        ("03 Structure BA", "Béton poteaux / poutres / voiles C30/37", "m³", 420, 340),
        ("03 Structure BA", "Béton planchers dalle pleine", "m³", 520, 300),
        ("03 Structure BA", "Acier HA superstructure", "kg", 95000, 1.6),
        ("03 Structure BA", "Coffrage", "m²", 5200, 28),
        ("04 Maçonnerie", "Maçonnerie agglos 20 cm", "m²", 2100, 38),
        ("04 Maçonnerie", "Cloisons de distribution", "m²", 1800, 34),
        ("05 Étanchéité", "Étanchéité toiture-terrasse", "m²", 260, 55),
        ("06 Menuiseries", "Menuiseries alu double vitrage", "u", 110, 780),
        ("07 Revêtements", "Enduits intérieurs / extérieurs", "m²", 6500, 22),
        ("07 Revêtements", "Carrelage", "m²", 1050, 48),
        ("07 Revêtements", "Peinture", "m²", 7200, 9),
        ("08 Lots techniques", "Électricité CFO / CFA", "forfait", 1, 92000),
        ("08 Lots techniques", "Plomberie sanitaire", "forfait", 1, 78000),
        ("09 VRD", "VRD et aménagements extérieurs", "forfait", 1, 65000),
    ]
    S.metre = coerce(pd.DataFrame(mt, columns=COLS["metre"]), "metre")

    # Planning
    tk = [
        ("Installation de chantier", 10, "Entreprise GO", "", 100),
        ("Terrassement", 15, "Terrassier", "Installation de chantier", 100),
        ("Fondations", 25, "Entreprise GO", "Terrassement", 100),
        ("Structure RDC", 20, "Entreprise GO", "Fondations", 100),
        ("Structure R+1", 20, "Entreprise GO", "Structure RDC", 60),
        ("Structure R+2", 20, "Entreprise GO", "Structure R+1", 0),
        ("Structure R+3", 20, "Entreprise GO", "Structure R+2", 0),
        ("Structure R+4 et toiture", 25, "Entreprise GO", "Structure R+3", 0),
        ("Maçonnerie", 30, "Maçon", "Structure R+1", 0),
        ("Étanchéité toiture", 10, "Étancheur", "Structure R+4 et toiture", 0),
        ("Électricité / plomberie", 40, "Lots techniques", "Maçonnerie", 0),
        ("Menuiseries", 25, "Menuisier", "Maçonnerie", 0),
        ("Enduits", 30, "Façadier", "Maçonnerie", 0),
        ("Carrelage et peinture", 35, "Second œuvre", "Enduits;Électricité / plomberie", 0),
        ("VRD et finitions", 20, "VRD", "Étanchéité toiture", 0),
        ("Réception", 5, "MOE / MOA", "Carrelage et peinture;Menuiseries;VRD et finitions", 0),
    ]
    tdf = pd.DataFrame([{"Tâche": a, "Début": today, "Durée (j)": b, "Avancement (%)": e, "Responsable": c,
                         "Prédécesseurs": d} for a, b, c, d, e in tk])
    sched, _ = cpm(tdf)
    tdf["Début"] = [S.projet["debut"] + timedelta(days=int(v)) for v in sched["ES"]]
    S.taches = coerce(tdf, "taches")

    # Risques
    rk = [
        ("Chute de hauteur (coffrage, rive de dalle)", "Structure", 3, 5, "Garde-corps périphériques, harnais, filets"),
        ("Effondrement de talus de fouille", "Terrassement", 2, 5, "Blindage, pente de talus, balisage"),
        ("Électrisation (réseaux provisoires)", "Installation", 2, 4, "Différentiels 30 mA, vérification périodique"),
        ("Chute d'objets / charge suspendue", "Levage", 3, 4, "Zone balisée, élingage contrôlé, casque"),
        ("Étaiement / décoffrage prématuré", "Structure", 2, 5, "Respect des délais de décoffrage, essais maturité"),
        ("Poussières / silice (découpe)", "Second œuvre", 4, 2, "Découpe à l'eau, masque FFP3"),
        ("Coactivité entre corps d'état", "Finitions", 4, 3, "Plan de coordination, planning de zones"),
    ]
    S.risques = coerce(pd.DataFrame(rk, columns=COLS["risques"]), "risques")

    # Suivi coûts
    S.ev = coerce(pd.DataFrame({
        "Mois": [1, 2, 3, 4, 5, 6, 7, 8],
        "PV cumulé": [60e3, 190e3, 380e3, 600e3, 850e3, 1.1e6, 1.35e6, 1.55e6],
        "EV cumulée": [55e3, 175e3, 350e3, 560e3, 790e3, np.nan, np.nan, np.nan],
        "AC cumulé": [58e3, 185e3, 372e3, 598e3, 842e3, np.nan, np.nan, np.nan],
    }), "ev")

    # Aciers
    S.acier = coerce(pd.DataFrame([
        ("P1", "Poteaux 30×30 (barres longitudinales)", 24, 16, 4, 3.4),
        ("P2", "Poteaux (cadres φ8)", 24, 8, 17, 1.1),
        ("PO1", "Poutres 25×45 (chap. inf.)", 18, 16, 3, 5.6),
        ("PO2", "Poutres (chap. sup.)", 18, 12, 2, 5.6),
        ("S1", "Semelles (nappe inf. sens x)", 24, 12, 10, 1.7),
    ], columns=COLS["acier"]), "acier")

    S.init = True


# =====================================================================
# 3. FONCTIONS DE CALCUL (Eurocodes simplifiés)
# =====================================================================
def parse_classe(c):
    try:
        a, b = str(c).upper().replace("C", "").split("/")
        return float(a), float(b)
    except Exception:
        return None, None


def beton_props(classe, gc=1.5):
    fck, _ = parse_classe(classe)
    fcd = fck / gc
    fctm = 0.30 * fck ** (2 / 3)
    fcm = fck + 8
    ecm = 22 * (fcm / 10) ** 0.3  # GPa
    return dict(fck=fck, fcd=fcd, fctm=fctm, fcm=fcm, Ecm=ecm)


def aire_barre(phi):
    return math.pi * phi ** 2 / 4.0


def flexion_rect(M_kNm, b, d, fck, fyk, gc=1.5, gs=1.15, dp=None):
    """Flexion simple ELU, section rectangulaire (fck<=50). b,d en mm. Retourne dict (As en mm²)."""
    fcd = fck / gc
    fyd = fyk / gs
    M = abs(M_kNm) * 1e6
    mu = M / (b * d ** 2 * fcd)
    mu_lim = 0.295  # xu/d = 0.45
    res = dict(mu=mu, mu_lim=mu_lim, As=0.0, As2=0.0, z=d, xu_d=0.0, ok=True, double=False)
    if M == 0:
        return res
    if mu <= mu_lim:
        xi = 1 - math.sqrt(1 - 2 * mu)
        z = d * (1 - xi / 2)
        res.update(As=M / (z * fyd), z=z, xu_d=xi / 0.8)
    else:
        dp = dp if dp else 0.1 * d
        xi_lim = 0.8 * 0.45
        z_lim = d * (1 - xi_lim / 2)
        M_lim = mu_lim * b * d ** 2 * fcd
        As2 = (M - M_lim) / ((d - dp) * fyd)
        As = M_lim / (z_lim * fyd) + As2
        res.update(As=As, As2=As2, z=z_lim, xu_d=0.45, double=True)
    return res


def vrd_c(b, d, fck, As):
    rho = min(As / (b * d), 0.02)
    k = min(2.0, 1 + math.sqrt(200.0 / d))
    v = 0.18 / 1.5 * k * (100 * rho * fck) ** (1 / 3)
    vmin = 0.035 * k ** 1.5 * math.sqrt(fck)
    return max(v, vmin) * b * d / 1e3  # kN


def as_min_flex(b, d, fck, fyk):
    fctm = 0.30 * fck ** (2 / 3)
    return max(0.26 * fctm / fyk * b * d, 0.0013 * b * d)


def options_barres(As_req, b, c, phit, phis=(10, 12, 14, 16, 20, 25, 32)):
    rows = []
    for phi in phis:
        n = max(2, math.ceil(As_req / aire_barre(phi))) if As_req > 0 else 2
        a_prov = n * aire_barre(phi)
        s_min = max(phi, 20.0, 25.0)
        s = (b - 2 * (c + phit) - n * phi) / (n - 1) if n > 1 else 0
        rows.append({"Barres": f"{n} HA{phi}", "φ (mm)": phi, "n": n, "As fournie (cm²)": round(a_prov / 100, 2),
                     "Espacement libre (mm)": round(s, 0), "Min. requis (mm)": s_min,
                     "Faisable (1 lit)": "✅" if s >= s_min else "❌ (2 lits)"})
    return pd.DataFrame(rows)


def dessiner_section(b, h, c, phit, phi, n, n_sup=2, phi_sup=10):
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=b, y1=h, line=dict(color=NOIR, width=3), fillcolor="#E8E4D0")
    fig.add_shape(type="rect", x0=c, y0=c, x1=b - c, y1=h - c, line=dict(color=ROUGE, width=2))
    off = c + phit
    for k, (nb, ph, y) in enumerate([(n, phi, off + phi / 2), (n_sup, phi_sup, h - off - phi_sup / 2)]):
        xs = np.linspace(off + ph / 2, b - off - ph / 2, nb) if nb > 1 else [b / 2]
        for x in xs:
            fig.add_shape(type="circle", x0=x - ph / 2, y0=y - ph / 2, x1=x + ph / 2, y1=y + ph / 2,
                          fillcolor=NOIR if k == 0 else GRIS, line=dict(color=NOIR))
    fig.update_xaxes(visible=False, range=[-b * 0.1, b * 1.1])
    fig.update_yaxes(visible=False, range=[-h * 0.05, h * 1.05], scaleanchor="x", scaleratio=1)
    fig.update_layout(title=f"Coupe — {b:.0f}×{h:.0f} mm | inf. {n}HA{phi} | sup. {n_sup}HA{phi_sup} | cadres φ{phit}")
    return fig


def eval_beton(df, use_cube=False):
    d = df.copy()
    d["Âge (j)"] = pd.to_numeric(d["Âge (j)"], errors="coerce")
    d["Résistance (MPa)"] = pd.to_numeric(d["Résistance (MPa)"], errors="coerce")
    d = d.dropna(subset=["Classe", "Âge (j)", "Résistance (MPa)"])
    rows = []
    for cl, g in d[d["Âge (j)"].round() == 28].groupby("Classe"):
        f_cyl, f_cube = parse_classe(cl)
        if f_cyl is None:
            continue
        fck = f_cube if use_cube else f_cyl
        v = g["Résistance (MPa)"].values
        n, fcm, fmin = len(v), float(v.mean()), float(v.min())
        s = float(v.std(ddof=1)) if n > 1 else float("nan")
        if n >= 15:
            c1 = fcm >= fck + 1.48 * max(s, 3.0)
            c2 = fmin >= fck - 4
            crit = "Production continue (n≥15)"
            seuil1 = fck + 1.48 * max(s, 3.0)
        elif n >= 3:
            c1 = fcm >= fck + 4
            c2 = fmin >= fck - 4
            crit = "Production initiale (3≤n<15)"
            seuil1 = fck + 4
        else:
            rows.append({"Classe": cl, "n": n, "fcm (MPa)": round(fcm, 1), "f min (MPa)": round(fmin, 1),
                         "Écart-type": None, "Seuil fcm": None, "Seuil f min": fck - 4,
                         "Critère": "n < 3", "Statut": "⚠️ Échantillon insuffisant"})
            continue
        rows.append({"Classe": cl, "n": n, "fcm (MPa)": round(fcm, 1), "f min (MPa)": round(fmin, 1),
                     "Écart-type": round(s, 2), "Seuil fcm": round(seuil1, 1), "Seuil f min": fck - 4,
                     "Critère": crit, "Statut": "✅ Conforme" if (c1 and c2) else "❌ Non conforme"})
    return pd.DataFrame(rows)


def beta_cc(t, s):
    return math.exp(s * (1 - math.sqrt(28.0 / t)))


def metre_totals(df):
    d = df.copy()
    d["Quantité"] = num(d, "Quantité")
    d["PU"] = num(d, "PU")
    d["Total"] = d["Quantité"] * d["PU"]
    d["Lot"] = d["Lot"].fillna("Divers").astype(str)
    return d


def vent_qp(z, vb0, z0, zmin):
    kr = 0.19 * (z0 / 0.05) ** 0.07
    ze = max(z, zmin)
    cr = kr * math.log(ze / z0)
    vm = cr * vb0
    iv = 1.0 / math.log(ze / z0)
    return (1 + 7 * iv) * 0.5 * 1.25 * vm ** 2 / 1000.0  # kN/m²


def spectre_ec8(T, ag, S_, TB, TC, TD, q, beta=0.2):
    if T <= TB:
        return ag * S_ * (2 / 3 + T / TB * (2.5 / q - 2 / 3))
    if T <= TC:
        return ag * S_ * 2.5 / q
    if T <= TD:
        return max(ag * S_ * 2.5 / q * TC / T, beta * ag)
    return max(ag * S_ * 2.5 / q * TC * TD / T ** 2, beta * ag)


# =====================================================================
# 4. PAGES
# =====================================================================
def page_dashboard():
    S = st.session_state
    P = S.projet
    hero("🏗️ Tableau de bord du projet", f"{P['nom']} — {P['usage']}")

    with st.expander("✏️ Informations générales du projet"):
        c1, c2, c3 = st.columns(3)
        P["nom"] = c1.text_input("Nom du projet", P["nom"])
        P["moa"] = c2.text_input("Maître d'ouvrage", P["moa"])
        P["lieu"] = c3.text_input("Localisation", P["lieu"])
        c1, c2, c3, c4 = st.columns(4)
        idx = USAGE_PROJET.index(P["usage"]) if P["usage"] in USAGE_PROJET else 0
        P["usage"] = c1.selectbox("Usage", USAGE_PROJET, index=idx)
        P["niveaux"] = int(c2.number_input("Nombre de niveaux (hors toiture)", 1, 60, int(P["niveaux"])))
        P["surface"] = float(c3.number_input("Surface de plancher totale (m²)", 20.0, 500000.0, float(P["surface"]), 50.0))
        P["budget"] = float(c4.number_input("Budget cible HT", 0.0, 1e10, float(P["budget"]), 10000.0))
        c1, c2, c3 = st.columns(3)
        P["debut"] = c1.date_input("Début des travaux", P["debut"])
        P["fin"] = c2.date_input("Fin contractuelle", P["fin"])
        devs = ["€", "FCFA", "$", "MAD", "DZD"]
        P["devise"] = c3.selectbox("Devise", devs, index=devs.index(P["devise"]) if P["devise"] in devs else 0)

    dev = P["devise"]
    t = S.taches.dropna(subset=["Tâche"])
    dur = num(t, "Durée (j)")
    avanc = float((dur * num(t, "Avancement (%)")).sum() / dur.sum()) if dur.sum() > 0 else 0.0
    mt = metre_totals(S.metre)
    total_metre = float(mt["Total"].sum())
    jours_restants = (P["fin"] - date.today()).days
    ess = eval_beton(S.essais)
    n_conf = int((ess["Statut"] == "✅ Conforme").sum()) if len(ess) else 0
    r = S.risques.copy()
    r["Score"] = num(r, "Probabilité") * num(r, "Gravité")
    n_crit = int((r["Score"] >= 15).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avancement global", f"{avanc:.1f} %")
    c2.metric("Estimation métré HT", f"{fmt(total_metre, 0)} {dev}",
              f"{(total_metre - P['budget']) / P['budget'] * 100:+.1f} % vs budget" if P["budget"] else None,
              delta_color="inverse")
    c3.metric("Ratio / m² de plancher", f"{fmt(total_metre / P['surface'], 0)} {dev}/m²")
    c4.metric("Jours avant échéance", f"{jours_restants} j")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Classes béton conformes", f"{n_conf} / {len(ess)}")
    c2.metric("Risques critiques (≥15)", n_crit)
    c3.metric("Effectif moyen (journal)", f"{num(S.journal, 'Effectif').mean():.0f} pers." if len(S.journal) else "—")
    c4.metric("Essais béton enregistrés", len(S.essais))

    g1, g2 = st.columns(2)
    with g1:
        if len(t):
            tt = t.copy()
            tt["Avancement (%)"] = num(tt, "Avancement (%)")
            fig = px.bar(tt, x="Avancement (%)", y="Tâche", orientation="h", range_x=[0, 100],
                         color="Avancement (%)", color_continuous_scale=[[0, "#FFF3B0"], [1, NOIR]],
                         title="Avancement par tâche")
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(coloraxis_showscale=False)
            pplot(fig, 480)
    with g2:
        lots = mt.groupby("Lot", as_index=False)["Total"].sum()
        if len(lots) and lots["Total"].sum() > 0:
            fig = px.pie(lots, names="Lot", values="Total", hole=0.5, title="Répartition du coût par lot",
                         color_discrete_sequence=[NOIR, JAUNE, ROUGE, BLEU, VERT, ORANGE, GRIS, "#8D6E63", "#00838F"])
            pplot(fig, 480)

    ev = S.ev.copy()
    for c in COLS["ev"]:
        ev[c] = pd.to_numeric(ev[c], errors="coerce")
    ev = ev.dropna(subset=["Mois"]).sort_values("Mois")
    if len(ev):
        fig = go.Figure()
        for col, color in [("PV cumulé", GRIS), ("EV cumulée", JAUNE), ("AC cumulé", ROUGE)]:
            fig.add_trace(go.Scatter(x=ev["Mois"], y=ev[col], name=col, mode="lines+markers",
                                     line=dict(color=color, width=4)))
        fig.update_layout(title="Courbes en S — coûts planifiés, acquis et réels", xaxis_title="Mois")
        pplot(fig, 380)


# ---------------------------------------------------------------------
def page_collecte():
    S = st.session_state
    hero("📥 Collecte de données de chantier", "Journal, relevés de contrôle, import / fusion de fichiers")
    t1, t2, t3 = st.tabs(["📓 Journal de chantier", "📏 Relevés et mesures", "📎 Import / fusion"])

    with t1:
        with st.form("form_journal", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            d = c1.date_input("Date", date.today())
            m = c2.selectbox("Météo", METEO)
            e = c3.number_input("Effectif présent", 0, 1000, 25)
            act = st.text_area("Activités réalisées")
            obs = st.text_area("Incidents / observations")
            if st.form_submit_button("➕ Ajouter l'entrée"):
                new = pd.DataFrame([{"Date": d, "Météo": m, "Effectif": e, "Activités": act, "Observations": obs}])
                S.journal = pd.concat([S.journal, new], ignore_index=True)
                st.rerun()
        editor("journal", {
            "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
            "Météo": st.column_config.SelectboxColumn("Météo", options=METEO),
            "Effectif": st.column_config.NumberColumn("Effectif", min_value=0, step=1),
            "Activités": st.column_config.TextColumn("Activités", width="large"),
            "Observations": st.column_config.TextColumn("Observations", width="large"),
        })
        j = S.journal.copy()
        j["Effectif"] = pd.to_numeric(j["Effectif"], errors="coerce")
        j = j.dropna(subset=["Date", "Effectif"])
        if len(j):
            fig = px.bar(j.sort_values("Date"), x="Date", y="Effectif", color="Météo", title="Effectif journalier et météo",
                         color_discrete_sequence=PALETTE)
            pplot(fig, 330)

    with t2:
        with st.form("form_releve", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            d = c1.date_input("Date du relevé", date.today())
            z = c2.selectbox("Zone / niveau", ZONES)
            p = c3.selectbox("Paramètre", list(PARAMS.keys()))
            v = c4.number_input("Valeur", value=0.0, step=0.1, format="%.2f")
            c1, c2 = st.columns(2)
            op = c1.text_input("Opérateur")
            rem = c2.text_input("Remarque")
            if st.form_submit_button("➕ Enregistrer le relevé"):
                new = pd.DataFrame([{"Date": d, "Zone": z, "Paramètre": p, "Valeur": v, "Unité": PARAMS[p],
                                     "Opérateur": op, "Remarque": rem}])
                S.releves = pd.concat([S.releves, new], ignore_index=True)
                st.rerun()
        editor("releves", {
            "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
            "Zone": st.column_config.SelectboxColumn("Zone", options=ZONES),
            "Paramètre": st.column_config.SelectboxColumn("Paramètre", options=list(PARAMS.keys())),
            "Valeur": st.column_config.NumberColumn("Valeur", format="%.2f"),
        })
        r = S.releves.copy()
        r["Valeur"] = pd.to_numeric(r["Valeur"], errors="coerce")
        r = r.dropna(subset=["Date", "Valeur", "Paramètre"])
        if len(r):
            params = sorted(r["Paramètre"].unique())
            sel = st.selectbox("Paramètre à analyser", params)
            rr = r[r["Paramètre"] == sel].sort_values("Date")
            fig = px.line(rr, x="Date", y="Valeur", color="Zone", markers=True, title=f"{sel} — évolution",
                          color_discrete_sequence=PALETTE)
            lo, hi = TOLERANCES.get(sel, (None, None))
            if lo is not None:
                fig.add_hline(y=lo, line_dash="dash", line_color=ROUGE)
            if hi is not None:
                fig.add_hline(y=hi, line_dash="dash", line_color=ROUGE)
            pplot(fig, 360)
            v = rr["Valeur"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Moyenne", fmt(v.mean()))
            c2.metric("Min / Max", f"{fmt(v.min())} / {fmt(v.max())}")
            c3.metric("Écart-type", fmt(v.std(ddof=1) if len(v) > 1 else 0))
            hors = int(((v < lo) if lo is not None else pd.Series(False, index=v.index)).sum()
                       + ((v > hi) if hi is not None else pd.Series(False, index=v.index)).sum())
            c4.metric("Valeurs hors tolérance", hors)

    with t3:
        key = st.selectbox("Jeu de données cible", list(LABELS.keys()), format_func=lambda k: LABELS[k])
        st.caption("Colonnes attendues : " + " | ".join(COLS[key]))
        up = st.file_uploader("Fichier CSV ou Excel", type=["csv", "xlsx"])
        if up is not None:
            try:
                df = pd.read_csv(up, sep=None, engine="python") if up.name.lower().endswith(".csv") else pd.read_excel(up)
                manque = [c for c in COLS[key] if c not in df.columns]
                if manque:
                    st.error("Colonnes manquantes : " + ", ".join(manque))
                else:
                    df = coerce(df, key)
                    show_df(df.head(20))
                    mode = st.radio("Mode", ["Ajouter aux données existantes", "Remplacer les données"], horizontal=True)
                    if st.button("📥 Importer"):
                        S[key] = pd.concat([S[key], df], ignore_index=True) if mode.startswith("Ajouter") else df
                        st.success(f"{len(df)} lignes importées dans « {LABELS[key]} ».")
                        st.rerun()
            except Exception as ex:
                st.error(f"Lecture impossible : {ex}")


# ---------------------------------------------------------------------
def page_essais():
    S = st.session_state
    hero("🧱 Essais béton et conformité", "Résistances à la compression • critères de conformité EN 206 • estimation à 28 jours")
    c1, c2 = st.columns([1, 2])
    with c1:
        eprouv = st.radio("Type d'éprouvettes", ["Cylindriques (fck)", "Cubiques (fck,cube)"])
        ciment = st.selectbox("Type de ciment (cinétique)", ["CEM 32,5 N (s=0,38)", "CEM 32,5 R / 42,5 N (s=0,25)",
                                                             "CEM 42,5 R / 52,5 (s=0,20)"], index=1)
        s_cin = {"CEM 32,5 N (s=0,38)": 0.38, "CEM 32,5 R / 42,5 N (s=0,25)": 0.25,
                 "CEM 42,5 R / 52,5 (s=0,20)": 0.20}[ciment]
    with c2:
        note("Saisir un résultat par ligne : <b>Classe</b> (ex. C25/30), <b>Âge</b> en jours et <b>Résistance</b> en MPa. "
             "La conformité est évaluée sur les essais à 28 jours (critères 1 et 2 de l'EN 206).")
    editor("essais", {
        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
        "Classe": st.column_config.SelectboxColumn("Classe", options=CLASSES_BETON),
        "Âge (j)": st.column_config.NumberColumn("Âge (j)", min_value=1, step=1),
        "Résistance (MPa)": st.column_config.NumberColumn("Résistance (MPa)", min_value=0.0, format="%.1f"),
    })
    resume = eval_beton(S.essais, use_cube=eprouv.startswith("Cub"))
    st.subheader("Conformité par classe de béton")
    if len(resume):
        show_df(resume)
    else:
        st.info("Aucun essai à 28 jours exploitable.")

    d = S.essais.copy()
    d["Âge (j)"] = pd.to_numeric(d["Âge (j)"], errors="coerce")
    d["Résistance (MPa)"] = pd.to_numeric(d["Résistance (MPa)"], errors="coerce")
    d = d.dropna(subset=["Âge (j)", "Résistance (MPa)", "Classe"])
    if len(d):
        d["Estimation f28 (MPa)"] = [round(r / beta_cc(t, s_cin), 1) if t < 28 else None
                                     for t, r in zip(d["Âge (j)"], d["Résistance (MPa)"])]
        fig = px.scatter(d, x="Âge (j)", y="Résistance (MPa)", color="Classe", hover_data=["Élément"],
                         title="Résistances mesurées vs âge", color_discrete_sequence=PALETTE)
        fig.update_traces(marker=dict(size=12, line=dict(width=2, color=NOIR)))
        for cl in d["Classe"].unique():
            f_cyl, f_cube = parse_classe(cl)
            if f_cyl:
                fig.add_hline(y=f_cube if eprouv.startswith("Cub") else f_cyl, line_dash="dot", line_color=GRIS,
                              annotation_text=f"fck {cl}")
        pplot(fig, 400)
        young = d.dropna(subset=["Estimation f28 (MPa)"])
        if len(young):
            st.subheader("Estimation de f28 à partir des essais jeunes (β<sub>cc</sub>(t), EC2 §3.1.2)".replace("<sub>", "").replace("</sub>", ""))
            show_df(young[["Élément", "Classe", "Âge (j)", "Résistance (MPa)", "Estimation f28 (MPa)"]])
        fig = px.histogram(d[d["Âge (j)"].round() == 28], x="Résistance (MPa)", color="Classe", nbins=12,
                           title="Distribution des résistances à 28 jours", color_discrete_sequence=PALETTE)
        pplot(fig, 320)


# ---------------------------------------------------------------------
def page_descente():
    S = st.session_state
    P = S.projet
    hero("⚖️ Descente de charges et pré-dimensionnement des poteaux",
         "Combinaisons ELU / ELS • dégression des charges d'exploitation (EC1) • section minimale")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### Géométrie")
        N = int(st.number_input("Nombre de planchers courants", 1, 40, int(P["niveaux"])))
        Ss = st.number_input("Surface d'influence du poteau (m²)", 4.0, 120.0, 30.0, 1.0)
        H = st.number_input("Hauteur d'étage (m)", 2.4, 6.0, 3.0, 0.1)
        bc = st.number_input("Poteau — b (cm)", 20.0, 100.0, 30.0, 5.0)
        hc = st.number_input("Poteau — h (cm)", 20.0, 100.0, 30.0, 5.0)
    with c2:
        st.markdown("#### Charges permanentes (kN/m²)")
        hd = st.number_input("Épaisseur de dalle (cm)", 12.0, 40.0, 20.0, 1.0)
        g_rev = st.number_input("Revêtements + chape", 0.0, 5.0, 1.5, 0.1)
        g_clo = st.number_input("Cloisons (équivalent réparti)", 0.0, 3.0, 1.0, 0.1)
        g_toit = st.number_input("Toiture : étanchéité + isolation + protection", 0.0, 8.0, 2.5, 0.1)
    with c3:
        st.markdown("#### Exploitation et matériaux")
        usage = st.selectbox("Usage des étages", list(USAGES.keys()))
        q_et = st.number_input("q étages (kN/m²)", 0.0, 15.0, USAGES[usage], 0.5, key=f"qe_{usage}")
        q_to = st.number_input("q toiture inaccessible (kN/m²)", 0.0, 5.0, 1.0, 0.1)
        psi0 = st.slider("ψ0 (dégression)", 0.5, 1.0, 0.7, 0.05)
        classe = st.selectbox("Classe de béton", CLASSES_BETON, index=2)
        rho = st.slider("Taux d'armatures visé ρ (%)", 0.5, 4.0, 1.0, 0.1) / 100

    pp_pot = bc / 100 * hc / 100 * H * 25.0
    G_toit = (hd / 100 * 25 + g_toit) * Ss + pp_pot
    G_et = (hd / 100 * 25 + g_rev + g_clo) * Ss + pp_pot
    Q_toit = q_to * Ss
    Q_et = q_et * Ss
    fcd = beton_props(classe)["fcd"]
    fyd = 500 / 1.15
    rows = []
    Gc, Qc_fl = 0.0, 0.0
    for k in range(0, N + 1):
        if k == 0:
            nom, Gk = "Toiture", G_toit
            Gc = Gk
            Qc = Q_toit
            Qn = Q_toit
        else:
            nom, Gk = f"Plancher {N - k + 1}", G_et
            Gc += Gk
            alpha = 1.0 if k <= 2 else (2 + (k - 2) * psi0) / k
            Qc = Q_toit + alpha * k * Q_et
            Qn = Q_et
        Ned = 1.35 * Gc + 1.5 * Qc
        Ac = Ned * 1e3 / (0.7 * (fcd + rho * fyd))  # mm²
        cote = math.ceil(math.sqrt(Ac) / 10 / 5) * 5
        rows.append({"Niveau (pied de poteau sous)": nom, "G niveau (kN)": round(Gk, 1), "Q niveau (kN)": round(Qn, 1),
                     "G cumulé (kN)": round(Gc, 1), "Q cumulé dégressé (kN)": round(Qc, 1),
                     "N_Ed ELU (kN)": round(Ned, 1), "N_ser ELS (kN)": round(Gc + Qc, 1),
                     "Côté carré mini (cm)": max(20, cote)})
    df = pd.DataFrame(rows)
    st.subheader("Résultats par niveau")
    show_df(df)
    base = df.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("N_Ed en pied (ELU)", f"{fmt(base['N_Ed ELU (kN)'], 0)} kN")
    c2.metric("N_ser en pied (ELS)", f"{fmt(base['N_ser ELS (kN)'], 0)} kN")
    c3.metric("Charge ELS / m² de plancher", f"{base['N_ser ELS (kN)'] / (Ss * (N + 1)):.1f} kN/m²")
    c4.metric("Poteau de pied conseillé", f"{int(base['Côté carré mini (cm)'])}×{int(base['Côté carré mini (cm)'])} cm")
    verdict(min(bc, hc) >= base["Côté carré mini (cm)"],
            "La section de poteau saisie est suffisante au pré-dimensionnement.",
            "La section saisie est inférieure au minimum conseillé en pied : l'augmenter.")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=df["Niveau (pied de poteau sous)"], x=df["G cumulé (kN)"], orientation="h",
                         name="G cumulé", marker_color=NOIR))
    fig.add_trace(go.Bar(y=df["Niveau (pied de poteau sous)"], x=df["Q cumulé dégressé (kN)"], orientation="h",
                         name="Q cumulé", marker_color=JAUNE))
    fig.update_layout(barmode="stack", title="Charges cumulées sur le poteau", xaxis_title="kN")
    fig.update_yaxes(autorange="reversed")
    pplot(fig, 420)
    note("Pré-dimensionnement : N<sub>Ed</sub> ≤ 0,7·(A<sub>c</sub>·f<sub>cd</sub> + ρ·A<sub>c</sub>·f<sub>yd</sub>), poteau centré. "
         "Dégression : α<sub>n</sub> = (2 + (n−2)·ψ<sub>0</sub>)/n pour n>2 étages.".replace("<sub>", "").replace("</sub>", ""))


# ---------------------------------------------------------------------
def page_poutre():
    hero("📐 Poutre en béton armé — flexion, tranchant, flèche",
         "Section rectangulaire • Eurocode 2 • armatures longitudinales, cadres et vérification de flèche")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### Géométrie")
        L = st.number_input("Portée L (m)", 1.0, 20.0, 5.5, 0.1)
        b = st.number_input("Largeur b (mm)", 150.0, 1000.0, 250.0, 10.0)
        h = st.number_input("Hauteur h (mm)", 200.0, 1500.0, 500.0, 10.0)
        c = st.number_input("Enrobage nominal c (mm)", 15.0, 60.0, 30.0, 5.0)
    with c2:
        st.markdown("#### Matériaux et armatures")
        classe = st.selectbox("Classe de béton", CLASSES_BETON, index=1)
        fyk = st.selectbox("Acier HA fyk (MPa)", [400, 500], index=1)
        phit = st.selectbox("Diamètre des cadres (mm)", [6, 8, 10, 12], index=1)
        phi = st.selectbox("Diamètre des barres inf. (mm)", [10, 12, 14, 16, 20, 25, 32], index=3)
    with c3:
        st.markdown("#### Charges et schéma statique")
        g = st.number_input("Charge permanente g hors poids propre (kN/m)", 0.0, 200.0, 18.0, 0.5)
        q = st.number_input("Charge d'exploitation q (kN/m)", 0.0, 200.0, 8.0, 0.5)
        schema = st.selectbox("Schéma statique", ["Isostatique (wL²/8)", "Travée de rive continue (≈ wL²/10)",
                                                  "Travée intermédiaire (≈ wL²/12)", "Console (wL²/2)"])
        manuel = st.checkbox("Saisir M_Ed / V_Ed manuellement")

    pr = beton_props(classe)
    fck = pr["fck"]
    pp = b * h * 25e-6
    gt = g + pp
    w_elu = 1.35 * gt + 1.5 * q
    coef = {"Isostatique (wL²/8)": (1 / 8, 0.5, 1.0), "Travée de rive continue (≈ wL²/10)": (1 / 10, 0.6, 1.3),
            "Travée intermédiaire (≈ wL²/12)": (1 / 12, 0.5, 1.5), "Console (wL²/2)": (0.5, 1.0, 0.4)}[schema]
    MEd = coef[0] * w_elu * L ** 2
    VEd = coef[1] * w_elu * L
    if manuel:
        MEd = st.number_input("M_Ed (kN·m)", 0.0, 5000.0, float(round(MEd, 1)), 1.0)
        VEd = st.number_input("V_Ed (kN)", 0.0, 5000.0, float(round(VEd, 1)), 1.0)
    d = h - c - phit - phi / 2
    res = flexion_rect(MEd, b, d, fck, fyk, dp=c + phit + 10)
    asmin = as_min_flex(b, d, fck, fyk)
    as_req = max(res["As"], asmin)
    as_max = 0.04 * b * h

    st.subheader("1) Flexion à l'ELU")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Poids propre", f"{pp:.2f} kN/m")
    c2.metric("w_ELU", f"{w_elu:.1f} kN/m")
    c3.metric("M_Ed", f"{MEd:.1f} kN·m")
    c4.metric("V_Ed", f"{VEd:.1f} kN")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hauteur utile d", f"{d:.0f} mm")
    c2.metric("μ = M/(b d² fcd)", f"{res['mu']:.3f}")
    c3.metric("A_s requise", f"{res['As'] / 100:.2f} cm²")
    c4.metric("A_s,min", f"{asmin / 100:.2f} cm²")
    if res["double"]:
        st.warning(f"μ > μ_lim ({res['mu_lim']:.3f}) : armatures comprimées nécessaires A_s2 = {res['As2'] / 100:.2f} cm². "
                   "Il est préférable d'augmenter la hauteur de la section.")
    verdict(as_req <= as_max, "Pourcentage d'armatures ≤ 4 % de A_c.", "A_s > 4 % A_c : section à augmenter.")

    opts = options_barres(as_req, b, c, phit)
    st.markdown("**Choix des armatures inférieures (tous diamètres)**")
    show_df(opts)
    n = max(2, math.ceil(as_req / aire_barre(phi)))
    as_prov = n * aire_barre(phi)
    st.info(f"Choix retenu : **{n} HA{phi}** = {as_prov / 100:.2f} cm² (utilisation {as_req / as_prov * 100:.0f} %).")

    st.subheader("2) Effort tranchant")
    vrdc = vrd_c(b, d, fck, as_prov)
    z = 0.9 * d
    nu1 = 0.6 * (1 - fck / 250)
    fywd = 500 / 1.15 if fyk >= 500 else 400 / 1.15
    cot = None
    for cc in np.arange(2.5, 0.99, -0.1):
        vrdmax = b * z * nu1 * (fck / 1.5) / (cc + 1 / cc) / 1e3
        if vrdmax >= VEd:
            cot = float(cc)
            break
    asw_min_ratio = 0.08 * math.sqrt(fck) / fyk
    Asw = 2 * aire_barre(phit)
    c1, c2, c3 = st.columns(3)
    c1.metric("V_Rd,c (sans armatures)", f"{vrdc:.1f} kN")
    c2.metric("V_Ed", f"{VEd:.1f} kN")
    if cot is None:
        c3.metric("V_Rd,max", "insuffisant")
        st.error("❌ V_Ed > V_Rd,max : bielle de béton écrasée — augmenter b, h ou la classe de béton.")
        s_chosen = None
    else:
        s_req = Asw * z * fywd * cot / (VEd * 1e3) if VEd * 1e3 > 0 else 1e9
        s_max = min(0.75 * d, Asw * fyk / (0.08 * math.sqrt(fck) * b))
        s_use = min(s_req, s_max) if VEd > vrdc else s_max
        s_chosen = max(50, int(math.floor(s_use / 5.0) * 5))
        c3.metric("Espacement des cadres", f"cadres φ{phit} (2 brins) @ {s_chosen} mm")
        st.caption(f"cotθ = {cot:.1f} • s requis = {min(s_req, 1e5):.0f} mm • s max = {s_max:.0f} mm "
                   f"• ρw,min = {asw_min_ratio * 100:.3f} %")
        if VEd <= vrdc:
            st.success("V_Ed ≤ V_Rd,c : armatures d'effort tranchant minimales suffisantes.")

    st.subheader("3) Flèche (méthode l/d simplifiée, EC2 §7.4.2)")
    K = coef[2]
    rho_ = as_req / (b * d)
    rho0 = 1e-3 * math.sqrt(fck)
    if rho_ <= rho0:
        ld = K * (11 + 1.5 * math.sqrt(fck) * rho0 / rho_ + 3.2 * math.sqrt(fck) * (rho0 / rho_ - 1) ** 1.5)
    else:
        rho_p = res["As2"] / (b * d)
        ld = K * (11 + 1.5 * math.sqrt(fck) * rho0 / (rho_ - rho_p) + math.sqrt(fck) / 12 * math.sqrt(rho_p / rho0))
    ld *= min(1.5, 500 / (fyk * as_req / as_prov))
    ld_act = L * 1000 / d
    c1, c2 = st.columns(2)
    c1.metric("(l/d) limite", f"{ld:.1f}")
    c2.metric("(l/d) réel", f"{ld_act:.1f}")
    verdict(ld_act <= ld, "Flèche non vérifiée par calcul nécessaire : critère l/d respecté.",
            "Critère l/d non respecté : augmenter h ou calculer la flèche précisément.")

    pplot(dessiner_section(b, h, c, phit, phi, n), 440)
    note("Hypothèses : fck ≤ 50 MPa, α<sub>cc</sub>=1, γ<sub>c</sub>=1,5, γ<sub>s</sub>=1,15, x<sub>u</sub>/d ≤ 0,45. "
         "Les moments d'appui, la redistribution et les dispositions constructives restent à vérifier.".replace("<sub>", "").replace("</sub>", ""))


# ---------------------------------------------------------------------
def page_poteau_dalle():
    t1, t2 = st.tabs(["🏛️ Poteau (compression centrée)", "🧩 Dalle pleine"])
    with t1:
        hero("🏛️ Poteau en béton armé", "Méthode forfaitaire (type BAEL) • élancement • armatures longitudinales et transversales")
        c1, c2, c3 = st.columns(3)
        Ned = c1.number_input("N_Ed (kN)", 50.0, 20000.0, 1800.0, 50.0)
        b = c1.number_input("b (mm)", 200.0, 1000.0, 300.0, 10.0)
        h = c1.number_input("h (mm)", 200.0, 1000.0, 300.0, 10.0)
        H = c2.number_input("Hauteur libre (m)", 1.5, 8.0, 3.0, 0.1)
        kf = c2.selectbox("Liaisons (l0/L)", [0.7, 0.85, 1.0, 2.0], index=1,
                          format_func=lambda v: {0.7: "0,70 encastré-articulé", 0.85: "0,85 poteau de bâtiment courant",
                                                 1.0: "1,00 articulé-articulé", 2.0: "2,00 console"}[v])
        classe = c3.selectbox("Classe de béton", CLASSES_BETON, index=2, key="pot_cl")
        fyk = c3.selectbox("fyk (MPa)", [400, 500], index=1, key="pot_fy")
        fck = beton_props(classe)["fck"]
        fyd = fyk / 1.15
        l0 = kf * H
        i_min = min(b, h) / math.sqrt(12)
        lam = l0 * 1000 / i_min
        alpha = 0.85 / (1 + 0.2 * (lam / 35) ** 2) if lam <= 50 else 0.6 * (50 / lam) ** 2
        Br = (b - 20) * (h - 20)
        Ac = b * h
        as_calc = (Ned * 1e3 / alpha - Br * fck / 1.35) / fyd
        as_min = max(0.10 * Ned * 1e3 / fyd, 0.002 * Ac, 4 * 100 * 2 * (b + h) / 1000)
        as_use = max(as_calc, as_min)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Élancement λ", f"{lam:.1f}")
        c2.metric("Coefficient α", f"{alpha:.3f}")
        c3.metric("A_s calculée", f"{max(as_calc, 0) / 100:.2f} cm²")
        c4.metric("A_s retenue (≥ min)", f"{as_use / 100:.2f} cm²")
        verdict(lam <= 70, "Poteau dans le domaine de validité (λ ≤ 70).", "Poteau trop élancé : augmenter la section.")
        verdict(as_use <= 0.04 * Ac, "A_s ≤ 4 % de A_c.", "A_s > 4 % A_c : augmenter la section ou la classe de béton.")
        rows = []
        for phi in [12, 14, 16, 20, 25, 32]:
            n = max(4, math.ceil(as_use / aire_barre(phi)))
            n += n % 2
            rows.append({"Barres": f"{n} HA{phi}", "As fournie (cm²)": round(n * aire_barre(phi) / 100, 2),
                         "φt cadres (mm)": max(6, math.ceil(phi / 4)),
                         "Espacement cadres max (mm)": int(min(20 * phi, min(b, h), 400))})
        show_df(pd.DataFrame(rows))
        Nrd = alpha * (Br * fck / 1.35 + (as_use) * fyd) / 1e3
        st.info(f"Résistance N_Rd = {Nrd:.0f} kN pour N_Ed = {Ned:.0f} kN → taux de travail {Ned / Nrd * 100:.0f} %.")

    with t2:
        hero("🧩 Dalle pleine en béton armé", "Appuyée sur 4 côtés • coefficients μx, μy • armatures par mètre • poinçon / tranchant simplifié")
        c1, c2, c3 = st.columns(3)
        lx = c1.number_input("Petite portée lx (m)", 1.0, 10.0, 4.0, 0.1)
        ly = c1.number_input("Grande portée ly (m)", 1.0, 15.0, 5.5, 0.1)
        hd = c1.number_input("Épaisseur h (mm)", 100.0, 500.0, 180.0, 10.0)
        g = c2.number_input("g hors poids propre (kN/m²)", 0.0, 20.0, 2.5, 0.1)
        q = c2.number_input("q exploitation (kN/m²)", 0.0, 20.0, 2.5, 0.5)
        cc = c2.number_input("Enrobage c (mm)", 15.0, 50.0, 25.0, 5.0)
        classe = c3.selectbox("Classe de béton", CLASSES_BETON, index=1, key="dal_cl")
        fyk = c3.selectbox("fyk (MPa)", [400, 500], index=1, key="dal_fy")
        phi = c3.selectbox("φ armatures (mm)", [8, 10, 12, 14, 16], index=1)
        cont = c3.selectbox("Continuité", ["Appuyée simplement", "Continue (Mt=0,75M0 ; Ma=0,5M0)"])
        if lx > ly:
            lx, ly = ly, lx
        fck = beton_props(classe)["fck"]
        a = lx / ly
        w = 1.35 * (hd / 1000 * 25 + g) + 1.5 * q
        if a < 0.4:
            M0x, M0y = w * lx ** 2 / 8, 0.0
            sens = "Portant dans un seul sens (lx)"
        else:
            mux = 1 / (8 * (1 + 2.4 * a ** 3))
            muy = a ** 2 * (1 - 0.95 * (1 - a) ** 2)
            M0x = mux * w * lx ** 2
            M0y = muy * M0x
            sens = f"Portant dans 2 sens (α = {a:.2f})"
        ft, fa = (1.0, 0.0) if cont.startswith("Appuy") else (0.75, 0.5)
        dx = hd - cc - phi / 2
        dy = dx - phi
        out = []
        for nom, M, dd in [("Travée sens x (lx)", ft * M0x, dx), ("Travée sens y (ly)", ft * M0y, dy),
                           ("Appui sens x", fa * M0x, dx)]:
            r = flexion_rect(M, 1000.0, dd, fck, fyk)
            amin = as_min_flex(1000.0, dd, fck, fyk)
            if nom == "Travée sens y (ly)":
                amin = max(amin, 0.2 * (ft * M0x and flexion_rect(ft * M0x, 1000.0, dx, fck, fyk)["As"]))
            if M == 0:
                out.append({"Section": nom, "M (kN·m/m)": 0.0, "As (cm²/m)": 0.0, "Espacement φ (mm)": "—", "Remarque": "—"})
                continue
            asu = max(r["As"], amin)
            s = min(math.floor(1000 * aire_barre(phi) / asu / 25) * 25, min(3 * hd, 400))
            out.append({"Section": nom, "M (kN·m/m)": round(M, 2), "As (cm²/m)": round(asu / 100, 2),
                        "Espacement φ (mm)": f"φ{int(phi)} @ {int(s)}",
                        "Remarque": "⚠️ μ>μlim" if r["double"] else "OK"})
        c1, c2, c3 = st.columns(3)
        c1.metric("Charge ELU", f"{w:.1f} kN/m²")
        c2.metric("Fonctionnement", sens)
        c3.metric("h min indicative (lx/30)", f"{lx * 1000 / 30:.0f} mm")
        show_df(pd.DataFrame(out))
        VEd = w * lx / 2
        asv = max([float(str(o['As (cm²/m)']).replace('—', '0')) for o in out]) * 100
        vrdc = vrd_c(1000.0, dx, fck, max(asv, 1.0))
        verdict(VEd <= vrdc, f"Tranchant : V_Ed = {VEd:.1f} kN/m ≤ V_Rd,c = {vrdc:.1f} kN/m (pas d'armatures d'effort tranchant).",
                f"Tranchant : V_Ed = {VEd:.1f} kN/m > V_Rd,c = {vrdc:.1f} kN/m → augmenter h.")
        verdict(hd >= lx * 1000 / 35, "Épaisseur compatible avec la limitation de flèche usuelle (lx/35).",
                "Épaisseur faible vis-à-vis de la flèche : vérifier ou augmenter h.")


# ---------------------------------------------------------------------
def page_fondations():
    hero("🦶 Fondations et sol", "Semelle isolée • capacité portante • tassement • mur de soutènement / voile enterré")
    t1, t2, t3 = st.tabs(["🟫 Semelle isolée", "🌍 Capacité portante et tassement", "🧱 Mur de soutènement"])

    with t1:
        c1, c2, c3 = st.columns(3)
        Ned = c1.number_input("N_Ed ELU (kN)", 50.0, 30000.0, 1800.0, 50.0)
        Nser = c1.number_input("N_ser ELS (kN)", 50.0, 30000.0, 1300.0, 50.0)
        qadm = c2.number_input("Contrainte admissible du sol (kPa)", 50.0, 1500.0, 200.0, 10.0)
        a = c2.number_input("Côté du poteau a (cm)", 20.0, 100.0, 30.0, 5.0)
        D = c2.number_input("Profondeur d'assise D (m)", 0.3, 6.0, 1.5, 0.1)
        classe = c3.selectbox("Classe de béton", CLASSES_BETON, index=1, key="sem_cl")
        fyk = c3.selectbox("fyk (MPa)", [400, 500], index=1, key="sem_fy")
        phi = c3.selectbox("φ armatures (mm)", [10, 12, 14, 16, 20], index=1, key="sem_phi")
        gam_s = 18.0
        B = 1.0
        for _ in range(20):
            h = max(0.4, (B - a / 100) / 4 + 0.05)
            W = B * B * h * 25 + B * B * (D - h) * gam_s
            B_new = math.ceil(math.sqrt((Nser + W) / qadm) / 0.05) * 0.05
            if abs(B_new - B) < 1e-6:
                break
            B = B_new
        h = math.ceil(max(0.4, (B - a / 100) / 4 + 0.05) / 0.05) * 0.05
        d = h - 0.06
        fyd = fyk / 1.15
        As = Ned * (B - a / 100) / (8 * d * fyd * 1e3) * 1e4  # cm² par direction
        sig = (Nser + B * B * h * 25 + B * B * (D - h) * gam_s) / (B * B)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Côté B = L", f"{B:.2f} m")
        c2.metric("Hauteur h", f"{h:.2f} m")
        c3.metric("σ sol ELS", f"{sig:.0f} kPa")
        c4.metric("A_s par direction", f"{As:.1f} cm²")
        verdict(sig <= qadm, "σ_sol ≤ q_adm.", "σ_sol > q_adm : élargir la semelle.")
        rows = []
        for ph in [10, 12, 14, 16, 20]:
            n = math.ceil(As * 100 / aire_barre(ph))
            rows.append({"Barres": f"{n} HA{ph} par direction", "Espacement (mm)": round((B * 1000 - 120) / max(n - 1, 1)),
                         "Longueur d'ancrage mini (mm)": round(40 * ph)})
        show_df(pd.DataFrame(rows))
        fig = go.Figure()
        fig.add_shape(type="rect", x0=0, y0=0, x1=B, y1=B, line=dict(color=NOIR, width=3), fillcolor="#E8E4D0")
        fig.add_shape(type="rect", x0=(B - a / 100) / 2, y0=(B - a / 100) / 2, x1=(B + a / 100) / 2, y1=(B + a / 100) / 2,
                      fillcolor=JAUNE, line=dict(color=NOIR, width=2))
        fig.update_xaxes(visible=False, range=[-0.2, B + 0.2])
        fig.update_yaxes(visible=False, scaleanchor="x", range=[-0.2, B + 0.2])
        fig.update_layout(title=f"Vue en plan — semelle {B:.2f} × {B:.2f} m, poteau {a:.0f} cm")
        pplot(fig, 360)
        note("Méthode des bielles : A_s = N_Ed·(B − a)/(8·d·f_yd) ; semelle rigide si h ≥ (B − a)/4 + 5 cm. "
             "Poinçonnement et ancrage à vérifier.")

    with t2:
        c1, c2, c3 = st.columns(3)
        cc = c1.number_input("Cohésion c (kPa)", 0.0, 300.0, 5.0, 1.0)
        ph = c1.number_input("Angle de frottement φ (°)", 0.0, 45.0, 28.0, 1.0)
        gam = c2.number_input("Poids volumique γ (kN/m³)", 12.0, 24.0, 18.0, 0.5)
        Df = c2.number_input("Encastrement D (m)", 0.0, 6.0, 1.5, 0.1, key="cp_D")
        Bf = c3.number_input("Largeur B (m)", 0.4, 10.0, 2.0, 0.1)
        Lf = c3.number_input("Longueur L (m) (= B si carrée)", 0.4, 100.0, 2.0, 0.1)
        FS = c3.slider("Coefficient de sécurité", 2.0, 4.0, 3.0, 0.5)
        phr = math.radians(ph)
        Nq = math.exp(math.pi * math.tan(phr)) * math.tan(math.radians(45 + ph / 2)) ** 2
        Nc = (Nq - 1) / math.tan(phr) if ph > 0 else 5.14
        Ng = 2 * (Nq + 1) * math.tan(phr)
        sc = 1 + (Bf / Lf) * (Nq / Nc)
        sq = 1 + (Bf / Lf) * math.tan(phr)
        sg = 1 - 0.4 * (Bf / Lf)
        qu = cc * Nc * sc + gam * Df * Nq * sq + 0.5 * gam * Bf * Ng * sg
        qa = (qu - gam * Df) / FS + gam * Df
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Nq / Nc / Nγ", f"{Nq:.1f} / {Nc:.1f} / {Ng:.1f}")
        c2.metric("q ultime", f"{qu:.0f} kPa")
        c3.metric("q admissible", f"{qa:.0f} kPa")
        c4.metric("Charge admissible", f"{qa * Bf * Lf:.0f} kN")
        st.markdown("##### Tassement élastique indicatif")
        c1, c2, c3 = st.columns(3)
        Es = c1.number_input("Module du sol Es (MPa)", 2.0, 500.0, 30.0, 1.0)
        nu = c2.number_input("Coefficient de Poisson", 0.1, 0.5, 0.3, 0.05)
        qapp = c3.number_input("Pression appliquée (kPa)", 10.0, 1500.0, min(qa, 200.0), 10.0)
        a_eq = math.sqrt(Bf * Lf / math.pi)
        s = qapp * math.pi * a_eq * (1 - nu ** 2) / (2 * Es * 1000) * 1000
        c1, c2 = st.columns(2)
        c1.metric("Tassement (semelle rigide)", f"{s:.1f} mm")
        c2.metric("Seuil usuel", "25 mm")
        verdict(s <= 25, "Tassement ≤ 25 mm.", "Tassement élevé : élargir la semelle ou améliorer le sol.")
        Bs = np.linspace(0.5, 5, 30)
        qs = []
        for bb in Bs:
            sc_ = 1 + (bb / Lf) * (Nq / Nc)
            sq_ = 1 + (bb / Lf) * math.tan(phr)
            sg_ = 1 - 0.4 * (bb / Lf)
            qs.append(((cc * Nc * sc_ + gam * Df * Nq * sq_ + 0.5 * gam * bb * Ng * sg_) - gam * Df) / FS + gam * Df)
        fig = px.line(x=Bs, y=qs, labels={"x": "Largeur B (m)", "y": "q admissible (kPa)"}, title="q admissible en fonction de B")
        fig.update_traces(line=dict(color=NOIR, width=4))
        pplot(fig, 330)
        note("Formule de Terzaghi/Vesic généralisée ; données géotechniques à confirmer par étude de sol (G2).")

    with t3:
        c1, c2, c3 = st.columns(3)
        Hm = c1.number_input("Hauteur de terres H (m)", 1.0, 10.0, 3.0, 0.1)
        Bb = c1.number_input("Largeur de semelle B (m)", 0.5, 8.0, 2.2, 0.1)
        tb = c1.number_input("Épaisseur de semelle (m)", 0.2, 1.0, 0.4, 0.05)
        ts = c2.number_input("Épaisseur du voile (m)", 0.15, 0.8, 0.25, 0.01)
        lt = c2.number_input("Talon avant (patin) (m)", 0.0, 3.0, 0.5, 0.1)
        phs = c2.number_input("φ du remblai (°)", 20.0, 45.0, 30.0, 1.0)
        gs_ = c3.number_input("γ remblai (kN/m³)", 14.0, 22.0, 18.0, 0.5, key="mur_g")
        qs_ = c3.number_input("Surcharge q (kPa)", 0.0, 50.0, 10.0, 1.0)
        mu = c3.number_input("Frottement base-sol tanδ", 0.2, 0.9, 0.5, 0.05)
        Ka = math.tan(math.radians(45 - phs / 2)) ** 2
        Pa1 = 0.5 * Ka * gs_ * Hm ** 2
        Pa2 = Ka * qs_ * Hm
        Mo = Pa1 * Hm / 3 + Pa2 * Hm / 2
        lh = Bb - lt - ts
        W1 = ts * (Hm - tb) * 25
        W2 = Bb * tb * 25
        W3 = lh * (Hm - tb) * gs_
        W4 = qs_ * lh
        Mr = W1 * (lt + ts / 2) + W2 * Bb / 2 + (W3 + W4) * (lt + ts + lh / 2)
        SV = W1 + W2 + W3 + W4
        FSr = Mr / Mo if Mo else 99
        FSg = SV * mu / (Pa1 + Pa2)
        e = Bb / 2 - (Mr - Mo) / SV
        qmax = SV / Bb * (1 + 6 * e / Bb) if abs(e) <= Bb / 6 else 2 * SV / (3 * (Bb / 2 - e))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ka", f"{Ka:.3f}")
        c2.metric("Poussée totale", f"{Pa1 + Pa2:.1f} kN/m")
        c3.metric("FS renversement", f"{FSr:.2f}")
        c4.metric("FS glissement", f"{FSg:.2f}")
        verdict(FSr >= 1.5, "Renversement : FS ≥ 1,5.", "Renversement insuffisant (FS < 1,5).")
        verdict(FSg >= 1.5, "Glissement : FS ≥ 1,5.", "Glissement insuffisant (FS < 1,5) : ajouter une bêche ou élargir la base.")
        verdict(abs(e) <= Bb / 6, f"Résultante dans le tiers central (e = {e:.2f} m) ; σ_max = {qmax:.0f} kPa.",
                f"Résultante hors du tiers central (e = {e:.2f} m) ; σ_max ≈ {qmax:.0f} kPa.")
        fig = go.Figure()
        fig.add_shape(type="rect", x0=0, y0=0, x1=Bb, y1=tb, fillcolor="#CFC9A6", line=dict(color=NOIR, width=2))
        fig.add_shape(type="rect", x0=lt, y0=tb, x1=lt + ts, y1=Hm, fillcolor="#CFC9A6", line=dict(color=NOIR, width=2))
        fig.add_shape(type="rect", x0=lt + ts, y0=tb, x1=Bb, y1=Hm, fillcolor=JAUNE_CLAIR, line=dict(color=ORANGE, dash="dot"))
        fig.update_xaxes(visible=False, range=[-0.5, Bb + 0.5])
        fig.update_yaxes(visible=False, scaleanchor="x", range=[-0.3, Hm + 0.5])
        fig.update_layout(title="Coupe du mur de soutènement")
        pplot(fig, 360)


# ---------------------------------------------------------------------
def page_actions():
    S = st.session_state
    P = S.projet
    hero("🌬️ Actions climatiques et sismiques", "Vent (EC1-1-4 simplifié) • neige (EC1-1-3) • séisme (EC8, force latérale équivalente)")
    t1, t2, t3 = st.tabs(["🌬️ Vent", "❄️ Neige", "🌍 Séisme"])

    with t1:
        c1, c2, c3 = st.columns(3)
        N = c1.number_input("Nombre de niveaux", 1, 60, int(P["niveaux"]), key="v_N")
        hn = c1.number_input("Hauteur d'étage (m)", 2.5, 5.0, 3.0, 0.1, key="v_h")
        b = c2.number_input("Largeur face au vent b (m)", 3.0, 200.0, 25.0, 1.0)
        dd = c2.number_input("Profondeur d (m)", 3.0, 200.0, 15.0, 1.0)
        vb0 = c3.number_input("Vitesse de référence vb,0 (m/s)", 15.0, 60.0, 26.0, 1.0)
        terr = {"0 – Mer / côte": (0.003, 1), "I – Lacs / plaine plate": (0.01, 1), "II – Rural, obstacles rares": (0.05, 2),
                "III – Suburbain / forêt": (0.3, 5), "IV – Urbain dense": (1.0, 10)}
        tk = c3.selectbox("Catégorie de terrain", list(terr.keys()), index=2)
        z0, zmin = terr[tk]
        Htot = N * hn
        hd_ = Htot / dd
        cpD = float(np.interp(hd_, [0.25, 1, 5], [0.7, 0.8, 0.8]))
        cpE = float(np.interp(hd_, [0.25, 1, 5], [-0.3, -0.5, -0.7]))
        qpH = vent_qp(Htot, vb0, z0, zmin)
        rows = []
        for i in range(1, int(N) + 1):
            z = i * hn
            qz = vent_qp(z, vb0, z0, zmin)
            F = b * hn * (qz * cpD + qpH * abs(cpE))
            rows.append({"Niveau": i, "z (m)": round(z, 1), "qp(z) (kN/m²)": round(qz, 3), "Force F_i (kN)": round(F, 1)})
        df = pd.DataFrame(rows)
        Fb = df["Force F_i (kN)"].sum()
        Mb = float((df["Force F_i (kN)"] * df["z (m)"]).sum())
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("h/d", f"{hd_:.2f}")
        c2.metric("c_pe (D / E)", f"{cpD:+.2f} / {cpE:+.2f}")
        c3.metric("Effort tranchant en base", f"{Fb:.0f} kN")
        c4.metric("Moment de renversement", f"{Mb:.0f} kN·m")
        g1, g2 = st.columns(2)
        with g1:
            fig = px.bar(df, y="z (m)", x="Force F_i (kN)", orientation="h", title="Force de vent par niveau",
                         color_discrete_sequence=[NOIR])
            pplot(fig, 360)
        with g2:
            zz = np.linspace(max(zmin, 1), max(Htot, 5), 40)
            fig = px.line(x=[vent_qp(z, vb0, z0, zmin) for z in zz], y=zz,
                          labels={"x": "qp (kN/m²)", "y": "z (m)"}, title="Profil de pression dynamique de pointe")
            fig.update_traces(line=dict(color=ROUGE, width=4))
            pplot(fig, 360)
        show_df(df)

    with t2:
        c1, c2, c3 = st.columns(3)
        sk = c1.number_input("Charge de neige au sol sk (kN/m²)", 0.0, 6.0, 0.45, 0.05)
        pente = c2.number_input("Pente de toiture α (°)", 0.0, 80.0, 5.0, 1.0)
        ce = c3.number_input("Ce (exposition)", 0.5, 1.2, 1.0, 0.1)
        ct = c3.number_input("Ct (thermique)", 0.5, 1.0, 1.0, 0.1)
        mu = 0.8 if pente <= 30 else (0.8 * (60 - pente) / 30 if pente <= 60 else 0.0)
        s = mu * ce * ct * sk
        c1, c2 = st.columns(2)
        c1.metric("Coefficient de forme μ1", f"{mu:.2f}")
        c2.metric("Charge de neige sur toiture s", f"{s:.2f} kN/m²")
        note("Toiture à un seul versant ou terrasse sans accumulation ; les accumulations (acrotères, noues) sont à ajouter séparément.")

    with t3:
        c1, c2, c3 = st.columns(3)
        N = int(c1.number_input("Nombre de niveaux", 1, 60, int(P["niveaux"]), key="s_N"))
        hn = c1.number_input("Hauteur d'étage (m)", 2.5, 5.0, 3.0, 0.1, key="s_h")
        Sniv = c1.number_input("Surface par niveau (m²)", 50.0, 10000.0, float(round(P["surface"] / max(N, 1), 0)), 10.0)
        g_s = c2.number_input("Charges permanentes sismiques (kN/m²)", 3.0, 15.0, 7.5, 0.5)
        q_s = c2.number_input("Charges d'exploitation (kN/m²)", 0.0, 10.0, 1.5, 0.5, key="s_q")
        psiE = c2.slider("ψE = φ·ψ2", 0.1, 1.0, 0.3, 0.05)
        agr = c3.number_input("Accélération de référence a_gR (m/s²)", 0.2, 4.0, 1.1, 0.1)
        gI = c3.selectbox("Catégorie d'importance", ["I (0,8)", "II (1,0)", "III (1,2)", "IV (1,4)"], index=1)
        gI = float(gI.split("(")[1].replace(",", ".").replace(")", ""))
        sol = c3.selectbox("Classe de sol", ["A", "B", "C", "D", "E"], index=1)
        qf = st.slider("Coefficient de comportement q", 1.5, 5.0, 3.0, 0.5)
        ctyp = st.selectbox("Structure (Ct)", ["Portiques béton (0,075)", "Portiques acier (0,085)", "Autres / voiles (0,05)"])
        Ct = float(ctyp.split("(")[1].replace(",", ".").replace(")", ""))
        sp = {"A": (1.0, 0.15, 0.4, 2.0), "B": (1.2, 0.15, 0.5, 2.0), "C": (1.15, 0.2, 0.6, 2.0),
              "D": (1.35, 0.2, 0.8, 2.0), "E": (1.4, 0.15, 0.5, 2.0)}[sol]
        S_, TB, TC, TD = sp
        ag = agr * gI
        Htot = N * hn
        T1 = Ct * Htot ** 0.75
        Sd = spectre_ec8(T1, ag, S_, TB, TC, TD, qf)
        Wi = (g_s + psiE * q_s) * Sniv
        W = Wi * N
        lam = 0.85 if (T1 <= 2 * TC and N > 2) else 1.0
        Fb = Sd / 9.81 * W * lam
        zi = np.array([hn * (i + 1) for i in range(N)])
        Fi = Fb * zi / zi.sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Période T1", f"{T1:.2f} s")
        c2.metric("Sd(T1)", f"{Sd:.2f} m/s²")
        c3.metric("Poids sismique total", f"{W:.0f} kN")
        c4.metric("Effort tranchant sismique Fb", f"{Fb:.0f} kN")
        st.caption(f"Fb / W = {Fb / W * 100:.1f} % • λ = {lam}")
        g1, g2 = st.columns(2)
        with g1:
            Ts = np.linspace(0, 4, 200)
            fig = px.line(x=Ts, y=[spectre_ec8(t, ag, S_, TB, TC, TD, qf) for t in Ts],
                          labels={"x": "T (s)", "y": "Sd (m/s²)"}, title="Spectre de calcul (type 1)")
            fig.update_traces(line=dict(color=NOIR, width=4))
            fig.add_vline(x=T1, line_dash="dash", line_color=ROUGE)
            pplot(fig, 350)
        with g2:
            fig = px.bar(x=Fi, y=zi, orientation="h", labels={"x": "Force Fi (kN)", "y": "z (m)"},
                         title="Répartition des forces sismiques", color_discrete_sequence=[JAUNE])
            fig.update_traces(marker_line_color=NOIR, marker_line_width=2)
            pplot(fig, 350)
        note("Méthode des forces latérales (EC8 §4.3.3.2) : applicable aux bâtiments réguliers. "
             "Une analyse modale, la torsion et les effets du second ordre restent à justifier.")


# ---------------------------------------------------------------------
MATERIAUX = {
    "Enduit ciment": 1.0, "Parpaing creux (équiv.)": 1.0, "Béton armé": 2.3, "Brique alvéolaire": 0.30,
    "Brique pleine": 0.80, "Béton cellulaire": 0.16, "Pierre": 1.7, "Plâtre / BA13": 0.25,
    "Polystyrène expansé": 0.038, "Laine de roche": 0.038, "Laine de verre": 0.035, "Polyuréthane": 0.025,
    "Bois massif": 0.13, "Carrelage + chape": 1.4,
}


def page_thermique():
    hero("🌡️ Enveloppe thermique et bilan énergétique", "Résistance thermique des parois • coefficient U • déperditions • consommation")
    t1, t2 = st.tabs(["🧱 Paroi composée (U)", "🔥 Bilan thermique du bâtiment"])
    with t1:
        if "couches" not in st.session_state:
            st.session_state.couches = pd.DataFrame({
                "Matériau": ["Enduit ciment", "Parpaing creux (équiv.)", "Polystyrène expansé", "Plâtre / BA13"],
                "Épaisseur (cm)": [2.0, 20.0, 10.0, 1.3]})
        ed = st.data_editor(st.session_state.couches, num_rows="dynamic", hide_index=True, key="ed_couches",
                            column_config={"Matériau": st.column_config.SelectboxColumn("Matériau (ext. → int.)",
                                                                                         options=list(MATERIAUX.keys()))})
        st.session_state.couches = ed
        e = ed.dropna()
        e = e[e["Matériau"].isin(MATERIAUX.keys())].copy()
        e["λ (W/m·K)"] = e["Matériau"].map(MATERIAUX)
        e["R (m²·K/W)"] = pd.to_numeric(e["Épaisseur (cm)"], errors="coerce").fillna(0) / 100 / e["λ (W/m·K)"]
        Rsi = st.number_input("R_si (m²·K/W)", 0.0, 0.3, 0.13, 0.01)
        Rse = st.number_input("R_se (m²·K/W)", 0.0, 0.2, 0.04, 0.01)
        Rt = Rsi + Rse + float(e["R (m²·K/W)"].sum())
        U = 1 / Rt if Rt > 0 else 0
        cobj = st.number_input("U cible (W/m²·K)", 0.1, 3.0, 0.45, 0.05)
        c1, c2, c3 = st.columns(3)
        c1.metric("R total", f"{Rt:.2f} m²·K/W")
        c2.metric("U de la paroi", f"{U:.3f} W/m²·K")
        c3.metric("Épaisseur totale", f"{pd.to_numeric(e['Épaisseur (cm)'], errors='coerce').sum():.1f} cm")
        verdict(U <= cobj, "U ≤ U cible.", "U > U cible : renforcer l'isolation.")
        if len(e):
            fig = px.bar(e, x="R (m²·K/W)", y="Matériau", orientation="h", title="Contribution de chaque couche à R",
                         color_discrete_sequence=[JAUNE])
            fig.update_traces(marker_line_color=NOIR, marker_line_width=2)
            fig.update_yaxes(autorange="reversed")
            pplot(fig, 320)
    with t2:
        P = st.session_state.projet
        c1, c2, c3 = st.columns(3)
        Ti = c1.number_input("T intérieure (°C)", 10.0, 30.0, 20.0, 0.5)
        Te = c1.number_input("T extérieure de base (°C)", -30.0, 45.0, -5.0, 1.0)
        nren = c2.number_input("Renouvellement d'air (vol/h)", 0.1, 3.0, 0.5, 0.1)
        hs = c2.number_input("Hauteur sous plafond (m)", 2.2, 5.0, 2.6, 0.1)
        pt = c3.slider("Majoration ponts thermiques (%)", 0, 30, 10)
        if "parois" not in st.session_state:
            st.session_state.parois = pd.DataFrame({
                "Paroi": ["Murs extérieurs", "Toiture-terrasse", "Plancher bas", "Vitrages", "Portes"],
                "Surface (m²)": [620.0, 260.0, 260.0, 130.0, 12.0],
                "U (W/m²·K)": [0.40, 0.25, 0.35, 1.6, 1.8]})
        pa = st.data_editor(st.session_state.parois, num_rows="dynamic", hide_index=True, key="ed_parois")
        st.session_state.parois = pa
        A = pd.to_numeric(pa["Surface (m²)"], errors="coerce").fillna(0)
        Uu = pd.to_numeric(pa["U (W/m²·K)"], errors="coerce").fillna(0)
        dT = Ti - Te
        Gt = float((A * Uu).sum()) * (1 + pt / 100)
        Vh = P["surface"] * hs
        Gv = 0.34 * nren * Vh
        Ptot = (Gt + Gv) * dT / 1000
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Transmission", f"{Gt:.0f} W/K")
        c2.metric("Ventilation", f"{Gv:.0f} W/K")
        c3.metric("Puissance (ΔT=%.0f K)" % dT, f"{Ptot:.1f} kW")
        c4.metric("Puissance spécifique", f"{Ptot * 1000 / P['surface']:.1f} W/m²")
        c1, c2, c3 = st.columns(3)
        dju = c1.number_input("Degrés-jours unifiés (DJU)", 0.0, 6000.0, 2400.0, 100.0)
        prix = c2.number_input("Prix énergie (par kWh)", 0.0, 2.0, 0.15, 0.01)
        kwh = 24 * (Gt + Gv) * dju / 1000
        c3.metric("Consommation annuelle", f"{kwh:,.0f} kWh".replace(",", " "), f"{kwh * prix:,.0f} {P['devise']}/an".replace(",", " "))
        d2 = pd.DataFrame({"Poste": list(pa["Paroi"].fillna("?")) + ["Ventilation"],
                           "W/K": list((A * Uu * (1 + pt / 100))) + [Gv]})
        fig = px.pie(d2, names="Poste", values="W/K", hole=0.5, title="Répartition des déperditions",
                     color_discrete_sequence=[NOIR, JAUNE, ROUGE, BLEU, VERT, ORANGE, GRIS])
        pplot(fig, 360)
        note("Pour un climat chaud, utiliser ΔT = T<sub>ext</sub> − T<sub>int</sub> et ajouter apports solaires et internes pour estimer la charge de climatisation.".replace("<sub>", "").replace("</sub>", ""))


# ---------------------------------------------------------------------
def page_metre():
    S = st.session_state
    P = S.projet
    dev = P["devise"]
    hero("🧮 Métré et estimation des coûts", "Bordereau quantitatif • calculateur de quantités structure • aléas, frais généraux, TVA")
    t1, t2, t3 = st.tabs(["📋 Bordereau", "🧊 Calculateur de quantités", "💶 Synthèse"])

    with t1:
        editor("metre", {
            "Unité": st.column_config.SelectboxColumn("Unité", options=["m³", "m²", "ml", "kg", "t", "u", "forfait", "j"]),
            "Quantité": st.column_config.NumberColumn("Quantité", min_value=0.0, format="%.2f"),
            "PU": st.column_config.NumberColumn(f"PU ({dev})", min_value=0.0, format="%.2f"),
            "Désignation": st.column_config.TextColumn("Désignation", width="large"),
        })
        mt = metre_totals(S.metre)
        st.metric("Total HT du bordereau", f"{fmt(mt['Total'].sum(), 0)} {dev}")

    with t2:
        st.markdown("##### Structure en béton armé — quantités automatiques")
        c1, c2, c3 = st.columns(3)
        with c1:
            N = int(st.number_input("Niveaux", 1, 60, int(P["niveaux"]), key="mq_N"))
            npot = int(st.number_input("Poteaux par niveau", 1, 500, 24))
            bp = st.number_input("Poteau b (cm)", 20.0, 100.0, 30.0, 5.0, key="mq_bp")
            hp = st.number_input("Poteau h (cm)", 20.0, 100.0, 30.0, 5.0, key="mq_hp")
            Hn = st.number_input("Hauteur d'étage (m)", 2.4, 6.0, 3.0, 0.1, key="mq_H")
        with c2:
            Lpo = st.number_input("Longueur totale de poutres / niveau (m)", 0.0, 3000.0, 220.0, 5.0)
            bpo = st.number_input("Poutre b (cm)", 15.0, 100.0, 25.0, 5.0)
            hpo = st.number_input("Poutre h (cm)", 25.0, 150.0, 45.0, 5.0)
            Sdal = st.number_input("Surface de dalle / niveau (m²)", 10.0, 10000.0, float(round(P["surface"] / max(N, 1), 0)), 10.0)
            edal = st.number_input("Épaisseur dalle (cm)", 10.0, 40.0, 20.0, 1.0, key="mq_e")
        with c3:
            nsem = int(st.number_input("Nombre de semelles", 0, 500, 24))
            Bs = st.number_input("Semelle côté (m)", 0.5, 6.0, 1.8, 0.1, key="mq_B")
            hs = st.number_input("Semelle hauteur (m)", 0.3, 2.0, 0.5, 0.05, key="mq_hs")
            Vv = st.number_input("Voiles / escaliers / divers (m³)", 0.0, 5000.0, 40.0, 5.0)
        r1, r2, r3 = st.columns(3)
        with r1:
            ra = {"Semelles": st.number_input("Ratio acier semelles (kg/m³)", 30.0, 200.0, 70.0, 5.0),
                  "Poteaux": st.number_input("Ratio acier poteaux (kg/m³)", 80.0, 300.0, 180.0, 5.0)}
        with r2:
            ra["Poutres"] = st.number_input("Ratio acier poutres (kg/m³)", 80.0, 250.0, 140.0, 5.0)
            ra["Dalles"] = st.number_input("Ratio acier dalles (kg/m³)", 60.0, 200.0, 100.0, 5.0)
        with r3:
            pu_b = st.number_input(f"Béton en place ({dev}/m³)", 0.0, 1e6, 320.0, 10.0)
            pu_a = st.number_input(f"Acier façonné posé ({dev}/kg)", 0.0, 1e4, 1.7, 0.1)
            pu_c = st.number_input(f"Coffrage ({dev}/m²)", 0.0, 1e5, 30.0, 1.0)
        Vsem = nsem * Bs * Bs * hs
        Vpot = npot * bp / 100 * hp / 100 * Hn * N
        Vpou = Lpo * bpo / 100 * hpo / 100 * N
        Vdal = Sdal * edal / 100 * N
        Vtot = Vsem + Vpot + Vpou + Vdal + Vv
        acier = Vsem * ra["Semelles"] + Vpot * ra["Poteaux"] + Vpou * ra["Poutres"] + Vdal * ra["Dalles"] + Vv * 90
        coff = (npot * 2 * (bp + hp) / 100 * Hn * N + Lpo * (bpo / 100 + 2 * (hpo - edal) / 100) * N + Sdal * N
                + nsem * 4 * Bs * hs + Vv / 0.2 * 2)
        calc = pd.DataFrame([
            {"Poste": "Béton semelles", "Quantité": round(Vsem, 1), "Unité": "m³"},
            {"Poste": "Béton poteaux", "Quantité": round(Vpot, 1), "Unité": "m³"},
            {"Poste": "Béton poutres", "Quantité": round(Vpou, 1), "Unité": "m³"},
            {"Poste": "Béton dalles", "Quantité": round(Vdal, 1), "Unité": "m³"},
            {"Poste": "Béton voiles / divers", "Quantité": round(Vv, 1), "Unité": "m³"},
            {"Poste": "TOTAL béton", "Quantité": round(Vtot, 1), "Unité": "m³"},
            {"Poste": "Acier HA", "Quantité": round(acier, 0), "Unité": "kg"},
            {"Poste": "Coffrage", "Quantité": round(coff, 0), "Unité": "m²"},
        ])
        c1, c2 = st.columns([1, 1])
        with c1:
            show_df(calc)
        with c2:
            c1_, c2_, c3_ = st.columns(3)
            c1_.metric("Ratio acier", f"{acier / Vtot:.0f} kg/m³")
            c2_.metric("Béton / m² plancher", f"{Vtot / (Sdal * N):.3f} m³/m²")
            c3_.metric("Coût structure", f"{fmt(Vtot * pu_b + acier * pu_a + coff * pu_c, 0)} {dev}")
            if st.button("➕ Envoyer ces quantités au bordereau"):
                new = pd.DataFrame([
                    ("03 Structure BA", "Béton armé — structure (calculateur)", "m³", round(Vtot, 1), pu_b),
                    ("03 Structure BA", "Acier HA — structure (calculateur)", "kg", round(acier, 0), pu_a),
                    ("03 Structure BA", "Coffrage — structure (calculateur)", "m²", round(coff, 0), pu_c),
                ], columns=COLS["metre"])
                S.metre = pd.concat([S.metre, new], ignore_index=True)
                st.rerun()

    with t3:
        mt = metre_totals(S.metre)
        c1, c2, c3, c4 = st.columns(4)
        ale = c1.slider("Aléas (%)", 0, 20, 5)
        fg = c2.slider("Frais généraux et bénéfice (%)", 0, 30, 12)
        tva = c3.slider("TVA (%)", 0.0, 25.0, 20.0, 0.5)
        ht = float(mt["Total"].sum())
        ht_a = ht * (1 + ale / 100) * (1 + fg / 100)
        ttc = ht_a * (1 + tva / 100)
        c4.metric("Total TTC", f"{fmt(ttc, 0)} {dev}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total HT brut", f"{fmt(ht, 0)}")
        c2.metric("+ Aléas", f"{fmt(ht * ale / 100, 0)}")
        c3.metric("+ Frais généraux", f"{fmt(ht * (1 + ale / 100) * fg / 100, 0)}")
        c4.metric("€/m² TTC", f"{fmt(ttc / P['surface'], 0)}")
        lots = mt.groupby("Lot", as_index=False)["Total"].sum().sort_values("Total")
        fig = px.bar(lots, x="Total", y="Lot", orientation="h", title="Coût par lot", color_discrete_sequence=[JAUNE])
        fig.update_traces(marker_line_color=NOIR, marker_line_width=2)
        pplot(fig, 420)


# ---------------------------------------------------------------------
def page_planning():
    S = st.session_state
    P = S.projet
    hero("📅 Planning et chemin critique", "Diagramme de Gantt • calage automatique • marges • avancement réel")
    note("Les prédécesseurs se saisissent par nom de tâche, séparés par « ; » (ex. <b>Terrassement;Installation de chantier</b>).")
    editor("taches", {
        "Début": st.column_config.DateColumn("Début", format="DD/MM/YYYY"),
        "Durée (j)": st.column_config.NumberColumn("Durée (j)", min_value=0, step=1),
        "Avancement (%)": st.column_config.NumberColumn("Avancement (%)", min_value=0, max_value=100, step=5),
        "Prédécesseurs": st.column_config.TextColumn("Prédécesseurs", width="large"),
    })
    mode = st.radio("Calendrier", ["Dates saisies", "Calage automatique selon prédécesseurs"], horizontal=True)
    try:
        d, T = cpm(S.taches)
    except ValueError as ex:
        st.error(str(ex))
        return
    d["Avancement (%)"] = pd.to_numeric(d["Avancement (%)"], errors="coerce").fillna(0).clip(0, 100)
    if mode.startswith("Calage"):
        d["Début_"] = [pd.Timestamp(P["debut"]) + pd.Timedelta(days=float(v)) for v in d["ES"]]
    else:
        d["Début_"] = pd.to_datetime(d["Début"], errors="coerce").fillna(pd.Timestamp(P["debut"]))
    d["Fin_"] = d["Début_"] + pd.to_timedelta(d["Durée (j)"], unit="D")
    today = pd.Timestamp(date.today())

    def statut(r):
        if r["Avancement (%)"] >= 100:
            return "Terminé"
        if r["Fin_"] < today:
            return "En retard"
        if r["Début_"] <= today:
            return "En cours"
        return "À venir"

    d["Statut"] = d.apply(statut, axis=1)
    if mode.startswith("Calage") and st.button("💾 Appliquer ces dates au tableau"):
        tt = S.taches.copy()
        mp = dict(zip(d["Tâche"], d["Début_"].dt.date))
        tt["Début"] = [mp.get(n, x) for n, x in zip(tt["Tâche"], tt["Début"])]
        S.taches = tt
        st.rerun()
    fig = px.timeline(d, x_start="Début_", x_end="Fin_", y="Tâche", color="Statut",
                      color_discrete_map={"Terminé": VERT, "En cours": JAUNE, "En retard": ROUGE, "À venir": "#C9C5AA"},
                      hover_data=["Responsable", "Avancement (%)"], title="Diagramme de Gantt")
    fig.update_yaxes(autorange="reversed")
    prog = go.Bar(orientation="h", y=d["Tâche"], base=d["Début_"],
                  x=((d["Fin_"] - d["Début_"]).dt.total_seconds() * 1000 * d["Avancement (%)"] / 100),
                  marker_color=NOIR, width=0.22, name="Avancement réel", hoverinfo="skip")
    fig.add_trace(prog)
    fig.update_layout(barmode="overlay")
    fig.add_shape(type="line", x0=today, x1=today, y0=0, y1=1, yref="paper", line=dict(color=ROUGE, width=2, dash="dash"))
    fig.add_annotation(x=today, y=1.04, yref="paper", text="Aujourd'hui", showarrow=False, font=dict(color=ROUGE))
    pplot(fig, 120 + 34 * len(d))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Durée (chemin critique)", f"{T:.0f} j")
    c2.metric("Fin prévue", (pd.Timestamp(P["debut"]) + pd.Timedelta(days=T)).strftime("%d/%m/%Y"))
    c3.metric("Tâches en retard", int((d["Statut"] == "En retard").sum()))
    c4.metric("Tâches critiques", int(d["Critique"].sum()))
    out = d[["Tâche", "Responsable", "Durée (j)", "Avancement (%)", "Marge (j)", "Critique", "Statut"]].copy()
    out["Critique"] = out["Critique"].map({True: "🔴 Oui", False: "—"})
    show_df(out)


# ---------------------------------------------------------------------
def page_cout():
    S = st.session_state
    P = S.projet
    dev = P["devise"]
    hero("💰 Suivi des coûts — valeur acquise (EVM)", "PV, EV, AC • CPI, SPI • prévision à l'achèvement")
    bac = st.number_input(f"Budget à l'achèvement BAC ({dev})", 0.0, 1e10, float(P["budget"]), 10000.0)
    note("Saisir les valeurs <b>cumulées</b> par mois : valeur planifiée (PV), valeur acquise (EV) et coût réel (AC).")
    editor("ev", {"Mois": st.column_config.NumberColumn("Mois", min_value=1, step=1)})
    ev = S.ev.copy()
    for c in COLS["ev"]:
        ev[c] = pd.to_numeric(ev[c], errors="coerce")
    ev = ev.dropna(subset=["Mois"]).sort_values("Mois")
    last = ev.dropna(subset=["EV cumulée", "AC cumulé", "PV cumulé"])
    if last.empty:
        st.info("Renseigner au moins un mois complet.")
        return
    r = last.iloc[-1]
    PV, EV, AC = float(r["PV cumulé"]), float(r["EV cumulée"]), float(r["AC cumulé"])
    CPI = EV / AC if AC else float("nan")
    SPI = EV / PV if PV else float("nan")
    EAC = bac / CPI if CPI else float("nan")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CPI (coût)", f"{CPI:.2f}", "sous budget" if CPI >= 1 else "dépassement", delta_color="normal" if CPI >= 1 else "inverse")
    c2.metric("SPI (délai)", f"{SPI:.2f}", "en avance" if SPI >= 1 else "en retard", delta_color="normal" if SPI >= 1 else "inverse")
    c3.metric("CV = EV − AC", f"{fmt(EV - AC, 0)} {dev}")
    c4.metric("SV = EV − PV", f"{fmt(EV - PV, 0)} {dev}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("EAC (prévision finale)", f"{fmt(EAC, 0)} {dev}")
    c2.metric("ETC (reste à dépenser)", f"{fmt(EAC - AC, 0)} {dev}")
    c3.metric("VAC (écart final)", f"{fmt(bac - EAC, 0)} {dev}")
    c4.metric("Avancement financier", f"{EV / bac * 100:.1f} %")
    fig = go.Figure()
    for col, color in [("PV cumulé", GRIS), ("EV cumulée", JAUNE), ("AC cumulé", ROUGE)]:
        fig.add_trace(go.Scatter(x=ev["Mois"], y=ev[col], name=col, mode="lines+markers", line=dict(color=color, width=4),
                                 marker=dict(size=9, line=dict(color=NOIR, width=1))))
    fig.add_hline(y=bac, line_dash="dot", line_color=NOIR, annotation_text="BAC")
    fig.update_layout(title="Courbes en S", xaxis_title="Mois", yaxis_title=dev)
    pplot(fig, 420)


# ---------------------------------------------------------------------
def page_hse():
    S = st.session_state
    hero("🦺 Santé, sécurité et gestion des risques", "Matrice de criticité • plan de maîtrise • taux de fréquence et de gravité")
    t1, t2 = st.tabs(["⚠️ Matrice des risques", "📈 Indicateurs d'accidentologie"])
    with t1:
        editor("risques", {
            "Probabilité": st.column_config.NumberColumn("Probabilité (1-5)", min_value=1, max_value=5, step=1),
            "Gravité": st.column_config.NumberColumn("Gravité (1-5)", min_value=1, max_value=5, step=1),
            "Risque": st.column_config.TextColumn("Risque", width="large"),
            "Mesure de maîtrise": st.column_config.TextColumn("Mesure de maîtrise", width="large"),
        })
        r = S.risques.dropna(subset=["Risque"]).copy()
        r["Probabilité"] = pd.to_numeric(r["Probabilité"], errors="coerce").fillna(1).clip(1, 5).astype(int)
        r["Gravité"] = pd.to_numeric(r["Gravité"], errors="coerce").fillna(1).clip(1, 5).astype(int)
        r["Score"] = r["Probabilité"] * r["Gravité"]
        r["Niveau"] = pd.cut(r["Score"], [0, 4, 9, 14, 25], labels=["🟢 Faible", "🟡 Modéré", "🟠 Élevé", "🔴 Critique"])
        counts = np.zeros((5, 5), dtype=int)
        for _, x in r.iterrows():
            counts[x["Probabilité"] - 1, x["Gravité"] - 1] += 1
        sc = np.array([[(p + 1) * (g + 1) for g in range(5)] for p in range(5)])
        c1, c2 = st.columns([1, 1])
        with c1:
            fig = go.Figure(go.Heatmap(z=sc, x=[1, 2, 3, 4, 5], y=[1, 2, 3, 4, 5], text=counts, texttemplate="%{text}",
                                       colorscale=[[0, VERT], [0.25, JAUNE], [0.55, ORANGE], [1, ROUGE]], showscale=False,
                                       textfont=dict(size=22, color=NOIR)))
            fig.update_layout(title="Matrice de criticité (nombre de risques)", xaxis_title="Gravité", yaxis_title="Probabilité")
            pplot(fig, 420)
        with c2:
            show_df(r[["Risque", "Phase", "Score", "Niveau", "Mesure de maîtrise"]].sort_values("Score", ascending=False))
    with t2:
        c1, c2, c3 = st.columns(3)
        hrs = c1.number_input("Heures travaillées (cumul)", 1000.0, 1e8, 85000.0, 1000.0)
        acc = c2.number_input("Accidents avec arrêt", 0, 500, 1)
        jp = c3.number_input("Jours d'arrêt perdus", 0, 100000, 24)
        tf = acc * 1e6 / hrs
        tg = jp * 1e3 / hrs
        c1, c2, c3 = st.columns(3)
        c1.metric("Taux de fréquence TF", f"{tf:.1f}")
        c2.metric("Taux de gravité TG", f"{tg:.2f}")
        c3.metric("Heures sans accident (indic.)", f"{hrs / max(acc, 1):,.0f}".replace(",", " "))
        note("TF = accidents avec arrêt × 10⁶ / heures travaillées • TG = jours perdus × 10³ / heures travaillées.")
        eq = pd.DataFrame({"Contrôle": ["Casque / chaussures / gilet", "Garde-corps et protections de rive",
                                        "Échafaudages réceptionnés", "Étaiement vérifié avant bétonnage",
                                        "Installation électrique provisoire", "Extincteurs / secours"],
                           "Conforme": [True, True, False, True, True, True]})
        st.data_editor(eq, hide_index=True, key="ed_hse_check")


# ---------------------------------------------------------------------
def page_formulation():
    hero("🧪 Formulation de béton", "Méthode de Bolomey / Dreux-Gorisse simplifiée • dosages par m³ • quantités pour un volume donné")
    c1, c2, c3 = st.columns(3)
    with c1:
        classe = st.selectbox("Classe de résistance", CLASSES_BETON, index=1, key="f_cl")
        exp = st.selectbox("Classe d'exposition", ["X0", "XC1", "XC2", "XC3", "XC4", "XD1", "XD2", "XS1", "XS3"], index=3)
        cim = st.selectbox("Classe vraie du ciment σ'c (MPa)", [32.5, 42.5, 52.5], index=1)
    with c2:
        dmax = st.selectbox("Dmax des granulats (mm)", [10, 16, 20, 25, 31.5, 40], index=2)
        qual = st.selectbox("Qualité des granulats", ["Excellente", "Bonne (courante)", "Passable"], index=1)
        slump = st.selectbox("Consistance", ["S1 (10–40 mm)", "S2 (50–90 mm)", "S3 (100–150 mm)", "S4 (160–210 mm)"], index=2)
    with c3:
        adj = st.slider("Réduction d'eau par adjuvant (%)", 0, 25, 0)
        ps = st.slider("Part de sable dans les granulats (%)", 30, 55, 42)
        Vb = st.number_input("Volume à produire (m³)", 0.5, 5000.0, 10.0, 0.5)
    fck = parse_classe(classe)[0]
    idx = 0 if dmax <= 16 else (1 if dmax <= 25 else 2)
    G = {"Excellente": (0.55, 0.60, 0.65), "Bonne (courante)": (0.45, 0.50, 0.55), "Passable": (0.35, 0.40, 0.45)}[qual][idx]
    fcm = fck + 8
    ce = fcm / (G * cim) + 0.5
    E0 = {"S1": 160, "S2": 175, "S3": 190, "S4": 205}[slump[:2]] + {10: 20, 16: 10, 20: 0, 25: -5, 31.5: -10, 40: -15}[dmax]
    E = E0 * (1 - adj / 100)
    C = E * ce
    cmin = {"X0": 150, "XC1": 260, "XC2": 280, "XC3": 280, "XC4": 300, "XD1": 300, "XD2": 320, "XS1": 330, "XS3": 350}[exp]
    ec_max = {"X0": 1.0, "XC1": 0.65, "XC2": 0.60, "XC3": 0.55, "XC4": 0.50, "XD1": 0.55, "XD2": 0.50, "XS1": 0.45, "XS3": 0.45}[exp]
    C = max(C, cmin)
    EC = E / C
    if EC > ec_max:
        E = C * ec_max
        EC = ec_max
    Vc = C / 3.1
    Vair = 20.0
    Vg = 1000 - Vc - E - Vair
    sable = Vg * ps / 100 * 2.65
    grav = Vg * (1 - ps / 100) * 2.65
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Résistance visée fcm", f"{fcm:.0f} MPa")
    c2.metric("Rapport C/E (Bolomey)", f"{ce:.2f}")
    c3.metric("Rapport E/C retenu", f"{EC:.2f}", f"max {ec_max:.2f}")
    c4.metric("Ciment", f"{C:.0f} kg/m³")
    df = pd.DataFrame({
        "Constituant": ["Ciment", "Eau efficace", "Sable 0/4", "Gravillons", "Air occlus (L)"],
        "Par m³": [round(C), round(E), round(sable), round(grav), Vair],
        "Unité": ["kg", "L", "kg", "kg", "L"],
        f"Pour {Vb:g} m³ (+5 % pertes)": [round(C * Vb * 1.05), round(E * Vb * 1.05), round(sable * Vb * 1.05),
                                          round(grav * Vb * 1.05), "—"],
    })
    show_df(df)
    fig = px.pie(values=[C, E, sable, grav], names=["Ciment", "Eau", "Sable", "Gravillons"], hole=0.5,
                 title="Composition massique du béton", color_discrete_sequence=[NOIR, BLEU, JAUNE, GRIS])
    pplot(fig, 340)
    st.info(f"≈ {math.ceil(C * Vb * 1.05 / 50)} sacs de ciment de 50 kg pour {Vb:g} m³ (pertes incluses).")
    note("Formulation indicative : à valider par des essais de convenance / d'étude (NF EN 206/CN, EN 12350). "
         "Les valeurs de C<sub>min</sub> et E/C<sub>max</sub> dépendent de l'annexe nationale applicable.".replace("<sub>", "").replace("</sub>", ""))


# ---------------------------------------------------------------------
def page_aciers():
    S = st.session_state
    hero("🪛 Nomenclature des aciers et ancrages", "Poids par diamètre • ratios • longueurs d'ancrage et de recouvrement (EC2)")
    t1, t2 = st.tabs(["📑 Nomenclature", "📏 Ancrage et recouvrement"])
    with t1:
        editor("acier", {
            "Diamètre (mm)": st.column_config.SelectboxColumn("Diamètre (mm)", options=[6, 8, 10, 12, 14, 16, 20, 25, 32, 40]),
            "Longueur (m)": st.column_config.NumberColumn("Longueur (m)", min_value=0.0, format="%.2f"),
        })
        a = S.acier.copy()
        for c in NUMS["acier"]:
            a[c] = pd.to_numeric(a[c], errors="coerce").fillna(0)
        a["Poids (kg)"] = a["Nb éléments"] * a["Nb barres / élément"] * a["Longueur (m)"] * a["Diamètre (mm)"] ** 2 * 0.00617
        pert = st.slider("Chutes et pertes (%)", 0, 15, 5)
        tot = a["Poids (kg)"].sum() * (1 + pert / 100)
        vb = st.number_input("Volume de béton associé (m³) pour le ratio", 0.0, 100000.0, 60.0, 5.0)
        c1, c2, c3 = st.columns(3)
        c1.metric("Poids net", f"{a['Poids (kg)'].sum():,.0f} kg".replace(",", " "))
        c2.metric("Poids avec pertes", f"{tot:,.0f} kg".replace(",", " "))
        c3.metric("Ratio", f"{tot / vb:.0f} kg/m³" if vb else "—")
        byd = a.groupby("Diamètre (mm)", as_index=False)["Poids (kg)"].sum()
        byd = byd[byd["Poids (kg)"] > 0]
        byd["Diamètre (mm)"] = "HA" + byd["Diamètre (mm)"].astype(int).astype(str)
        if len(byd):
            fig = px.bar(byd, x="Diamètre (mm)", y="Poids (kg)", title="Poids d'acier par diamètre", color_discrete_sequence=[JAUNE])
            fig.update_traces(marker_line_color=NOIR, marker_line_width=2)
            pplot(fig, 330)
    with t2:
        c1, c2, c3 = st.columns(3)
        phi = c1.selectbox("Diamètre φ (mm)", [8, 10, 12, 14, 16, 20, 25, 32], index=3)
        classe = c1.selectbox("Classe de béton", CLASSES_BETON, index=1, key="anc_cl")
        fyk = c2.selectbox("fyk (MPa)", [400, 500], index=1, key="anc_fy")
        bonne = c2.radio("Conditions d'adhérence", ["Bonnes (η1=1,0)", "Médiocres (η1=0,7)"])
        crochet = c3.radio("Forme", ["Barre droite (α1=1,0)", "Crochet / coude (α1=0,7)"])
        eta1 = 1.0 if bonne.startswith("Bonnes") else 0.7
        a1 = 1.0 if crochet.startswith("Barre") else 0.7
        a6 = c3.slider("α6 (% de barres recouvertes)", 1.0, 1.5, 1.5, 0.1)
        pr = beton_props(classe)
        fctd = 0.7 * pr["fctm"] / 1.5
        fbd = 2.25 * eta1 * fctd
        sig = fyk / 1.15
        lb = phi / 4 * sig / fbd
        lbd = max(a1 * lb, 0.3 * lb, 10 * phi, 100)
        l0 = max(a6 * lbd, 0.3 * a6 * lb, 15 * phi, 200)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("f_bd", f"{fbd:.2f} MPa")
        c2.metric("l_b,rqd", f"{lb:.0f} mm ({lb / phi:.0f}φ)")
        c3.metric("Ancrage l_bd", f"{lbd:.0f} mm")
        c4.metric("Recouvrement l_0", f"{l0:.0f} mm")


# ---------------------------------------------------------------------
def page_eau():
    P = st.session_state.projet
    hero("💧 Eaux pluviales, assainissement et alimentation en eau", "Méthode rationnelle • formule de Manning • réserve d'eau")
    t1, t2 = st.tabs(["🌧️ Eaux pluviales et collecteurs", "🚰 Alimentation en eau"])
    with t1:
        c1, c2, c3 = st.columns(3)
        A = c1.number_input("Surface collectée (m²)", 10.0, 100000.0, 260.0, 10.0)
        Cr = c1.number_input("Coefficient de ruissellement C", 0.1, 1.0, 0.95, 0.05)
        i = c2.number_input("Intensité de pluie de projet (mm/h)", 20.0, 400.0, 140.0, 5.0)
        pente = c2.number_input("Pente du collecteur (%)", 0.2, 10.0, 1.0, 0.1)
        n = c3.selectbox("Matériau (Manning n)", [0.010, 0.011, 0.013, 0.015], index=1,
                         format_func=lambda v: {0.010: "PEHD lisse (0,010)", 0.011: "PVC (0,011)", 0.013: "Béton (0,013)",
                                                0.015: "Béton ancien (0,015)"}[v])
        Q = Cr * i * A / 3600
        rows = []
        for D in [100, 125, 160, 200, 250, 315, 400, 500, 630]:
            Dm = D / 1000
            Af = math.pi * Dm ** 2 / 4
            R = Dm / 4
            V = 1 / n * R ** (2 / 3) * math.sqrt(pente / 100)
            Qf = V * Af * 1000
            rows.append({"DN (mm)": D, "Q pleine section (L/s)": round(Qf, 1), "V (m/s)": round(V, 2),
                         "Taux Q/Qf": round(Q / Qf, 2), "Adapté (Q/Qf ≤ 0,7)": "✅" if Q / Qf <= 0.7 else "❌"})
        df = pd.DataFrame(rows)
        ok = df[df["Adapté (Q/Qf ≤ 0,7)"] == "✅"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Débit de pointe Q", f"{Q:.1f} L/s")
        c2.metric("DN minimal conseillé", f"DN {int(ok.iloc[0]['DN (mm)'])}" if len(ok) else "> DN 630")
        c3.metric("Vitesse d'autocurage", "≥ 0,6 m/s")
        show_df(df)
    with t2:
        c1, c2, c3 = st.columns(3)
        occ = c1.number_input("Nombre d'occupants", 1, 20000, int(P["surface"] / 30))
        ratio = c2.number_input("Consommation (L/pers/j)", 30.0, 400.0, 150.0, 10.0)
        jours = c3.number_input("Autonomie de réserve (jours)", 0.5, 5.0, 1.5, 0.5)
        cp = st.slider("Coefficient de pointe journalier", 1.2, 3.0, 1.8, 0.1)
        Vj = occ * ratio / 1000
        c1, c2, c3 = st.columns(3)
        c1.metric("Consommation moyenne", f"{Vj:.1f} m³/j")
        c2.metric("Volume de la réserve", f"{Vj * jours:.1f} m³")
        c3.metric("Débit moyen de pointe", f"{Vj * cp / 24 * 1000 / 3.6:.2f} L/s")


# ---------------------------------------------------------------------
def build_excel():
    S = st.session_state
    buf = io.BytesIO()
    P = {k: str(v) for k, v in S.projet.items()}
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame({"Clé": list(P.keys()), "Valeur": list(P.values())}).to_excel(xw, sheet_name="Projet", index=False)
        for k in COLS:
            S[k].to_excel(xw, sheet_name=LABELS[k][:31], index=False)
        metre_totals(S.metre).to_excel(xw, sheet_name="Metre avec totaux", index=False)
    return buf.getvalue()


def build_rapport():
    S = st.session_state
    P = S.projet
    dev = P["devise"]
    t = S.taches.dropna(subset=["Tâche"])
    dur = num(t, "Durée (j)")
    avanc = float((dur * num(t, "Avancement (%)")).sum() / dur.sum()) if dur.sum() else 0
    mt = metre_totals(S.metre)
    ess = eval_beton(S.essais)
    r = S.risques.copy()
    r["Score"] = num(r, "Probabilité") * num(r, "Gravité")
    lignes = [
        f"# Rapport de synthèse — {P['nom']}",
        f"*Édité le {date.today().strftime('%d/%m/%Y')}*", "",
        "## Projet",
        f"- Maître d'ouvrage : {P['moa']}", f"- Usage : {P['usage']}",
        f"- Niveaux : {P['niveaux']} • Surface : {P['surface']:.0f} m²",
        f"- Période : {P['debut']} → {P['fin']}", "",
        "## Avancement et délais", f"- Avancement global pondéré : **{avanc:.1f} %**", "",
        "## Coûts",
        f"- Estimation du métré HT : **{mt['Total'].sum():,.0f} {dev}**".replace(",", " "),
        f"- Budget cible : {P['budget']:,.0f} {dev}".replace(",", " "), "",
        "## Qualité des bétons",
    ]
    if len(ess):
        for _, x in ess.iterrows():
            lignes.append(f"- {x['Classe']} : n={x['n']}, fcm={x['fcm (MPa)']} MPa, fmin={x['f min (MPa)']} MPa → {x['Statut']}")
    else:
        lignes.append("- Aucun essai à 28 jours.")
    lignes += ["", "## Risques HSE critiques (score ≥ 15)"]
    crit = r[r["Score"] >= 15]
    lignes += [f"- {x['Risque']} (score {int(x['Score'])})" for _, x in crit.iterrows()] or ["- Aucun."]
    lignes += ["", "---", "*Rapport généré par GC Bâtiment Pro — résultats indicatifs à valider par un ingénieur.*"]
    return "\n".join(lignes)


def page_export():
    S = st.session_state
    hero("📤 Export, rapport et sauvegarde", "Classeur Excel complet • rapport de synthèse • restauration d'une sauvegarde")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Classeur Excel (toutes les données)")
        st.download_button("⬇️ Télécharger le classeur Excel", build_excel(), "projet_genie_civil.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with c2:
        st.markdown("#### Rapport de synthèse (Markdown)")
        rap = build_rapport()
        st.download_button("⬇️ Télécharger le rapport", rap.encode("utf-8"), "rapport_synthese.md", "text/markdown")
    with st.expander("👁️ Aperçu du rapport", expanded=True):
        st.markdown(rap)
    st.markdown("#### Jeux de données au format CSV")
    cols = st.columns(4)
    for i, k in enumerate(COLS):
        cols[i % 4].download_button(f"⬇️ {LABELS[k]}", S[k].to_csv(index=False).encode("utf-8-sig"), f"{k}.csv", "text/csv", key=f"csv_{k}")
    st.markdown("#### Restaurer une sauvegarde Excel")
    up = st.file_uploader("Classeur exporté précédemment", type=["xlsx"])
    if up is not None and st.button("♻️ Restaurer les données"):
        try:
            sheets = pd.read_excel(up, sheet_name=None)
            inv = {v[:31]: k for k, v in LABELS.items()}
            for nom, df in sheets.items():
                if nom in inv:
                    S[inv[nom]] = coerce(df, inv[nom])
            if "Projet" in sheets:
                dp = dict(zip(sheets["Projet"]["Clé"], sheets["Projet"]["Valeur"]))
                for k in ["nom", "moa", "lieu", "usage", "devise"]:
                    if k in dp and str(dp[k]) != "nan":
                        S.projet[k] = str(dp[k])
                for k in ["niveaux"]:
                    S.projet[k] = int(float(dp.get(k, S.projet[k])))
                for k in ["surface", "budget"]:
                    S.projet[k] = float(dp.get(k, S.projet[k]))
                for k in ["debut", "fin"]:
                    S.projet[k] = pd.to_datetime(dp.get(k)).date()
            st.success("Données restaurées.")
            st.rerun()
        except Exception as ex:
            st.error(f"Restauration impossible : {ex}")
    st.markdown("#### Réinitialisation")
    if st.button("🗑️ Recharger les données de démonstration"):
        for k in list(S.keys()):
            del S[k]
        st.rerun()


# =====================================================================
# 5. NAVIGATION
# =====================================================================
PAGES = {
    "🏠 Tableau de bord": page_dashboard,
    "📥 Collecte et journal": page_collecte,
    "🧱 Essais béton": page_essais,
    "⚖️ Descente de charges": page_descente,
    "📐 Poutre BA": page_poutre,
    "🏛️ Poteau et dalle": page_poteau_dalle,
    "🦶 Fondations et sol": page_fondations,
    "🌬️ Vent, neige, séisme": page_actions,
    "🌡️ Thermique": page_thermique,
    "🧮 Métré et coûts": page_metre,
    "📅 Planning": page_planning,
    "💰 Suivi des coûts (EVM)": page_cout,
    "🦺 HSE et risques": page_hse,
    "🧪 Formulation béton": page_formulation,
    "🪛 Aciers et ancrages": page_aciers,
    "💧 Eaux et réseaux": page_eau,
    "📤 Export et rapport": page_export,
}


def main():
    init_state()
    with st.sidebar:
        st.markdown("<div class='brand'>🏗️ GC Bâtiment Pro</div>", unsafe_allow_html=True)
        choix = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")
        st.markdown("---")
        st.caption(f"Projet : {st.session_state.projet['nom']}")
        st.caption("Résultats indicatifs — validation par un ingénieur / BET requise.")
    PAGES[choix]()


main()
