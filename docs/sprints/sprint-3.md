# Sprint 3: UX/UI Polish & Professionalism

Duration: 1 week  
Goal: Enhance user experience, modernise visual design, and streamline export workflow based on stakeholder feedback.

---

## Sprint Deliverables

1. **Professional navigation** – Sidebar page grouping with icons via `config.toml`
2. **Modernised health score display** – Replace gauge with contemporary radial/card design
3. **Refined loading states** – Custom, branded spinner; replace default Streamlit animations
4. **Intuitive export workflow** – User selects format first, then generates report; single comprehensive file
5. **Consistent feedback mechanisms** – Success/error toasts for async actions
6. **Updated documentation** – README and inline comments reflecting new features

---

## Week 1: Polishing & Redesign

### Day 1: Navigation & Configuration

1. **Create/update `.streamlit/config.toml`**
   - Define `[pages]` section with logical groups:
     - `Monitoring` – Home, VM Health
     - `Reports` – Comparison, Export (if separate)
     - `Administration` – Settings (future)
   - Assign page icons (e.g., `:material/home:`, `:material/health_and_safety:`, `:material/compare_arrows:`)
   - Ensure active page is highlighted

2. **Apply sidebar headers**
   - Add group titles above each page set
   - Test on both light/dark themes

3. **Refactor page file names** (if needed) to match desired order

**Checkpoint:** Sidebar shows organised, icon‑rich navigation; no broken links.

---

### Day 2: Custom Loading Indicator & Feedback

1. **Replace default spinners**
   - Create reusable `components/loader.py` with custom CSS animation (simple pulse or bar)
   - Use `st.spinner` with plain text only, or implement a context manager that injects custom HTML
   - Apply consistently across all async API calls

2. **Implement toast notifications**
   - Use `st.toast` for success messages (“Report generated successfully”)
   - Use `st.error`/`st.warning` for failures, paired with clear guidance

3. **Remove all emoji‑heavy button labels**
   - Standardise to plain text (e.g., “Refresh”, “Export Report”, “Generate”)

**Checkpoint:** All API calls show a professional, branded loading indicator; actions trigger informative toasts.

---

### Day 3: Health Score Redesign – Concept & Implementation

1. **Design new health score widget**
   - Replace Plotly gauge with:
     - **Radial progress component** (custom SVG / st.metric with circular progress)
     - **Colour‑coded card** displaying score and status as a large number with semantic badge
   - Use `st.columns` and custom CSS for a modern card layout

2. **Redesign component scores**
   - Move from stacked progress bars to **horizontal metric cards**
   - Each card shows component name, weight (e.g., 40%), score value, and a small sparkline or icon
   - Use `st.metric` with optional delta (e.g., change from previous period)

3. **Add status badge**
   - Replace plain text status with a styled `<span>` using background colour, rounded corners, and appropriate contrast

**Checkpoint:** Health section is visually refreshed, retains full functionality, and is responsive.

---

### Day 4: Export Workflow – User‑First Choice

1. **Remove top‑level “Export Report” button**

2. **Create dedicated export section**
   - Located **below the CPU chart** (or in sidebar as secondary)
   - Contains:
     - **Format selector** – Radio or dropdown (CSV / JSON)
     - **“Generate Report” button** – Triggers download immediately

3. **Single comprehensive file**
   - CSV: Structured with clear sections (HEADER, HEALTH SUMMARY, ANOMALY DETAILS, CPU STATISTICS, DETAILED METRICS)
   - JSON: Nested object with all health data + metrics array
   - Filename: `{vm_id}_report_{timestamp}.{csv|json}`

4. **Remove intermediate “Export Options” display**
   - No tabs; direct download after format selection

**Checkpoint:** Export is intuitive, fast, and produces a complete snapshot in one click.

---

### Day 5: Integration & Cross‑VM Consistency

1. **Apply health score redesign to Comparison page** (if exists)
   - Ensure consistent component usage across pages

2. **Update all API client methods**
   - Add `@st.cache_data` TTL and clear on refresh
   - Implement retry logic with exponential backoff for robustness

3. **Polish responsive behaviour**
   - Test on tablet/mobile viewports; adjust column widths and font sizes

**Checkpoint:** All pages use the new components; no visual regressions.

---

### Day 6: Testing & Edge Cases

1. **Test with all 20 VMs**
   - Verify health scores, anomaly detection, and exports

2. **Simulate error scenarios**
   - API down → show friendly error + retry button
   - No data for selected time range → informative message
   - Export during API failure → graceful cancellation

3. **Performance profiling**
   - Measure dashboard load time with/without caching
   - Optimise Plotly chart memory usage (limit points)

**Checkpoint:** Dashboard remains stable under various failure modes.

---

### Day 7: Documentation & Demo Preparation

1. **Update README.md**
   - New navigation structure
   - Export feature description
   - Screenshots of redesigned components

2. **Add inline code comments** for new components and complex logic

3. **Create demo script**
   - Highlight before/after of health score and export
   - Record short (2‑3 min) video walkthrough

4. **Prepare presentation deck** for sprint review

**Checkpoint:** Ready for stakeholder demo.

---

## Technical Implementation

### Folder / File Modifications

```
frontend/dashboard/
├── .streamlit/
│   └── config.toml                 # NEW – page groups & icons
├── app.py
├── pages/
│   ├── 1_Home.py                  # Renamed if needed
│   └── 2_VM_Health.py            # Updated export & health widget
├── components/
│   ├── charts.py                 # (unchanged)
│   ├── health_widget.py          # NEW – radial progress + component cards
│   ├── loader.py                 # NEW – custom spinner
│   └── api_client.py             # Updated with retry + caching
├── utils/
│   ├── export.py                 # NEW – CSV/JSON report generation
│   └── helpers.py                # Add status badge helper
├── assets/
│   └── custom.css               # Enhanced styling for new components
└── requirements.txt
```

### Key Dependencies (additions)

```
streamlit>=1.28.0
plotly>=5.18.0
pandas>=2.1.0
tenacity>=8.2.0                # For retry logic
```

### Custom Loader Example

```python
# components/loader.py
import streamlit as st

def custom_spinner(text="Loading..."):
    css = """
    <style>
        .custom-loader {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #3498db;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-right: 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    return st.spinner(f'<span class="custom-loader"></span> {text}', unsafe_allow_html=True)
```

### Export Utility (Simplified)

```python
# utils/export.py
import pandas as pd
import json
from io import StringIO
from datetime import datetime

def generate_csv_report(vm_data, metrics_list):
    buffer = StringIO()
    # ... structured sections ...
    return buffer.getvalue()

def generate_json_report(vm_data, metrics_list):
    return json.dumps(export_structure, indent=2, default=str)
```

---

## Page Specifications (Updated)

### VM Health Page – New Export Section

```
## CPU Metrics Analysis
[time range selector]
[CPU chart]
[statistics row]

---
### Export Report
**Format:** (•) CSV   ( ) JSON
[Generate Report]
*Report includes health summary, anomaly details, CPU stats, and all raw metrics.*
```

### Health Score Widget (New)

```
┌─────────────────────────────────┐
│  Health Score        ● Good     │
│  ┌─────────────┐                │
│  │    87       │  Radial or    │
│  │            │  card design   │
│  └─────────────┘                │
├─────────────────────────────────┤
│ Component Scores               │
│ ┌───────────────────────────┐  │
│ │ Anomaly (40%)    92/100  ▲│  │
│ └───────────────────────────┘  │
│ ┌───────────────────────────┐  │
│ │ Stability (30%)   78/100  ▼│  │
│ └───────────────────────────┘  │
│ ┌───────────────────────────┐  │
│ │ Historical (30%)  84/100  ▲│  │
│ └───────────────────────────┘  │
└─────────────────────────────────┘
```

---

## Success Criteria

**Must Have:**

1. Sidebar pages grouped with icons, no navigation confusion
2. Health score display is modern, readable, and colour‑coded
3. Export allows format selection before generation
4. All async operations use a consistent, non‑default loading indicator
5. Export file contains **all** relevant data in one document
6. Dashboard passes testing on all 20 VMs

**Nice to Have:**

1. Delta indicators on component scores (change over last hour)
2. Option to schedule auto‑export (future sprint)
3. Dark mode optimisation for new components

---

## Risks & Mitigation

| Risk                                     | Mitigation                                           |
| ---------------------------------------- | ---------------------------------------------------- |
| Custom CSS may conflict with Streamlit   | Use unique class names; test in both light/dark mode |
| Radial progress component not accessible | Fallback to simple metric card with colour coding    |
| Export generation slows UI               | Perform file creation in separate thread / callback  |
| Users accustomed to old export location  | Add tooltip or brief announcement banner for 1 week  |

---

## Commands Reference

```bash
# Run dashboard with custom config
streamlit run app.py --theme.base="dark"  # test both themes

# Clear cache manually
streamlit cache clear

# Generate sample export for validation
python -c "from utils.export import generate_csv_report; ..."
```

---

## Definition of Done

- [ ] All code reviewed and merged into `main` branch
- [ ] No console errors or warnings
- [ ] Responsive on 1280px, 768px, and 375px viewports
- [ ] Export files verified with sample data
- [ ] README updated with new features and screenshots
- [ ] Demo video recorded and shared

---
