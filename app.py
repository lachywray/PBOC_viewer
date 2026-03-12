import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

st.set_page_config(layout="centered")

# =============================
# Load Data
# =============================

@st.cache_data
def load_data():
    df = pd.read_csv("PBOC.csv", encoding="utf-8-sig")
    df.columns = df.columns.str.strip()
    return df

df = load_data()
df["SIZE"] = pd.to_numeric(df["SIZE"], errors="coerce")

# =============================
# Sidebar (Shared Filters)
# =============================

st.sidebar.title("Filters")

regions = st.sidebar.multiselect(
    "Regions",
    sorted(df["REGION - NEW"].dropna().unique()),
    default=["Australasia"]
)

# mfrs = st.sidebar.multiselect(
#     "MFR",
#     sorted(df["MFR GROUP"].dropna().unique()),
#     default=sorted(df["MFR GROUP"].dropna().unique())
# )

mfrs = st.sidebar.multiselect(
    "MFR",
    sorted(df["MFR GROUP"].dropna().unique()),
    default=[
        m for m in ["LIEBHERR", "CATERPILLAR", "KOMATSU"]
        if m in df["MFR GROUP"].unique()
    ]
)
# =============================
# Default Size Thresholds
# =============================

default_sizes = {
    "DOZER": 430,
    "HYD EXCAVATOR": 500,
    "TRUCK": 250,
    "DRILL": 50,
    "GRADER": 185,
    "WHEEL LOADER": 1000
}

# =============================
# Attenuation Rule Engine
# =============================

def attenuation_rules(product, size):

    rules = {
        "Exhaust": False,
        "Radiator Attenuation": False,
        "Engine Bay & Doors": False,
        "Belly Panels & Doors": False,
        "Horse Collar": False,
        "Engine Roof / Bonnet": False,
        "Electrical / Gridbox": False,
        "Engine Room Top Mount": False,
        "Blower Duct": False,
        "Hydraulic Fan I/O": False,
        "Engine Fan I/O": False
    }

    if product == "DOZER":
        rules["Exhaust"] = True
        rules["Engine Bay & Doors"] = True
        rules["Belly Panels & Doors"] = True
        rules["Engine Roof / Bonnet"] = True

    elif product == "HYD EXCAVATOR":
        if size >= 600:
            for k in rules: rules[k] = True
            rules["Horse Collar"] = False
            rules["Blower Duct"] = False
            rules["Electrical / Gridbox"] = False
        elif size >= 500:
            for k in rules: rules[k] = True
            rules["Horse Collar"] = False
            rules["Blower Duct"] = False
            rules["Electrical / Gridbox"] = False
        else:
            rules["Exhaust"] = True
            rules["Radiator Attenuation"] = True
            rules["Engine Bay & Doors"] = True
            rules["Engine Fan I/O"] = True

    elif product == "TRUCK":
        rules["Exhaust"] = True
        if size >= 300:
            rules["Radiator Attenuation"] = True
            rules["Engine Bay & Doors"] = True
            rules["Belly Panels & Doors"] = True
            rules["Engine Roof / Bonnet"] = True
            rules["Horse Collar"] = True
            rules["Electrical / Gridbox"] = True
            rules["Blower Duct"] = True
            rules["Engine Fan I/O"] = True
        elif size >= 250:
            rules["Radiator Attenuation"] = True
            rules["Engine Bay & Doors"] = True
            rules["Belly Panels & Doors"] = True
            rules["Engine Roof / Bonnet"] = True
            rules["Horse Collar"] = True

    elif product == "DRILL":
        rules["Exhaust"] = True
        rules["Engine Bay & Doors"] = True
        rules["Radiator Attenuation"] = True
        rules["Belly Panels & Doors"] = True
        rules["Engine Roof / Bonnet"] = True

    elif product == "GRADER":
        rules["Exhaust"] = True
        rules["Engine Bay & Doors"] = True
        rules["Radiator Attenuation"] = True
        rules["Belly Panels & Doors"] = True
        rules["Engine Roof / Bonnet"] = True

    elif product == "WHEEL LOADER":
        rules["Exhaust"] = True
        rules["Engine Bay & Doors"] = True
        rules["Radiator Attenuation"] = True
        rules["Belly Panels & Doors"] = True
        rules["Engine Roof / Bonnet"] = True

    return rules


# =============================
# Tabs
# =============================

tab1, tab2 = st.tabs(["📊 Charts", "📋 Top 10 Per Product"])

# ==========================================================
# TAB 1 — ORIGINAL CHART VIEW
# ==========================================================

with tab1:

    product = st.sidebar.selectbox(
        "Product",
        sorted(df["PRODUCT"].dropna().unique())
    )

    size_min = int(df["SIZE"].min())
    size_max = int(df["SIZE"].max())

    default_size = default_sizes.get(product, size_min)
    default_size = max(size_min, min(default_size, size_max))

    size_selected = st.sidebar.slider(
        "> Machine Size (t)",
        min_value=size_min,
        max_value=size_max,
        value=default_size,
        step=10
    )

    TOP_N = st.sidebar.slider("Top N models", 5, 20, 10)

    st.header("Machines Chart - Mammoth Equipment")

    product_df = df[df["PRODUCT"] == product]
    product_df = product_df[product_df["REGION - NEW"].isin(regions)]
    product_df = product_df[product_df["MFR GROUP"].isin(mfrs)]
    product_df = product_df[product_df["SIZE"] >= size_selected]

    if product_df.empty:
        st.warning("No machines match current filters.")
        st.stop()

    top_models = (
        product_df.groupby(["MFR GROUP", "MODEL"])
        .size()
        .sort_values(ascending=False)
        .head(TOP_N)
        .index
    )

    plot_df = (
        product_df
        .set_index(["MFR GROUP", "MODEL"])
        .loc[top_models]
        .reset_index()
    )

    stacked = (
        plot_df.groupby(["MFR GROUP", "MODEL", "REGION - NEW"])
        .size()
        .unstack(fill_value=0)
    )

    stacked = stacked.loc[stacked.sum(axis=1).sort_values().index]

    fig, ax = plt.subplots(figsize=(8, 5))
    stacked.plot(kind="barh", stacked=True, ax=ax)

    ax.set_title(f"{product} – Models by Region", fontweight="bold")
    ax.set_xlabel("Number of Machines")
    ax.set_ylabel("Machine Model")
    ax.legend(loc="lower right")

    summary_text = (
        f"Showing {len(product_df):,} machines, "
        f"with Size ≥ {size_selected} t. "
        f"Source: ParkerBayOpenCut"
    )

    fig.text(0.5, -0.02, summary_text, ha="center", fontsize=10)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=300)
    buf.seek(0)

    st.download_button(
        label="Download Chart as PNG",
        data=buf,
        file_name=f"{product}_machine_models.png",
        mime="image/png"
    )

    st.pyplot(fig)

# ==========================================================
# TAB 2 — TOP 10 + ATTENUATION MATRIX
# ==========================================================

with tab2:

    st.header("Top 10 Models Per Product + Attenuation Matrix")

    TOP_N = 30
    all_products = []

    for product_name, min_size in default_sizes.items():

        product_df = df[
            (df["PRODUCT"] == product_name) &
            (df["REGION - NEW"].isin(regions)) &
            (df["SIZE"] >= min_size)
        ]

        if product_df.empty:
            continue

        pivot = (
            product_df
            .groupby(["PRODUCT", "MFR GROUP", "MODEL", "SIZE", "REGION - NEW"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )

        region_cols = pivot.columns[4:]
        pivot["TOTAL"] = pivot[region_cols].sum(axis=1)

        pivot = pivot.sort_values("TOTAL", ascending=False).head(TOP_N)

        all_products.append(pivot)

    if not all_products:
        st.warning("No machines match current filters.")
    else:

        final_table = pd.concat(all_products, ignore_index=True)

        attenuation_data = final_table.apply(
            lambda row: attenuation_rules(row["PRODUCT"], row["SIZE"]),
            axis=1
        )

        attenuation_df = pd.DataFrame(list(attenuation_data))
        attenuation_df = attenuation_df.replace({
            True: "Y",
            False: ""
        })

        final_table = pd.concat(
            [final_table.reset_index(drop=True),
             attenuation_df.reset_index(drop=True)],
            axis=1
        )

        final_table = final_table.sort_values(
            ["PRODUCT", "TOTAL"],
            ascending=[True, False]
        )

        st.dataframe(final_table, use_container_width=True)

        csv = final_table.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Top 10 + Attenuation Matrix (CSV)",
            data=csv,
            file_name="Top10_With_Attenuation_Matrix.csv",
            mime="text/csv"
        )