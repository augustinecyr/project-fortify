# Sprint 2: Streamlit Dashboard & Visualization

Duration: 1-2 weeks  
Goal: Build interactive dashboard to visualize VM health scores and metrics

---

## Sprint Deliverables

1. Streamlit application structure
2. Home page with system overview
3. VM Health page with interactive charts
4. API integration with error handling
5. Real-time data visualization
6. Responsive layout and styling

---

## Week 1: Dashboard Foundation

### Days 1-2: Streamlit Setup & Home Page

1. Create Streamlit app structure in frontend/dashboard/
2. Setup requirements.txt for dashboard dependencies
3. Create API client module for backend integration
4. Build Home page:
   - System overview (total VMs, average health)
   - Summary cards with key metrics
   - VM selector dropdown
5. Test API connectivity

Checkpoint: Home page displays real data from API

### Days 3-4: VM Health Page

1. Create VM Health page layout
2. Add health score gauge visualization
3. Display score breakdown components
4. Show CPU metrics time-series chart (last 24 hours)
5. Display anomaly indicators
6. Add refresh functionality

Checkpoint: Can view health score for any VM with charts

### Day 5: Interactivity & Polish

1. Add auto-refresh toggle
2. Implement time range selector
3. Add loading states and spinners
4. Error handling and user feedback
5. Style with custom CSS
6. Test with different VMs

Checkpoint: Dashboard is interactive and handles errors gracefully

---

## Week 2: Additional Features & Testing

### Days 6-7: Advanced Visualizations

1. Add comparison view (compare multiple VMs)
2. Create health trend chart (score over time)
3. Add anomaly highlights on time-series
4. Implement export functionality (CSV)
5. Add filters and search

Checkpoint: Can compare VMs and export data

### Days 8-9: Testing & Documentation

1. Test dashboard with all 20 VMs
2. Test edge cases (no data, API down, etc.)
3. Optimize performance (caching, lazy loading)
4. Write dashboard user guide
5. Create demo scenarios
6. Screenshot key features

Checkpoint: Dashboard is stable and documented

### Day 10: Final Polish & Demo Prep

1. Final UI/UX improvements
2. Add help text and tooltips
3. Create demo data scenarios
4. Prepare presentation slides
5. Record demo video
6. Final testing

Checkpoint: Dashboard ready for demo

---

## Technical Implementation

### Folder Structure

```
frontend/dashboard/
├── app.py                      # Main entry point
├── pages/
│   ├── 1_VM_Health.py          # Health scoring page
│   └── 2_Comparison.py         # VM comparison (optional)
├── components/
│   ├── charts.py               # Reusable chart components
│   ├── metrics.py              # Metric display widgets
│   └── api_client.py           # API integration
├── utils/
│   ├── config.py               # Configuration
│   └── helpers.py              # Helper functions
├── requirements.txt
└── Dockerfile
```

### Key Dependencies

```
streamlit>=1.28.0
requests>=2.31.0
plotly>=5.18.0
pandas>=2.1.0
```

### API Integration Pattern

```python
import streamlit as st
import requests

class FortifyAPIClient:
    def __init__(self, base_url):
        self.base_url = base_url

    @st.cache_data(ttl=300)
    def get_health_score(_self, vm_id):
        response = requests.get(f"{_self.base_url}/api/v1/health/{vm_id}")
        return response.json()
```

---

## Page Specifications

### Home Page

Components:

1. Header with app title
2. System status indicator
3. Summary metrics row:
   - Total VMs monitored
   - Average health score
   - Critical alerts count
4. VM selector (dropdown or search)
5. Quick actions (Refresh, View All)

### VM Health Page

Components:

1. VM selector in sidebar
2. Health score gauge (0-100) with color coding:
   - Green: 80-100
   - Yellow: 50-79
   - Red: 0-49
3. Score breakdown (3 horizontal bars):
   - Anomaly component
   - Stability component
   - Historical component
4. CPU metrics line chart (last 24 hours)
5. Anomaly highlights table
6. Refresh button

---

## Success Criteria

Must Have:

1. Home page displays system overview
2. Can select and view any VM's health score
3. Charts display real data from API
4. Error messages when API unavailable
5. Dashboard runs without crashes

Nice to Have:

1. Auto-refresh capability
2. Export data to CSV
3. Compare multiple VMs
4. Custom time range selection
5. Responsive design for different screen sizes

---

## Risks & Mitigation

| Risk                      | Mitigation                                      |
| ------------------------- | ----------------------------------------------- |
| API connection issues     | Add retry logic, show cached data               |
| Large dataset performance | Implement pagination, limit data points         |
| Streamlit learning curve  | Follow official docs, use simple examples first |
| Chart rendering slow      | Use Plotly for performance, limit data points   |

---

## Commands Reference

```bash
# Setup
cd frontend/dashboard
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run dashboard
streamlit run app.py

# Run with specific port
streamlit run app.py --server.port=8501

# Run with auto-reload
streamlit run app.py --server.runOnSave=true
```

---

Version: 1.0  
Last Updated: [Date]
