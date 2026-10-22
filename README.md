# 📊 Time Use Interactive Dashboard: Canada vs. Vietnam (2022)

An interactive, comparative web dashboard visualizing and analyzing 24-hour daily time use patterns across **Canada** and **Vietnam** using official 2022 national time-use surveys.

Built with **Python**, **Dash**, and **Plotly**.

---

## 🌟 Key Features

- **24-Hour Comparative Timeline**: Side-by-side synchronized area charts displaying the minute-by-minute percentage share of the population engaged in various activities from 00:00 to 23:59.
- **Demographic Breakdowns**:
  - **Overview**: Entire national populations.
  - **By Gender**: Side-by-side subplots for Male vs. Female.
  - **By Age**: Multi-panel views across age cohorts (`15–34`, `35–54`, `55–64`, `65+`).
- **Activity Isolation & Overlay Comparison**: Click any activity in the legend to isolate it. Toggle **Overlay Isolate** to view both countries on a single coordinate plane with dynamic green/red difference shading showing where each country spends more or less time.
- **Surprise Chart (Animated Top 5 Race)**: Watch the top 5 activities transition smoothly throughout the 24-hour day with interactive play/pause controls and a time slider for each country.
- **Synchronized Hover (Sync Hover)**: When enabled, hovering over one country's timeline projects a synchronized vertical crosshair on the other country's chart for instant minute-by-minute comparison.
- **Raw Data View**: Toggle between graphical visualization and data tables for exact numeric values.
- **Responsive Layout**: Designed for full-screen desktop comparison, split-screen coding in IDEs, and touch-friendly mobile devices.

---

## 📚 Standardized Activity Taxonomy (17 Categories)

The distinct classification systems from Statistics Canada and the World Bank have been harmonized into 17 standardized activities:

| Activity | Description |
| :--- | :--- |
| **Sleeping** | Nighttime sleep, naps, essential rest, and resting during illness. |
| **Work** | Main/secondary employment, farming, business, telework, overtime, and work-related duties. |
| **Eating** | Meals, snacks, and beverages at home, work, or dining establishments. |
| **Housework** | Cooking, cleaning, laundry, ironing, home repairs, and household organization. |
| **Travelling** | Commuting to/from work, school, shopping, socializing, or errands via transit, car, bike, or walking. |
| **Personal care** | Bathing, grooming, dressing, personal hygiene, and health self-care. |
| **Caring** | Childcare (feeding, homework help) and eldercare or assisting sick/disabled relatives. |
| **Education** | Attending classes/lectures, studying, homework, courses, and educational training. |
| **Sport** | Physical exercise, workouts, gym, running, cycling, swimming, and fitness activities. |
| **TV/Online videos** | Broadcast television, cable, streaming services (Netflix, YouTube), and movies. |
| **Passive leisure** | Reading books, magazines, or news; listening to podcasts/music; social media browsing. |
| **Active leisure** | Gaming, hobbies, arts, crafts, musical instruments, and social events. |
| **Outdoor activities** | Walking, hiking, gardening, spending time in nature, parks, and outdoor recreation. |
| **Sell goods / services** | Informal commerce, market sales, retail selling, street vending, and client services. |
| **Relaxing** | Meditating, quiet contemplation, daydreaming, and intentional unstructured downtime. |
| **Shopping** | Purchasing groceries, food, clothing, household goods, and online shopping. |
| **Others** | Unclassified, unspecified, or miscellaneous diary entries. |

---

## 🗂 Data Sources

1. **Canada**: 2022 Canadian Time Use Survey (Statistics Canada, PUMF).
   - Episode file: `TU_ET_2022_Episode_PUMF.sas7bdat`
   - Main demographic file: `TU_ET_2022_Main_Principal_PUMF.sas7bdat`
   - Reference: [Statistics Canada Catalog 45-25-0001](https://www150.statcan.gc.ca/n1/pub/45-25-0001/index-eng.htm#a7)
2. **Vietnam**: 2022 Vietnam Time Use Survey (World Bank Microdata Library).
   - Diary file: `4_diary_main.csv`
   - Reference: [World Bank Microdata Catalog 5844](https://microdata.worldbank.org/index.php/catalog/5844)

---

## 🚀 Quick Start

### 1. Prerequisites & Environment Setup
Clone the repository and activate the virtual environment:

```powershell
# Create virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Dashboard
```powershell
python app.py
```
The server will boot and serve on `http://127.0.0.1:8050/`.

---

## 🖥 Viewing in Google Antigravity IDE

You can view and interact with the dashboard directly inside the editor without opening an external browser:

1. Start `app.py` in the terminal.
2. Press <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd> to open the **Command Palette**.
3. Type and select **`Simple Browser: Show`**.
4. Enter `http://127.0.0.1:8050/` and press <kbd>Enter</kbd>.
5. Drag the tab to the right side of your editor to view your code and dashboard side-by-side!

---

## 🔄 Data Caching & Pipeline

For fast startup, the app loads pre-aggregated matrices from `processed_data.pkl`.

If you update the raw survey datasets in `Data sources/` or adjust the mapping logic in `data_loader.py`, regenerate the cache anytime by running:

```powershell
python data_loader.py
```
