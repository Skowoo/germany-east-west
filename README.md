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

Dashboard korzysta z jednego źródła:

- [Eurostat — Regional gross domestic product (nama_10r_2gdp)](https://ec.europa.eu/eurostat/databrowser/view/nama_10r_2gdp/default/table?lang=en)
- Dane są pobierane z [API Eurostat](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10r_2gdp).

Pobierany jest roczny regionalny PKB na mieszkańca w standardzie siły nabywczej
(PPS, UE-27 od 2020 r.), dla poziomu NUTS 2 i lat 2000–2024. Aplikacja nie łączy
różnych zbiorów ani tabel.

Kod regionu przypisywany jest do grupy według `config/regions.py`. Wschód obejmuje
Brandenburgię, Meklemburgię-Pomorze Przednie, Drezno, Chemnitz, Lipsk,
Saksonię-Anhalt i Turyngię. Berlin jest wyłączony z porównania, a pozostałe
uwzględnione niemieckie regiony NUTS 2 są klasyfikowane jako Zachód. Wartości
brakujące są pomijane. Filtr i wykres regionalny pokazują nazwy regionów
dostarczone przez Eurostat; kod NUTS pozostaje dostępny w podpowiedzi po
najechaniu na słupek. Jeśli dla regionu brakuje nazwy, interfejs używa kodu NUTS.

## Przygotowanie danych (ETL)

Dashboard realizuje prosty przepływ ETL przy uruchomieniu aplikacji:

1. **Extract** — klient odpytuje API Eurostatu o roczne dane NUTS 2 dla lat
   2000–2024, w jednostce PKB na mieszkańca PPS.
2. **Transform** — odpowiedź JSON-stat jest dekodowana do tabeli z kodami i
   etykietami wymiarów oraz wartościami. Aplikacja konwertuje rok i wartość na
   typy liczbowe, przypisuje regiony do grup Wschód/Zachód, a następnie
   uwzględnia niemieckie regiony NUTS 2, wyklucza Berlin i pomija brakujące
   wartości.
3. **Load** — przetworzone dane są używane w pamięci przez dashboard; wynik
   pobrania jest buforowany przez godzinę. Aplikacja nie zapisuje danych w
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

## Struktura i strategia wizualizacji

Dashboard prowadzi od podsumowania do szczegółów:

1. **Podsumowanie** — sekcja otwierająca dashboard. Karty metryk prezentują
   mediany grup, różnicę procentową, relację Wschód/Zachód i odniesienie do
   mediany regionów dla wybranego roku.
2. **Obserwacje i interpretacja** — tekst podsumowuje zmianę luki między
   pierwszym i ostatnim wspólnym rokiem oraz wskazuje regiony z najwyższą i
   najniższą wartością w wybranym roku. Wnioski zmieniają się wraz z filtrami;
   mają charakter opisowy i nie wyjaśniają przyczyn różnic ani nie testują ich
   istotności statystycznej.
3. **Luka Wschód–Zachód w czasie** — wykres procentowej różnicy median grup
   odpowiada bezpośrednio na pytanie, czy luka maleje; poziom 0% oznacza równe
   mediany.
4. **Poziom i zmiana w czasie** — wykres liniowy porównuje mediany PKB na
   mieszkańca (PPS) rok po roku, a karty pokazują łączną procentową zmianę median
   grupy pomiędzy pierwszym i ostatnim dostępnym rokiem w zakresie. Poziom na
   wykresie liniowym nie jest tempem wzrostu.
5. **Porównanie regionów** — poziomy wykres słupkowy porządkuje regiony według
   wartości w wybranym roku i koloruje je według grupy. Dłuższy słupek oznacza
   wyższy PKB na mieszkańca w PPS.
6. **Heatmapa region × rok** — jedna mapa pokazuje poziom PKB na mieszkańca
   w PPS dla wybranych regionów i lat. Wąski pasek przy wierszu oznacza grupę:
   czerwony to Wschód, niebieski to Zachód. Skala niebieskiego w głównej części
   mapy służy wyłącznie do porównywania wartości PKB; ciemniejszy kolor oznacza
   wyższą wartość, a puste pole brak danych. Dokładna wartość, region i rok są
   widoczne po najechaniu na komórkę. Etykiety liczbowe nie są wyświetlane
   bezpośrednio, a delikatne odstępy rozdzielają komórki. Regiony są sortowane
   malejąco według PKB w pierwszym dostępnym roku wybranego zakresu. Wykres
   słupkowy sortuje regiony według PKB w wybranym roku, więc kolejność może się
   różnić, gdy wybrany rok nie jest pierwszym rokiem zakresu.

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

W razie błędu połączenia z Eurostatem, odpowiedzi API lub nieprawidłowego
formatu danych aplikacja wyświetla komunikat i zatrzymuje renderowanie, zamiast
pokazywać niekompletny dashboard.
