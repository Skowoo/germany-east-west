
import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from api.eurostat_client import get_employment_data, get_gdp_data
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


@st.cache_data(ttl=3600)
def load_employment_data():
    return get_employment_data()


try:
    with st.spinner("Pobieranie danych Eurostatu..."):
        df = load_data()

except (httpx.HTTPError, RuntimeError, ValueError, KeyError) as error:
    st.error(f"Nie udało się pobrać danych: {error}")
    st.stop()

try:
    with st.spinner("Pobieranie danych o zatrudnieniu..."):
        employment_df = load_employment_data()
except (httpx.HTTPError, RuntimeError, ValueError, KeyError) as error:
    st.warning(f"Nie udało się pobrać danych o zatrudnieniu: {error}")
    employment_df = pd.DataFrame()

if not employment_df.empty:
    employment_df["geo"] = employment_df["geo"].fillna("").astype(str)
    employment_df["year"] = pd.to_numeric(
        employment_df["time"],
        errors="coerce",
    )
    employment_df["value"] = pd.to_numeric(
        employment_df["value"],
        errors="coerce",
    )
    employment_df["group"] = employment_df["geo"].apply(get_region_group)
    employment_df = employment_df[
        employment_df["geo"].str.startswith("DE")
        & (employment_df["geo"].str.len() == 4)
        & (employment_df["geo"] != BERLIN)
        & employment_df["group"].notna()
        & employment_df["value"].notna()
    ].copy()


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

employment_trend_df = pd.DataFrame(columns=["year", "group", "value"])
if not employment_df.empty:
    employment_trend_source = employment_df[
        employment_df["year"].between(*selected_year_range)
        & employment_df["geo"].isin(selected_regions)
        & employment_df["group"].isin(selected_groups)
    ]
    employment_trend_df = (
        employment_trend_source.groupby(
            ["year", "group"],
            as_index=False,
        )["value"]
        .median()
    )

st.divider()

st.subheader("Obserwacje i interpretacja")
st.caption(
    "Poniższe obserwacje są opisowe i zależą od wybranych filtrów. Nie wyjaśniają "
    "przyczyn różnic ani nie stanowią testu istotności statystycznej."
)

if {"East", "West"}.issubset(trend_df["group"].unique()):
    insight_gap_df = (
        trend_df.pivot(index="year", columns="group", values="value")
        .dropna(subset=["East", "West"])
        .reset_index()
    )
    insight_gap_df = insight_gap_df[insight_gap_df["West"] != 0].copy()
    insight_gap_df["gap"] = (
        insight_gap_df["East"] / insight_gap_df["West"] - 1
    ) * 100

    if insight_gap_df.empty:
        st.info("Brak wspólnych lat z danymi obu grup do opisania luki.")
    else:
        first_gap = insight_gap_df.iloc[0]
        last_gap = insight_gap_df.iloc[-1]

        if len(insight_gap_df) == 1:
            gap_direction = (
                "wyższą medianę ma Wschód"
                if last_gap["gap"] > 0
                else "wyższą medianę ma Zachód"
                if last_gap["gap"] < 0
                else "mediany obu grup są równe"
            )
            st.write(
                f"W {int(last_gap['year'])} luka wynosi "
                f"{format_number(last_gap['gap'], 1)}%; {gap_direction}."
            )
        else:
            gap_magnitude_change = abs(last_gap["gap"]) - abs(first_gap["gap"])
            gap_change = last_gap["gap"] - first_gap["gap"]
            if gap_magnitude_change < 0:
                gap_interpretation = "bezwzględna wielkość luki zmalała"
            elif gap_magnitude_change > 0:
                gap_interpretation = "bezwzględna wielkość luki wzrosła"
            else:
                gap_interpretation = "bezwzględna wielkość luki pozostała bez zmian"

            gap_direction = (
                "na końcu okresu wyższą medianę ma Wschód"
                if last_gap["gap"] > 0
                else "na końcu okresu wyższą medianę ma Zachód"
                if last_gap["gap"] < 0
                else "na końcu okresu mediany obu grup są równe"
            )
            sign_change = (
                " Luka zmieniła znak."
                if first_gap["gap"] * last_gap["gap"] < 0
                else ""
            )
            st.write(
                f"W latach {int(first_gap['year'])}–{int(last_gap['year'])} "
                f"luka zmieniła się z {format_number(first_gap['gap'], 1)}% "
                f"do {format_number(last_gap['gap'], 1)}% "
                f"(zmiana o {format_number(gap_change, 1)} p.p.). "
                f"{gap_interpretation}; {gap_direction}.{sign_change}"
            )
else:
    st.info("Wybierz obie grupy, aby zobaczyć obserwację dotyczącą luki.")

if filtered_df.empty:
    st.info("Brak danych dla wybranego roku i regionów do porównania regionów.")
elif len(filtered_df) == 1:
    region = filtered_df.iloc[0]
    region_name = region_names.get(region["geo"], region["geo"])
    st.write(
        f"W {selected_year} wybrany zestaw obejmuje jeden region: {region_name} "
        f"({format_number(region['value'])} PPS)."
    )
else:
    ranked_regions = filtered_df.sort_values("value")
    lowest_region = ranked_regions.iloc[0]
    highest_region = ranked_regions.iloc[-1]
    highest_name = region_names.get(
        highest_region["geo"],
        highest_region["geo"],
    )
    lowest_name = region_names.get(
        lowest_region["geo"],
        lowest_region["geo"],
    )
    st.write(
        f"W {selected_year} najwyższą wartość w wybranym zestawie ma "
        f"{highest_name} ({format_number(highest_region['value'])} PPS), "
        f"a najniższą {lowest_name} "
        f"({format_number(lowest_region['value'])} PPS)."
    )

if employment_df.empty:
    st.info("Brak dostępnych danych o zatrudnieniu do przygotowania obserwacji.")
elif {"East", "West"}.issubset(employment_trend_df["group"].unique()):
    employment_gap_df = (
        employment_trend_df.pivot(
            index="year",
            columns="group",
            values="value",
        )
        .dropna(subset=["East", "West"])
        .reset_index()
    )
    selected_employment = employment_gap_df[
        employment_gap_df["year"] == selected_year
    ]

    if selected_employment.empty:
        st.info("Brak wspólnych danych o zatrudnieniu dla wybranego roku.")
    else:
        current_employment = selected_employment.iloc[0]
        current_employment_gap = (
            current_employment["East"] - current_employment["West"]
        )
        employment_direction = (
            "wyższa jest na Wschodzie"
            if current_employment_gap > 0
            else "wyższa jest na Zachodzie"
            if current_employment_gap < 0
            else "mediany obu grup są równe"
        )
        st.write(
            f"W {selected_year} mediana stopy zatrudnienia (wiek 15–64 lata) "
            f"wynosi {format_number(current_employment['East'], 1)}% na Wschodzie "
            f"i {format_number(current_employment['West'], 1)}% na Zachodzie "
            f"(różnica {format_number(current_employment_gap, 1)} p.p.; "
            f"{employment_direction})."
        )

        if len(employment_gap_df) > 1:
            first_employment = employment_gap_df.iloc[0]
            last_employment = employment_gap_df.iloc[-1]
            first_employment_gap = (
                first_employment["East"] - first_employment["West"]
            )
            last_employment_gap = (
                last_employment["East"] - last_employment["West"]
            )
            employment_gap_change = (
                abs(last_employment_gap) - abs(first_employment_gap)
            )
            if employment_gap_change < 0:
                employment_gap_trend = "bezwzględna różnica zmalała"
            elif employment_gap_change > 0:
                employment_gap_trend = "bezwzględna różnica wzrosła"
            else:
                employment_gap_trend = (
                    "bezwzględna różnica pozostała bez zmian"
                )
            st.write(
                f"W latach {int(first_employment['year'])}–"
                f"{int(last_employment['year'])} różnica zmieniła się z "
                f"{format_number(first_employment_gap, 1)} p.p. do "
                f"{format_number(last_employment_gap, 1)} p.p.; "
                f"{employment_gap_trend}."
            )
elif len(selected_groups) < 2:
    st.info(
        "Wybierz obie grupy, aby zobaczyć obserwację o różnicy zatrudnienia."
    )
else:
    st.info("Brak wspólnych danych o zatrudnieniu dla obu grup.")

if trend_df.empty:
    st.info("Brak danych dla wybranych grup, regionów i zakresu lat.")
    st.stop()

st.divider()

st.subheader("Luka Wschód–Zachód w czasie")
st.caption(
    "Każdy punkt pokazuje względną różnicę median PKB na mieszkańca "
    "(mediana Wschodu / mediana Zachodu − 1) × 100% w danym roku, dla "
    "wybranych regionów. Wartość ujemna oznacza niższą medianę na Wschodzie, "
    "a 0% — równe mediany. Wykres obejmuje tylko lata z danymi obu grup."
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
        st.plotly_chart(gap_fig, width="stretch")
else:
    st.info("Wybierz obie grupy historyczne, aby zobaczyć lukę Wschód–Zachód.")

st.divider()

trend_df["group_name"] = trend_df["group"].map(group_names)

st.subheader("Poziom PKB na mieszkańca w czasie")
st.caption(
    "Każda linia przedstawia medianę regionalnego PKB na mieszkańca w PPS "
    "dla grupy historycznej w danym roku, obliczoną dla wybranych regionów. "
    "Wykres pokazuje poziom PKB, a nie tempo wzrostu."
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

st.plotly_chart(trend_fig, width="stretch")

st.divider()

st.caption(
    "Zmiana procentowa między medianą PKB na mieszkańca w pierwszym i ostatnim "
    "roku z dostępnymi danymi w wybranym zakresie, liczona osobno dla każdej "
    "grupy i wybranych regionów. To zmiana łączna, nie średnioroczne tempo wzrostu."
)
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

st.subheader("Stopa zatrudnienia w czasie")
st.caption(
    "Każda linia przedstawia medianę regionalnej stopy zatrudnienia — odsetek "
    "zatrudnionych wśród osób w wieku 15–64 lata — dla grupy historycznej "
    "w danym roku i wybranych regionów. Wartości są podane w procentach. "
    "Współwystępowanie trendów z PKB nie wskazuje związku przyczynowego."
)

if employment_df.empty:
    st.info("Dane o zatrudnieniu są obecnie niedostępne.")
elif employment_trend_df.empty:
    st.info("Brak danych o zatrudnieniu dla wybranych filtrów.")
else:
    employment_trend_df["group_name"] = employment_trend_df[
        "group"
    ].map(group_names)
    employment_fig = px.line(
        employment_trend_df,
        x="year",
        y="value",
        color="group_name",
        markers=True,
        color_discrete_map={
            "Wschód": "#D96B6B",
            "Zachód": "#5B8DB8",
        },
        labels={
            "value": "Stopa zatrudnienia (%)",
            "year": "Rok",
            "group_name": "Grupa historyczna",
        },
    )
    employment_fig.update_layout(
        legend_title_text="Grupa historyczna",
    )
    st.plotly_chart(employment_fig, width="stretch")

st.divider()

if not filtered_df.empty:
    st.subheader(f"PKB na mieszkańca według regionu — {selected_year}")
    st.caption(
        "Każdy słupek pokazuje PKB na mieszkańca w PPS dla regionu w wybranym "
        "roku. Dłuższy słupek oznacza wyższą wartość; kolor odróżnia grupy "
        "historyczne. Widoczne są tylko wybrane regiony z dostępnymi danymi."
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

    st.plotly_chart(fig, width="stretch")

st.divider()

st.subheader("PKB na mieszkańca w regionach w czasie")
st.caption(
    "Wiersze oznaczają wybrane regiony, kolumny — lata z wybranego zakresu, "
    "a komórki — regionalny PKB na mieszkańca w PPS. Pasek przy wierszu "
    "oznacza grupę: czerwony — Wschód, niebieski — Zachód. Ciemniejszy odcień "
    "oznacza wyższą wartość w skali wyznaczonej dla aktualnego wyboru; puste "
    "pole oznacza brak danych. Kolejność regionów ustala PKB w pierwszym "
    "dostępnym roku zakresu."
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

st.plotly_chart(heatmap_fig, width="stretch")