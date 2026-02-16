import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

st.set_page_config(layout="centered")

@st.cache_data
def load_data():
    df = pd.read_csv("PBOC.csv", encoding="utf-8-sig")
    df.columns = df.columns.str.strip()
    return df

df = load_data()

# =============================
# Sidebar Filters
# =============================
st.sidebar.title("Filters")

product = st.sidebar.selectbox(
    "Product",
    sorted(df["PRODUCT"].dropna().unique())
)

regions = st.sidebar.multiselect(
    "Regions",
    sorted(df["REGION - NEW"].dropna().unique()),
    default=["Australasia"]
)

#Machine SIZE
df["SIZE"] = pd.to_numeric(df["SIZE"], errors="coerce")

size_min = int(df["SIZE"].min())
size_max = int(df["SIZE"].max())

# default size by product
default_sizes = {
    "DOZER": 430,
    "HYD EXCAVATOR": 500,
    "TRUCK": 250,
    "DRILL": 50,
    "GRADER": 185,
    "WHEEL LOADER":1000
}

# Get default for selected product
default_size = default_sizes.get(product, size_min)

# Ensure default is within dataset bounds
default_size = max(size_min, min(default_size, size_max))

size_selected = st.sidebar.slider(
    "> Machine Size (t)",
    min_value=size_min,
    max_value=size_max,
    value=default_size,
    step=10
)

TOP_N = st.sidebar.slider("Top N models", 5, 20, 10)

# =============================
# Main Page
# =============================
st.header("Machines Chart - Mammoth Equipment")

# ---- Apply filters ----
product_df = df[df["PRODUCT"] == product]
product_df = product_df[product_df["REGION - NEW"].isin(regions)]
product_df = product_df[product_df["SIZE"] >= size_selected]

if product_df.empty:
    st.warning("No machines match current filters.")
    st.stop()

# ---- Compute top models ----
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

# Sort ascending
stacked = stacked.loc[stacked.sum(axis=1).sort_values().index]

# ---- Plot ----
fig, ax = plt.subplots(figsize=(8, 5))

stacked.plot(kind="barh", stacked=True, ax=ax)

ax.set_title(
    f"{product} – Models by Region",
    fontweight="bold"
)

ax.set_xlabel("Number of Machines")
ax.set_ylabel("Machine Model")

ax.legend(loc="lower right")

# Add caption INSIDE figure
summary_text = f"Showing {len(product_df):,} machines, with Size ≥ {size_selected} t. Source: ParkerBayOpenCut"

fig.text(
    0.5,
    -0.02,
    summary_text,
    ha="center",
    fontsize=10
)

# ---- Export Button ----
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


