import streamlit as st
import pandas as pd
import mysql.connector
import matplotlib.pyplot as plt
import seaborn as sns
import squarify

# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(
    page_title="ChocoCrunch Dashboard",
    page_icon="🍫",
    layout="wide"
)

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
div[data-testid="metric-container"] {
    background-color: #1f2933;
    border-radius: 12px;
    padding: 15px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# DB
# -----------------------------
@st.cache_resource
def get_connection():
    return mysql.connector.connect(
        host='gateway01.ap-southeast-1.prod.aws.tidbcloud.com',
        port=4000,
        user='EnD345nfx9wxmnG.root',
        password='Q4KKSkNgKxF3JIPn',
        database='choco_crunch'
    )

@st.cache_data(ttl=600)
def load_main_data():
    query = """
    SELECT p.product_code, p.product_name, p.brand,
           n.energy_kcal_value, n.sugars_value, n.carbohydrates_value,
           d.sugar_to_carb_ratio, d.calorie_category, d.sugar_category,
           d.is_ultra_processed, n.nova_group,
           n.fruits_vegetables_nuts_estimate_from_ingredients_100g
    FROM product_info p
    JOIN nutrient_info n ON p.product_code = n.product_code
    JOIN derived_metrics d ON p.product_code = d.product_code;
    """
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# -----------------------------
# Header
# -----------------------------
st.title("🍫 ChocoCrunch – Chocolate Nutrition Intelligence")

st.caption(
    "Interactive analytics dashboard for calories, sugar and processing level of chocolate products"
)

df = load_main_data()

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("🎯 Filters")

calorie_opts = sorted(df["calorie_category"].dropna().unique())
sugar_opts   = sorted(df["sugar_category"].dropna().unique())
ultra_opts   = sorted(df["is_ultra_processed"].dropna().unique())

sel_cal = st.sidebar.multiselect(
    "Calorie category", calorie_opts, default=calorie_opts
)
sel_sug = st.sidebar.multiselect(
    "Sugar category", sugar_opts, default=sugar_opts
)
sel_ultra = st.sidebar.multiselect(
    "Ultra processed", ultra_opts, default=ultra_opts
)

df_f = df[
    (df["calorie_category"].isin(sel_cal)) &
    (df["sugar_category"].isin(sel_sug)) &
    (df["is_ultra_processed"].isin(sel_ultra))
]

# -----------------------------
# KPI row
# -----------------------------
k1, k2, k3, k4 = st.columns(4)

k1.metric("Products", len(df_f))
k2.metric("Avg Calories /100g", f"{df_f['energy_kcal_value'].mean():.1f}")
k3.metric("Avg Sugar /100g", f"{df_f['sugars_value'].mean():.1f}")
k4.metric(
    "Ultra-processed",
    int((df_f["is_ultra_processed"] == "Yes").sum())
)

st.divider()

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Overview", "🍫 Brand view", "🧪 Nutrition view", "🗃 Data"]
)

# ======================================================
# TAB 1 – Overview
# ======================================================
with tab1:

    c1, c2 = st.columns(2)

    with c1:
        fig, ax = plt.subplots()
        sns.countplot(
            data=df_f,
            x="calorie_category",
            order=calorie_opts,
            ax=ax
        )
        ax.set_title("Products by calorie category")
        st.pyplot(fig)

    with c2:
        fig2, ax2 = plt.subplots()
        nova = df_f["nova_group"].value_counts().sort_index()
        ax2.pie(nova, labels=nova.index, autopct="%1.0f%%")
        ax2.set_title("NOVA group distribution")
        st.pyplot(fig2)


    fig3, ax3 = plt.subplots(figsize=(9,4))
    corr = df_f[
        ["energy_kcal_value","sugars_value","carbohydrates_value"]
    ].corr()

    sns.heatmap(corr, annot=True, ax=ax3, cmap="coolwarm")
    ax3.set_title("Nutrition correlation")
    st.pyplot(fig3)


# ======================================================
# TAB 2 – Brand view
# ======================================================
with tab2:

    top_brands = (
        df_f["brand"]
        .value_counts()
        .head(10)
        .index
    )

    df_top = df_f[df_f["brand"].isin(top_brands)]

    fig4, ax4 = plt.subplots(figsize=(10,4))
    sns.barplot(
        data=df_top,
        x="brand",
        y="energy_kcal_value",
        estimator="mean",
        ax=ax4
    )
    ax4.set_title("Top brands – average calories")
    ax4.tick_params(axis="x", rotation=40)
    st.pyplot(fig4)


    brand_cat = (
        df_top
        .groupby(["brand","calorie_category"])
        .size()
        .reset_index(name="count")
    )

    labels = brand_cat.apply(
        lambda x: f"{x['brand']}\n{x['calorie_category']}\n{x['count']}",
        axis=1
    )

    fig5, ax5 = plt.subplots(figsize=(11,6))
    squarify.plot(
        sizes=brand_cat["count"],
        label=labels,
        ax=ax5
    )
    ax5.axis("off")
    ax5.set_title("Brand vs calorie category – treemap")
    st.pyplot(fig5)


# ======================================================
# TAB 3 – Nutrition view
# ======================================================
with tab3:

    c3, c4 = st.columns(2)

    with c3:
        fig6, ax6 = plt.subplots()
        sns.scatterplot(
            data=df_f,
            x="energy_kcal_value",
            y="sugars_value",
            hue="is_ultra_processed",
            ax=ax6
        )
        ax6.set_title("Calories vs sugar")
        st.pyplot(fig6)

    with c4:
        fig7, ax7 = plt.subplots(figsize=(6,4))
        sns.boxplot(
            data=df_top,
            x="brand",
            y="sugar_to_carb_ratio",
            ax=ax7
        )
        ax7.tick_params(axis="x", rotation=45)
        ax7.set_title("Sugar to carb ratio (top brands)")
        st.pyplot(fig7)


    high_sugar = (
        df_f[df_f["sugar_category"] == "High Sugar"]["brand"]
        .value_counts()
        .head(10)
    )

    fig8, ax8 = plt.subplots(figsize=(9,4))
    sns.barplot(
        x=high_sugar.index,
        y=high_sugar.values,
        ax=ax8
    )
    ax8.set_title("High sugar products – top brands")
    ax8.tick_params(axis="x", rotation=40)
    ax8.set_ylabel("Count")
    st.pyplot(fig8)


# ======================================================
# TAB 4 – Data browser
# ======================================================
with tab4:

    st.subheader("Filtered product table")

    show_cols = st.multiselect(
        "Select columns",
        df_f.columns.tolist(),
        default=[
            "product_name","brand","energy_kcal_value",
            "sugars_value","calorie_category",
            "sugar_category","is_ultra_processed"
        ]
    )

    st.dataframe(
        df_f[show_cols],
        use_container_width=True,
        height=500
    )
