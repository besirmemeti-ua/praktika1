# app.py
import hmac
import os
from collections import Counter
from datetime import date, datetime

import streamlit as st

# ---------------- KONFIGURIMI ----------------
ORA_FILLIMI = 9 * 60
ORA_FUNDI = 17 * 60
KOHEZGJATJA = 30
FORMATI_DATES = "%d.%m.%Y"
SKEDARI_TERMINEVE = "terminet.txt"

# Në Streamlit Cloud vendosini te Settings > Secrets:
# STAFI_USERNAME = "admin test"
# STAFI_PASSWORD = "admin"
try:
    STAFI_USERNAME = st.secrets.get("STAFI_USERNAME", "admin test")
    STAFI_PASSWORD = st.secrets.get("STAFI_PASSWORD", "admin")
except Exception:
    STAFI_USERNAME, STAFI_PASSWORD = "admin test", "admin"

MUAJT = {
    1: "Janar", 2: "Shkurt", 3: "Mars", 4: "Prill",
    5: "Maj", 6: "Qershor", 7: "Korrik", 8: "Gusht",
    9: "Shtator", 10: "Tetor", 11: "Nëntor", 12: "Dhjetor",
}

TRAJTIMET = {
    "Kontrollë": 10,
    "Radiografi": 15,
    "Nxjerrje dhëmbi": 25,
    "Mbushje": 35,
    "Trajtim i kanalit": 80,
    "Pastrim i gurëzave": 30,
    "Zbardhim": 150,
    "Kurorë": 200,
}

FAQET = {
    "termin": ("Cakto termin", ":material/calendar_add_on:"),
    "stafi": ("Logoju", ":material/lock:"),
}

STILI = """
<style>
.kreu {
    display: flex; align-items: center; gap: 14px;
    margin-bottom: 18px;
}
.kreu .logo {
    width: 52px; height: 52px; border-radius: 50%;
    background: #0F6E56; color: #FFFFFF;
    display: flex; align-items: center; justify-content: center;
    font-size: 26px;
}
.kreu .emri { margin: 0; font-size: 26px; font-weight: 600; color: #085041; }
.kreu .orari { margin: 0; font-size: 14px; color: #0F6E56; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF;
    border-radius: 14px;
}
.block-container { padding-bottom: 120px; }
</style>
"""


# ---------------- BACKEND ----------------
def formato_daten(data):
    return data.strftime(FORMATI_DATES)


def data_me_fjale(data):
    return f"{data.day} {MUAJT[data.month]} {data.year}"


def gjenero_terminet():
    terminet = []
    minuta = ORA_FILLIMI
    while minuta < ORA_FUNDI:
        terminet.append(f"{minuta // 60:02d}:{minuta % 60:02d}")
        minuta += KOHEZGJATJA
    return terminet


TERMINET_E_DITES = gjenero_terminet()


def lexo_terminet(data_zgjedhur):
    """Kthen dict: ora -> (pacienti, trajtimi) për datën e zgjedhur."""
    te_rezervuara = {}
    if not os.path.exists(SKEDARI_TERMINEVE):
        return te_rezervuara

    with open(SKEDARI_TERMINEVE, "r", encoding="utf-8") as f:
        for rreshti in f:
            rreshti = rreshti.strip()
            if not rreshti:
                continue
            pjeset = [p.strip() for p in rreshti.split(",")]
            if len(pjeset) != 4:
                continue
            data_tekst, ora, pacienti, trajtimi = pjeset
            try:
                data_rreshtit = datetime.strptime(data_tekst, FORMATI_DATES).date()
            except ValueError:
                continue
            if data_rreshtit != data_zgjedhur:
                continue
            if ora not in TERMINET_E_DITES or ora in te_rezervuara:
                continue
            te_rezervuara[ora] = (pacienti, trajtimi)
    return te_rezervuara


def ruaj_termin(data_zgjedhur, ora, pacienti, trajtimi):
    duhet_rresht_i_ri = False
    if os.path.exists(SKEDARI_TERMINEVE) and os.path.getsize(SKEDARI_TERMINEVE) > 0:
        with open(SKEDARI_TERMINEVE, "rb") as f:
            f.seek(-1, os.SEEK_END)
            if f.read(1) not in (b"\n", b"\r"):
                duhet_rresht_i_ri = True

    with open(SKEDARI_TERMINEVE, "a", encoding="utf-8") as f:
        if duhet_rresht_i_ri:
            f.write("\n")
        f.write(f"{formato_daten(data_zgjedhur)},{ora},{pacienti},{trajtimi}\n")


def terminet_e_lira(te_rezervuara):
    return [t for t in TERMINET_E_DITES if t not in te_rezervuara]


def statistikat(te_rezervuara):
    numri = len(te_rezervuara)
    te_hyrat = sum(TRAJTIMET.get(t, 0) for _, t in te_rezervuara.values())
    zenia = numri / len(TERMINET_E_DITES) * 100
    if te_rezervuara:
        me_i_shpeshti = Counter(t for _, t in te_rezervuara.values()).most_common(1)[0][0]
    else:
        me_i_shpeshti = "asnjë"
    return numri, te_hyrat, zenia, me_i_shpeshti


def ndertro_raportin(te_rezervuara, data_zgjedhur):
    numri, te_hyrat, zenia, me_i_shpeshti = statistikat(te_rezervuara)
    te_lira = terminet_e_lira(te_rezervuara)

    rreshta = [
        "Raporti i ditës - Family Dental Care",
        "",
        f"Data: {formato_daten(data_zgjedhur)}",
        f"Dita: {data_me_fjale(data_zgjedhur)}",
        f"Muaji: {MUAJT[data_zgjedhur.month]}",
        f"Viti: {data_zgjedhur.year}",
        "",
        "Terminet e rezervuara:",
    ]
    if te_rezervuara:
        for ora in TERMINET_E_DITES:
            if ora in te_rezervuara:
                pacienti, trajtimi = te_rezervuara[ora]
                rreshta.append(f"  {formato_daten(data_zgjedhur)} ora {ora} - {pacienti} - {trajtimi}")
    else:
        rreshta.append("  asnjë")

    rreshta += ["", "Terminet e lira:"]
    if te_lira:
        for ora in te_lira:
            rreshta.append(f"  {formato_daten(data_zgjedhur)} ora {ora}")
    else:
        rreshta.append("  asnjë")

    rreshta += [
        "",
        f"Përqindja e zënies: {zenia:.1f}%",
        f"Numri i pacientëve: {numri}",
        f"Të hyrat e pritshme: {te_hyrat} €",
        f"Trajtimi më i shpeshtë: {me_i_shpeshti}",
    ]
    return "\n".join(rreshta)


def kredencialet_e_sakta(username, password):
    return hmac.compare_digest(username, STAFI_USERNAME) and hmac.compare_digest(password, STAFI_PASSWORD)


# ---------------- MENUJA E POSHTME ----------------
def hap_faqen(faqja):
    st.session_state["faqja"] = faqja


def stili_menuja(aktive):
    css = """
    <style>
    .st-key-menuja {
        position: fixed;
        bottom: 16px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 999;
        width: auto !important;
        flex-direction: row !important;
        align-items: center;
        gap: 8px !important;
        background: #FFFFFF;
        border: 1px solid #5DCAA5;
        border-radius: 999px;
        padding: 6px;
    }
    .st-key-menuja button {
        height: 48px;
        border: none;
        border-radius: 999px;
        overflow: hidden;
        white-space: nowrap;
        justify-content: flex-start;
        padding: 0 0 0 15px;
        transition: width .45s cubic-bezier(.4, 0, .2, 1),
                    background-color .3s, color .3s;
    }
    .st-key-menuja button > div {
        flex-wrap: nowrap;
        gap: 10px;
    }
    .st-key-menuja button p {
        transition: opacity .3s ease;
        font-size: 15px;
        font-weight: 500;
    }
    .st-key-menuja button[kind="primary"],
    .st-key-menuja [data-testid="stBaseButton-primary"] {
        background-color: #0F6E56;
        color: #FFFFFF;
    }
    .st-key-menuja button[kind="secondary"],
    .st-key-menuja [data-testid="stBaseButton-secondary"] {
        background-color: #F1EFE8;
        color: #5F5E5A;
    }
    """
    for celesi in FAQET:
        if celesi == aktive:
            css += f"""
    .st-key-menu_{celesi} button {{ width: 180px; }}
    .st-key-menu_{celesi} button p {{ opacity: 1; }}
            """
        else:
            css += f"""
    .st-key-menu_{celesi} button {{ width: 54px; }}
    .st-key-menu_{celesi} button p {{ opacity: 0; }}
            """
    css += "</style>"
    return css


def menuja_e_poshtme(aktive):
    st.markdown(stili_menuja(aktive), unsafe_allow_html=True)
    with st.container(key="menuja"):
        for celesi, (emri, ikona) in FAQET.items():
            st.button(
                emri,
                icon=ikona,
                key=f"menu_{celesi}",
                type="primary" if celesi == aktive else "secondary",
                on_click=hap_faqen,
                args=(celesi,),
            )


# ---------------- FRONTEND ----------------
def konfirmo_terminin():
    """Thirret kur klikohet butoni 'Konfirmo terminin'."""
    data_zgjedhur = st.session_state.get("data_e_terminit")
    ora = st.session_state.get("ora_e_terminit")
    sherbimi = st.session_state.get("sherbimi_i_terminit")
    emri = " ".join(st.session_state.get("emri_i_pacientit", "").replace(",", " ").split())

    if not emri:
        st.session_state["mesazhi"] = ("gabim", "Ju lutem shkruani emrin dhe mbiemrin.")
        return
    if not ora or ora not in TERMINET_E_DITES:
        st.session_state["mesazhi"] = ("gabim", "Ju lutem zgjidhni një orë të lirë.")
        return

    # Kontrollohet edhe një herë, në rast se dikush e ka zënë orën në ndërkohë
    te_rezervuara = lexo_terminet(data_zgjedhur)
    if ora in te_rezervuara:
        te_lira = terminet_e_lira(te_rezervuara)
        if te_lira:
            tekst = f"Kjo orë sapo u zu. Termini i parë i lirë është në orën {te_lira[0]}."
        else:
            tekst = "Kjo orë sapo u zu dhe nuk ka më terminet të lira për këtë datë."
        st.session_state["mesazhi"] = ("gabim", tekst)
        return

    ruaj_termin(data_zgjedhur, ora, emri, sherbimi)
    st.session_state["mesazhi"] = (
        "sukses",
        f"Termini u caktua me sukses, {emri}. "
        f"{data_me_fjale(data_zgjedhur)}, ora {ora}, {sherbimi} ({TRAJTIMET[sherbimi]} €).",
    )
    st.session_state["emri_i_pacientit"] = ""


def faqja_e_klientit():
    mesazhi = st.session_state.pop("mesazhi", None)
    if mesazhi:
        tipi, tekst = mesazhi
        if tipi == "sukses":
            st.success(tekst)
        else:
            st.error(tekst)

    k1, k2, k3 = st.columns(3)

    with k1:
        with st.container(border=True):
            st.caption("1. Data")
            data_zgjedhur = st.date_input(
                "Data",
                value=date.today(),
                min_value=date.today(),
                format="DD.MM.YYYY",
                key="data_e_terminit",
                label_visibility="collapsed",
            )

    te_rezervuara = lexo_terminet(data_zgjedhur)
    te_lira = terminet_e_lira(te_rezervuara)

    with k2:
        with st.container(border=True):
            st.caption("2. Ora")
            if te_lira:
                st.selectbox(
                    "Ora",
                    te_lira,
                    key="ora_e_terminit",
                    label_visibility="collapsed",
                )
            else:
                st.write("Nuk ka orë të lira")

    with k3:
        with st.container(border=True):
            st.caption("3. Shërbimi")
            st.selectbox(
                "Shërbimi",
                list(TRAJTIMET),
                format_func=lambda t: f"{t} - {TRAJTIMET[t]} €",
                key="sherbimi_i_terminit",
                label_visibility="collapsed",
            )

    st.write(f"Data e zgjedhur: **{data_me_fjale(data_zgjedhur)}**")

    if not te_lira:
        st.warning("Na vjen keq, për këtë datë nuk ka asnjë termin të lirë.")
        return

    st.caption("Terminet e lira: " + ", ".join(te_lira))

    st.text_input("Emri dhe mbiemri", key="emri_i_pacientit")
    st.button("Konfirmo terminin", type="primary", on_click=konfirmo_terminin)


def faqja_e_stafit():
    st.subheader("Paneli i stafit")

    if not st.session_state.get("i_loguar"):
        with st.form("forma_e_hyrjes"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            hyr = st.form_submit_button("Logohu", type="primary")
        if hyr:
            if kredencialet_e_sakta(username.strip(), password.strip()):
                st.session_state["i_loguar"] = True
                st.rerun()
            else:
                st.error("Username ose password i pasaktë.")
        return

    st.success(f"Mirë se erdhët, {STAFI_USERNAME}!")
    if st.button("Dil nga llogaria"):
        st.session_state["i_loguar"] = False
        st.rerun()

    st.markdown("#### Raporti për ditën")
    data_zgjedhur = st.date_input(
        "Për cilën ditë dëshironi raportin?",
        value=date.today(),
        format="DD.MM.YYYY",
        key="data_e_raportit",
    )

    te_rezervuara = lexo_terminet(data_zgjedhur)
    raporti = ndertro_raportin(te_rezervuara, data_zgjedhur)

    numri, te_hyrat, zenia, _ = statistikat(te_rezervuara)
    k1, k2, k3 = st.columns(3)
    with k1:
        with st.container(border=True):
            st.metric("Pacientë", numri)
    with k2:
        with st.container(border=True):
            st.metric("Të hyrat e pritshme", f"{te_hyrat} €")
    with k3:
        with st.container(border=True):
            st.metric("Përqindja e zënies", f"{zenia:.1f}%")

    with st.container(border=True):
        st.text(raporti)

    st.download_button(
        "Shkarko raportin (.txt)",
        data=raporti,
        file_name=f"raporti_{data_zgjedhur.strftime('%d-%m-%Y')}.txt",
        mime="text/plain",
    )


def main():
    st.set_page_config(page_title="Family Dental Care", page_icon="🦷")
    st.markdown(STILI, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="kreu">
            <div class="logo">🦷</div>
            <div>
                <p class="emri">Family Dental Care</p>
                <p class="orari">Hapur çdo ditë, 09:00 - 17:00 · Çdo termin zgjat 30 minuta</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "faqja" not in st.session_state:
        st.session_state["faqja"] = "termin"
    faqja = st.session_state["faqja"]

    if faqja == "termin":
        faqja_e_klientit()
    else:
        faqja_e_stafit()

    menuja_e_poshtme(faqja)


if __name__ == "__main__":
    main()