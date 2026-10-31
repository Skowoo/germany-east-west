
import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from api.eurostat_client import get_gdp_data
from config.regions import BERLIN, get_region_group
from plotly.subplots import make_subplots


def format_number(value: float | None, decimals: int = 0) -> str:
    if value is None:
        return "Brak danych"

    return f"{value:,.{decimals}f}".replace(",", "\u00a0").replace(".", ",")


st.set_page_config(
    page_title="Niemcy: Wschód i Zachód",
    page_icon="🇩🇪",
    layout="wide",
)

st.title("Niemcy: Wschód i Zachód")
st.caption("Analiza regionalnego PKB na mieszkańca")

st.sidebar.header("Filtry")

@st.cache_data(ttl=3600)
def load_data():
    return get_gdp_data()


try:
    with st.spinner("Pobieranie danych Eurostatu..."):
        df = load_data()

except (httpx.HTTPError, RuntimeError, ValueError, KeyError) as error:
    st.error(f"Nie udało się pobrać danych: {error}")
    st.stop()


df["geo"] = df["geo"].fillna("").astype(str)
df["year"] = pd.to_numeric(df["time"], errors="coerce")
df["value"] = pd.to_numeric(df["value"], errors="coerce")

df["group"] = df["geo"].apply(get_region_group)

df = df[
    df["geo"].str.startswith("DE")
    & (df["geo"].str.len() == 4)
    & (df["geo"] != BERLIN)
    & df["group"].notna()
    & df["value"].notna()
].copy()

if df.empty:
    st.warning("Brak dostępnych danych dla niemieckich regionów.")
    st.stop()

group_names = {"East": "Wschód", "West": "Zachód"}

region_names: dict[str, str] = {}
for code, name in df[["geo", "geo_label"]].drop_duplicates("geo").itertuples(
    index=False,
    name=None,
):
    region_names[code] = (
        name.strip() if isinstance(name, str) and name.strip() else code
    )

years = sorted(df["year"].dropna().astype(int).unique().tolist())

selected_year_range = st.sidebar.select_slider(
    "Zakres lat",
    options=years,
    value=(years[0], years[-1]),
)

selected_groups = st.sidebar.multiselect(
    "Grupy historyczne",
    ["East", "West"],
    default=["East", "West"],
    format_func=lambda group: group_names[group],
)

region_options = sorted(
    df.loc[df["group"].isin(selected_groups), "geo"].unique(),
    key=lambda code: region_names.get(str(code), str(code)),
)
available_years = [
    year
    for year in years
    if selected_year_range[0] <= year <= selected_year_range[1]
]

selected_year = st.sidebar.selectbox(
    "Rok",
    available_years,
    index=len(available_years) - 1,
)

selected_regions = st.sidebar.multiselect(
    "Regiony",
    region_options,
    default=region_options,
    format_func=lambda code: region_names.get(str(code), str(code)),
)

filtered_df = df[
    (df["year"] == selected_year)
    & df["geo"].isin(selected_regions)
    & df["group"].isin(selected_groups)
].copy()

if filtered_df.empty:
    st.warning(
        "Brak danych dla wybranego roku i regionów. Metryki zależne od wybranych "
        "regionów pokażą brak danych, a wykres regionalny zostanie pominięty. "
        "Analizy w czasie nadal mogą zawierać dane."
    )

east = filtered_df[filtered_df["group"] == "East"]["value"]
west = filtered_df[filtered_df["group"] == "West"]["value"]
regional_values = df[df["year"] == selected_year]["value"]

east_median = east.median() if not east.empty else None
west_median = west.median() if not west.empty else None
regional_median = regional_values.median() if not regional_values.empty else None

difference = (
    (east_median / west_median - 1) * 100
    if east_median is not None and west_median not in (None, 0)
    else None
)
ratio = (
    east_median / west_median
    if east_median is not None and west_median not in (None, 0)
    else None
)
regional_gap = (
    (east_median / regional_median - 1) * 100
    if east_median is not None and regional_median not in (None, 0)
    else None
)

st.subheader(f"Podsumowanie — {selected_year}")
st.caption(
    "Najważniejsze wskaźniki dla wybranego roku. Mediany grup uwzględniają "
    "wybrane regiony, a mediana referencyjna obejmuje wszystkie analizowane "
    "regiony NUTS 2."
)

col1, col2, col3 = st.columns(3)

col1.metric(
    "Mediana PKB na mieszkańca — Wschód",
    format_number(east_median),
)

col2.metric(
    "Mediana PKB na mieszkańca — Zachód",
    format_number(west_median),
)

col3.metric(
    "Różnica Wschód–Zachód",
    f"{format_number(difference, 1)}%" if difference is not None else "Brak danych",
)

col4, col5, col6 = st.columns(3)

col4.metric(
    "Relacja Wschód / Zachód",
    f"{format_number(ratio, 2)}×" if ratio is not None else "Brak danych",
)

col5.metric(
    "Mediana niemieckich regionów NUTS 2",
    format_number(regional_median),
    help="Mediana wszystkich uwzględnionych regionów dla wybranego roku; nie zmienia się wraz z filtrami grup i regionów.",
)

col6.metric(
    "Wschód względem mediany regionalnej",
    f"{format_number(regional_gap, 1)}%"
    if regional_gap is not None
    else "Brak danych",
)

st.caption(
    "PKB na mieszkańca podano w standardzie siły nabywczej (PPS); wskaźniki "
    "procentowe porównują mediany regionalne."
)

trend_source = df[
    df["year"].between(*selected_year_range)
    & df["geo"].isin(selected_regions)
    & df["group"].isin(selected_groups)
]

trend_df = (
    trend_source.groupby(["year", "group"], as_index=False)["value"]
    .median()
)

if trend_df.empty:
    st.info("Brak danych dla wybranych grup, regionów i zakresu lat.")
    st.stop()

st.divider()

st.subheader("Luka Wschód–Zachód w czasie")
st.caption(
    "Zmiana procentowa mediany Wschodu względem mediany Zachodu w każdym roku. "
    "Wartość poniżej 0% oznacza niższą medianę na Wschodzie."
)

if {"East", "West"}.issubset(trend_df["group"].unique()):
    gap_df = (
        trend_df.pivot(index="year", columns="group", values="value")
        .dropna(subset=["East", "West"])
        .reset_index()
    )
    gap_df = gap_df[gap_df["West"] != 0].copy()
    gap_df["gap"] = (gap_df["East"] / gap_df["West"] - 1) * 100

    if gap_df.empty:
        st.info("Brak danych obu grup w tym samym roku dla wybranych filtrów.")
    else:
        gap_fig = px.line(
            gap_df,
            x="year",
            y="gap",
            markers=True,
            labels={
                "year": "Rok",
                "gap": "Różnica mediany Wschodu względem Zachodu (%)",
            },
        )
        gap_fig.add_hline(y=0, line_dash="dash", line_color="#808080")
        gap_fig.update_traces(
            line_color="#8C4B8F",
            hovertemplate="Rok: %{x}<br>Różnica: %{y:.1f}%<extra></extra>",
        )
        st.plotly_chart(gap_fig, use_container_width=True)
else:
    st.info("Wybierz obie grupy historyczne, aby zobaczyć lukę Wschód–Zachód.")

st.divider()

trend_df["group_name"] = trend_df["group"].map(group_names)

st.subheader("Poziom PKB na mieszkańca w czasie")
st.caption(
    "Porównaj poziom mediany między grupami. Wartość pokazuje poziom PKB, "
    "nie tempo wzrostu."
)

trend_fig = px.line(
    trend_df,
    x="year",
    y="value",
    color="group_name",
    markers=True,
    color_discrete_map={
        "Wschód": "#D96B6B",
        "Zachód": "#5B8DB8",
    },
    labels={
        "value": "PKB na mieszkańca (PPS)",
        "year": "Rok",
        "group_name": "Grupa historyczna",
    },
)

trend_fig.update_layout(
    legend_title_text="Grupa historyczna",
)

st.plotly_chart(trend_fig, use_container_width=True)

st.divider()

st.caption("Łączna zmiana mediany grupy w wybranym okresie")
if selected_groups:
    growth_columns = st.columns(len(selected_groups))

    for column, group in zip(growth_columns, selected_groups):
        group_trend = trend_df[trend_df["group"] == group].sort_values("year")
        growth = None

        if len(group_trend) >= 2 and group_trend.iloc[0]["value"] != 0:
            growth = (
                group_trend.iloc[-1]["value"] / group_trend.iloc[0]["value"] - 1
            ) * 100

        period = (
            f"{int(group_trend.iloc[0]['year'])}–{int(group_trend.iloc[-1]['year'])}"
            if not group_trend.empty
            else "wybrany okres"
        )
        column.metric(
            f"Zmiana — {group_names[group]} ({period})",
            f"{format_number(growth, 1)}%"
            if growth is not None
            else "Brak danych",
            help="Zmiana procentowa między medianą grupy w pierwszym i ostatnim dostępnym roku okresu; nie jest to średnioroczne tempo wzrostu.",
        )
else:
    st.info("Wybierz co najmniej jedną grupę, aby zobaczyć zmianę w czasie.")

st.divider()

if not filtered_df.empty:
    st.subheader(f"PKB na mieszkańca według regionu — {selected_year}")
    st.caption(
        "Porównaj regiony dla wybranego roku. Dłuższy słupek oznacza wyższy PKB "
        "na mieszkańca (PPS); kolor wskazuje grupę historyczną."
    )

    sorted_df = filtered_df.sort_values("value")
    sorted_df["region_name"] = sorted_df["geo"].map(region_names)
    sorted_df["group_name"] = sorted_df["group"].map(group_names)

    fig = px.bar(
        sorted_df,
        x="value",
        y="region_name",
        color="group_name",
        orientation="h",
        hover_data={"geo": True, "geo_label": False},
        color_discrete_map={
            "Wschód": "#D96B6B",
            "Zachód": "#5B8DB8",
        },
        labels={
            "value": "PKB na mieszkańca (PPS)",
            "region_name": "Region",
            "group_name": "Grupa historyczna",
        },
    )

    fig.update_layout(
        yaxis={
            "categoryorder": "array",
            "categoryarray": sorted_df["region_name"].tolist(),
        }
    )

    st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("PKB na mieszkańca w regionach w czasie")
st.caption(
    "Pasek przy każdym wierszu oznacza grupę: czerwony — Wschód, niebieski — "
    "Zachód. Odcień komórki pokazuje poziom PKB na mieszkańca (PPS); puste "
    "pole oznacza brak danych."
)

heatmap_source = trend_source.copy()
heatmap_source["region_name"] = heatmap_source["geo"].map(region_names)
initial_values = (
    heatmap_source.sort_values("year")
    .groupby("geo", as_index=False)
    .first()[["geo", "value"]]
    .rename(columns={"value": "initial_value"})
)
region_metadata = (
    heatmap_source[["geo", "group", "region_name"]]
    .drop_duplicates("geo")
    .merge(initial_values, on="geo")
    .sort_values(["initial_value", "region_name"], ascending=[False, True])
)
region_order = region_metadata["geo"].tolist()
region_labels = region_metadata["region_name"].tolist()
color_min = float(heatmap_source["value"].min())
color_max = float(heatmap_source["value"].max())
if color_min == color_max:
    padding = max(abs(color_min) * 0.01, 0.5)
    color_min -= padding
    color_max += padding

heatmap_data = (
    heatmap_source.pivot_table(
        index="geo",
        columns="year",
        values="value",
        aggfunc="median",
    )
    .reindex(region_order)
)
group_codes = [0 if group == "East" else 1 for group in region_metadata["group"]]
group_colors = [
    [0.0, "#D96B6B"],
    [0.499, "#D96B6B"],
    [0.5, "#5B8DB8"],
    [1.0, "#5B8DB8"],
]

heatmap_fig = make_subplots(
    rows=1,
    cols=2,
    shared_yaxes=True,
    column_widths=[0.035, 0.965],
    horizontal_spacing=0.01,
)
heatmap_fig.add_trace(
    go.Heatmap(
        z=[[code] for code in group_codes],
        x=["Grupa"],
        y=region_labels,
        zmin=0,
        zmax=1,
        colorscale=group_colors,
        showscale=False,
        xgap=2,
        ygap=2,
        customdata=[
            [group_names[group]] for group in region_metadata["group"]
        ],
        hovertemplate="%{customdata}<extra></extra>",
    ),
    row=1,
    col=1,
)
heatmap_fig.add_trace(
    go.Heatmap(
        z=heatmap_data.to_numpy(),
        x=heatmap_data.columns.tolist(),
        y=region_labels,
        zmin=color_min,
        zmax=color_max,
        colorscale="Blues",
        colorbar={"title": "PKB na mieszkańca (PPS)"},
        xgap=2,
        ygap=2,
        hovertemplate=(
            "Region: %{y}<br>"
            "Rok: %{x}<br>"
            "PKB na mieszkańca: %{z:.0f} PPS"
            "<extra></extra>"
        ),
    ),
    row=1,
    col=2,
)
heatmap_fig.update_xaxes(showticklabels=False, ticks="", row=1, col=1)
heatmap_fig.update_xaxes(title_text="Rok", row=1, col=2)
heatmap_fig.update_yaxes(
    title_text="Region",
    categoryorder="array",
    categoryarray=region_labels,
    autorange="reversed",
    row=1,
    col=1,
)
heatmap_fig.update_layout(
    plot_bgcolor="#F1F3F5",
    yaxis2={"showticklabels": False},
)

st.plotly_chart(heatmap_fig, use_container_width=True)