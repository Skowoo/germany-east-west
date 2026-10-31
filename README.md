# Germany: East vs West

Interaktywny dashboard w Streamlit porównujący poziom regionalnego PKB na
mieszkańca we wschodnich i zachodnich regionach Niemiec. Celem jest sprawdzenie,
jak duża jest różnica między grupami, jak zmienia się ona w czasie oraz które
regiony odstają od swoich grup.

Interfejs dashboardu jest w języku polskim. Nazwy regionów na wykresach
pozostają zgodne z etykietami źródłowymi Eurostatu.

## Problem analityczny

Czy luka w poziomie PKB na mieszkańca między wschodnimi i zachodnimi regionami
Niemiec zmniejsza się w latach 2000–2024? Które regiony mają najwyższe i
najniższe wartości i jak wybrany zestaw regionów wpływa na porównanie?

### Kontekst i zastosowanie decyzyjne

Odbiorcami dashboardu są analitycy polityki regionalnej oraz osoby przygotowujące
wstępne porównania gospodarcze regionów. Narzędzie ma pomóc im:

- ocenić, czy różnica median PKB na mieszkańca między Wschodem i Zachodem
  zmienia się w analizowanym okresie;
- wskazać regiony o relatywnie niższych wartościach, które warto objąć
  pogłębioną diagnozą;
- wybrać regiony i okresy do dalszej analizy przed zaplanowaniem działań
  rozwojowych lub ewaluacją istniejących programów.

Dashboard wspiera etap rozpoznania i ustalania priorytetów do dalszego badania;
nie rekomenduje samodzielnie alokacji środków ani konkretnych interwencji.
PKB na mieszkańca nie mierzy wszystkich aspektów dobrobytu i nie wyjaśnia
przyczyn różnic. Decyzje powinny uwzględniać również inne dane, np. zatrudnienie,
dochody, demografię i dostęp do usług, oraz lokalny kontekst.

## Dane i źródła

Dashboard korzysta z dwóch zbiorów Eurostatu:

- [Eurostat — Regional gross domestic product (nama_10r_2gdp)](https://ec.europa.eu/eurostat/databrowser/view/nama_10r_2gdp/default/table?lang=en)
- [Eurostat — Employment rates by NUTS 2 region (lfst_r_lfe2emprt)](https://ec.europa.eu/eurostat/databrowser/view/lfst_r_lfe2emprt/default/table?lang=en)
- Dane są pobierane przez [API Eurostat](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/).

Pobierany jest roczny regionalny PKB na mieszkańca w standardzie siły nabywczej
(PPS, UE-27 od 2020 r.) oraz roczna stopa zatrudnienia dla osób w wieku 15–64
lata, jako odsetek populacji tej grupy wieku. Oba zbiory obejmują poziom NUTS 2
i lata 2000–2024. Każdy zbiór jest filtrowany osobno przy użyciu tych samych
mapowań regionów i zakresu lat; wskaźniki są wyliczane i prezentowane osobno.
Wykresy mają odrębne skale.

Kod regionu przypisywany jest do grupy według `config/regions.py`. Wschód obejmuje
Brandenburgię, Meklemburgię-Pomorze Przednie, Drezno, Chemnitz, Lipsk,
Saksonię-Anhalt i Turyngię. Berlin jest wyłączony z porównania, a pozostałe
uwzględnione niemieckie regiony NUTS 2 są klasyfikowane jako Zachód. Wartości
brakujące są pomijane. Filtr i wykres regionalny pokazują nazwy regionów
dostarczone przez Eurostat; kod NUTS pozostaje dostępny w podpowiedzi po
najechaniu na słupek. Jeśli dla regionu brakuje nazwy, interfejs używa kodu NUTS.

## Przygotowanie danych (ETL)

Dashboard realizuje prosty przepływ ETL przy uruchomieniu aplikacji:

1. **Extract** — klient odpytuje API Eurostatu o dwa roczne zbiory NUTS 2:
   PKB na mieszkańca w PPS oraz stopę zatrudnienia osób w wieku 15–64 lata,
   dla lat 2000–2024.
2. **Transform** — odpowiedzi JSON-stat są dekodowane do tabel z kodami i
   etykietami wymiarów oraz wartościami. Aplikacja konwertuje rok i wartość na
   typy liczbowe, przypisuje regiony do grup Wschód/Zachód, a następnie
   uwzględnia niemieckie regiony NUTS 2, wyklucza Berlin i pomija brakujące
   wartości. Te same filtry regionów i lat są stosowane niezależnie do obu
   zbiorów; nie są one łączone w jedną tabelę.
3. **Load** — przetworzone dane są używane w pamięci przez dashboard; każdy
   wynik pobrania jest buforowany przez godzinę. Awaria pobrania danych o
   zatrudnieniu nie blokuje wykresów PKB. Aplikacja nie zapisuje danych w
   zewnętrznej bazie ani pliku.

## Metryki

- **Mediana PKB na mieszkańca grupy** — mediana wartości regionów Wschodu lub
  Zachodu dla wybranego roku. Mediana ogranicza wpływ pojedynczych skrajnych
  regionów.
- **Różnica Wschód–Zachód (%)** — `(mediana Wschodu / mediana Zachodu - 1) × 100`.
  Wartość ujemna oznacza niższą medianę na Wschodzie.
- **Relacja Wschód / Zachód** — `mediana Wschodu / mediana Zachodu`; np. `0,80×`
  oznacza, że mediana Wschodu wynosi 80% mediany Zachodu.
- **Mediana uwzględnionych niemieckich regionów NUTS 2** — mediana wartości
  regionalnych dla wybranego roku. To punkt odniesienia z regionów objętych
  dashboardem, a nie odrębna, oficjalna wartość krajowa dla Niemiec. Metryka
  pozostaje oparta na wszystkich uwzględnionych regionach niezależnie od wyboru
  w filtrze regionów.
- **Wschód względem mediany regionalnej (%)** —
  `(mediana Wschodu / mediana uwzględnionych regionów - 1) × 100`.
- **Zmiana w wybranym okresie (%)** — `(mediana końcowa / mediana początkowa - 1) × 100`,
  obliczana osobno dla każdej wybranej grupy na podstawie jej median w pierwszym
  i ostatnim dostępnym roku z zakresu oraz aktualnie wybranych regionów. Jest to
  zmiana łączna, nie średnioroczne tempo wzrostu; przy mniej niż dwóch
  dostępnych latach wynik to `N/A`.
- **Trend w czasie** — mediany Wschodu i Zachodu dla kolejnych lat, filtrowane
  według wybranego zakresu, grup i regionów.
- **Luka Wschód–Zachód w czasie (%)** — dla każdego roku
  `(mediana Wschodu / mediana Zachodu - 1) × 100`, wyliczone z median grup
  w danym roku i dla wybranych regionów. Wynik poniżej zera oznacza niższą
  medianę na Wschodzie; linia 0% oznacza równe mediany. Wykres wymaga danych
  obu grup w tym samym roku.
- **Stopa zatrudnienia (%)** — mediana regionalnego odsetka zatrudnionych
  osób w wieku 15–64 lata, osobno dla wybranej grupy i roku. Wskaźnik jest
  filtrowany tym samym zakresem lat, grup i regionów co analizy PKB; stanowi
  kontekst rynku pracy, a nie miarę wyjaśniającą poziom PKB.

## Struktura i strategia wizualizacji

Dashboard prowadzi od podsumowania do szczegółów:

1. **Podsumowanie** — sekcja otwierająca dashboard. Karty metryk prezentują
   mediany grup, różnicę procentową, relację Wschód/Zachód i odniesienie do
   mediany regionów dla wybranego roku.
2. **Obserwacje i interpretacja** — tekst podsumowuje zmianę luki między
   pierwszym i ostatnim wspólnym rokiem oraz wskazuje regiony z najwyższą i
   najniższą wartością w wybranym roku. Pokazuje również różnicę median stopy
   zatrudnienia między grupami w wybranym roku oraz zmianę tej luki w zakresie
   lat. Wnioski zmieniają się wraz z filtrami; mają charakter opisowy i nie
   wyjaśniają przyczyn różnic ani nie testują ich istotności statystycznej.
3. **Luka Wschód–Zachód w czasie** — każdy punkt pokazuje względną różnicę
   median PKB na mieszkańca `(mediana Wschodu / mediana Zachodu - 1) × 100%`
   dla wybranych regionów i danego roku. Wartość ujemna oznacza niższą medianę
   na Wschodzie, a 0% — równe mediany; wykres obejmuje lata z danymi obu grup.
4. **Poziom i zmiana w czasie** — wykres liniowy pokazuje mediany regionalnego
   PKB na mieszkańca w PPS dla wybranych grup i regionów. Karty poniżej pokazują
   łączną procentową zmianę między pierwszym i ostatnim rokiem z danymi w
   wybranym zakresie; nie jest to średnioroczne tempo wzrostu. Następny wykres
   pokazuje medianę stopy zatrudnienia, czyli odsetek zatrudnionych osób w wieku
   15–64 lata, dla tych samych filtrów. Wskaźniki mają osobne skale, a ich
   współwystępowanie nie dowodzi związku przyczynowego.
5. **Porównanie regionów** — poziomy wykres słupkowy porządkuje regiony według
   regionalnego PKB na mieszkańca w PPS w wybranym roku; pokazuje tylko wybrane
   regiony z danymi. Dłuższy słupek oznacza wyższą wartość, kolor wskazuje grupę.
6. **Heatmapa region × rok** — jedna mapa pokazuje poziom PKB na mieszkańca
   w PPS dla wybranych regionów i lat. Wąski pasek oznacza grupę: czerwony to
   Wschód, niebieski to Zachód. Odcień głównej mapy pokazuje wartość względem
   skali wyznaczonej dla aktualnego wyboru; puste pole oznacza brak danych.
   Dokładna wartość, region i rok są widoczne po najechaniu na komórkę.
   Regiony są sortowane malejąco według PKB w pierwszym dostępnym roku zakresu;
   wykres słupkowy sortuje je według wybranego roku, więc kolejność może się
   różnić.

Filtry w panelu bocznym pozwalają wybrać rok oraz regiony. Wykresy regionalne,
trendy i heatmapa reagują na zakres lat, wybrane grupy historyczne i regiony.
Wykres luki wymaga wybrania obu grup. Wybrany pojedynczy rok (mieszczący się w
wybranym zakresie) steruje kartami podsumowania i wykresem słupkowym; zakres
lat steruje analizami w czasie. Jeśli nie ma danych dla wybranego roku, karty
metryk zależnych od wybranych regionów pokazują brak danych, wykres słupkowy
jest pomijany, a analizy dla całego zakresu lat nadal są wyświetlane, o ile
zawierają dane. Mediana wszystkich uwzględnionych niemieckich regionów NUTS 2
pozostaje dostępna jako punkt odniesienia dla wybranego roku, niezależnie od
filtrów grup i regionów.

## Uruchomienie

Projekt używa `uv` do zarządzania zależnościami. Z katalogu głównego repozytorium
zainstaluj zależności i uruchom aplikację:

```bash
uv sync
uv run streamlit run src/dashboard_germany/app.py
```

Jeśli pobranie danych PKB zakończy się błędem połączenia, odpowiedzi API lub
formatu danych, aplikacja wyświetla komunikat i zatrzymuje renderowanie. Błąd
pobrania dodatkowego zbioru o zatrudnieniu wyświetla ostrzeżenie, ale nie blokuje
pozostałych wykresów.
