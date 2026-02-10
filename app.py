import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
from pathlib import Path
import calendar
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Optional

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Warsztat Ziołolek PRO", 
    page_icon="🏭", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- KLASY DANYCH (BACKEND) ---

class MaintenanceSystem:
    def __init__(self, data_dir: str = "warsztat_data"):
        self.data_dir = Path(data_dir)
        self.db_file = self.data_dir / "database.json"
        self.history_file = self.data_dir / "history.json"
        self.backup_dir = self.data_dir / "backups"
        self._ensure_directories()
        
    def _ensure_directories(self):
        self.data_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)

    def load_data(self) -> Dict:
        if not self.db_file.exists(): return self._get_initial_data()
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return self._migrate_data(json.load(f))
        except: return self._get_initial_data()

    def save_data(self, data: Dict) -> bool:
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            st.error(f"Błąd zapisu: {e}"); return False

    def load_history(self) -> List[Dict]:
        if not self.history_file.exists(): return []
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f: return json.load(f)
        except: return []

    def log_event(self, machine_name: str, action: str):
        history = self.load_history()
        history.insert(0, {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "machine": machine_name, "action": action
        })
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history[:500], f, indent=2, ensure_ascii=False)
        if 'history' in st.session_state: st.session_state.history = history

    def create_backup(self):
        if not self.db_file.exists(): return False
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            with open(self.db_file, 'r', encoding='utf-8') as src: content = src.read()
            with open(self.backup_dir / f"backup_{ts}.json", 'w', encoding='utf-8') as dst: dst.write(content)
            return True
        except: return False

    def _get_initial_data(self) -> Dict: return {"machines": []}

    def _migrate_data(self, data: Dict) -> Dict:
        # Prosta migracja struktur danych
        for m in data.get('machines', []):
            if 'daily_cycles' not in m: m['daily_cycles'] = {}
            if 'documents' not in m: m['documents'] = []
            if 'avg_daily_cycles' not in m: m['avg_daily_cycles'] = 0
            # Przelicz średnią jeśli jest 0 a są dane
            if m['avg_daily_cycles'] == 0 and m['daily_cycles']:
                cycles = list(m['daily_cycles'].values())
                m['avg_daily_cycles'] = sum(cycles) / len(cycles) if cycles else 0
        return data

class Logic:
    @staticmethod
    def get_status(interval: Dict) -> int:
        """0=OK, 1=Warning, 2=Critical"""
        if not interval.get('enabled', True): return 0
        if interval['type'] == 'cycles':
            rem = interval['interval'] - interval['current_value']
            if rem <= 0: return 2
            elif rem <= interval['interval'] * 0.15: return 1
        else:
            last = datetime.strptime(interval['last_service'], "%Y-%m-%d").date()
            next_d = last + relativedelta(months=interval['interval'])
            days = (next_d - datetime.now().date()).days
            if days <= 0: return 2
            elif days <= 14: return 1
        return 0

    @staticmethod
    def get_progress(interval: Dict) -> float:
        if not interval.get('enabled', True): return 0.0
        if interval['type'] == 'cycles':
            return min(interval['current_value'] / interval['interval'], 1.0) if interval['interval'] > 0 else 0
        else:
            last = datetime.strptime(interval['last_service'], "%Y-%m-%d").date()
            next_d = last + relativedelta(months=interval['interval'])
            total = (next_d - last).days
            elapsed = (datetime.now().date() - last).days
            return min(elapsed / total, 1.0) if total > 0 else 0

    @staticmethod
    def predict_service_date(interval: Dict, avg_daily: float) -> Optional[str]:
        """Oblicza przewidywaną datę serwisu dla cykli"""
        if interval['type'] != 'cycles' or avg_daily <= 0: return None
        remaining = interval['interval'] - interval['current_value']
        if remaining <= 0: return "Dzisiaj"
        days_left = int(remaining / avg_daily)
        pred_date = datetime.now().date() + timedelta(days=days_left)
        return f"{pred_date.strftime('%d.%m.%Y')} (za ~{days_left} dni)"

# --- STYLE CSS (DARK MODE PROFESSIONAL) ---
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .stApp { font-family: 'Inter', sans-serif; background: #0e1117; }
    
    /* Custom Headers */
    h1, h2, h3 { color: #f0f2f6 !important; }
    
    /* Metrics */
    div[data-testid="stMetric"] {
        background: #1a1c24; border: 1px solid #2d3748;
        border-radius: 8px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Progress Bars - Custom Colors via Streamlit internal classes hack is hard, 
       so we rely on native logic but styled container */
    
    /* Cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #1a1c24; border: 1px solid #2d3748; border-radius: 8px;
    }
    
    /* Status Badges */
    .badge { padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 0.85em; text-transform: uppercase; }
    .badge-ok { background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid #22c55e; }
    .badge-warn { background: rgba(251, 191, 36, 0.2); color: #fbbf24; border: 1px solid #f59e0b; }
    .badge-crit { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #dc2626; }
    
    /* Heatmap styling */
    .heatmap-cell {
        width: 100%; height: 40px; border-radius: 4px; display: flex; 
        align-items: center; justify-content: center; font-size: 0.9em;
        border: 1px solid #333; transition: 0.2s;
    }
    .heatmap-cell:hover { border-color: #fff; transform: scale(1.05); }
    </style>
    """, unsafe_allow_html=True)

# --- GŁÓWNA APLIKACJA ---

def main():
    sys = MaintenanceSystem()
    load_css()
    
    # Session State Init
    if 'data' not in st.session_state: st.session_state.data = sys.load_data()
    if 'history' not in st.session_state: st.session_state.history = sys.load_history()
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.title("🏭 Ziołolek PRO")
        st.caption("Maintenance Management v3.0")
        
        view = st.radio("MENU", 
            ["📊 Dashboard", "🔧 Karta Maszyny", "⚙️ Konfiguracja & Edycja", "📄 Dokumenty"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Szybka statystyka w sidebarze (EXTRA: Wykres kołowy statusów)
        status_counts = {"OK": 0, "Warning": 0, "Critical": 0}
        for m in st.session_state.data['machines']:
            m_stat = 0
            for i in m.get('service_intervals', []):
                m_stat = max(m_stat, Logic.get_status(i))
            if m_stat == 0: status_counts["OK"] += 1
            elif m_stat == 1: status_counts["Warning"] += 1
            else: status_counts["Critical"] += 1
            
        if sum(status_counts.values()) > 0:
            df_status = pd.DataFrame([
                {"Status": "OK", "Count": status_counts["OK"]},
                {"Status": "Ostrzeżenie", "Count": status_counts["Warning"]},
                {"Status": "Krytyczne", "Count": status_counts["Critical"]}
            ])
            fig_pie = px.pie(df_status, values='Count', names='Status', 
                             color='Status',
                             color_discrete_map={"OK":"#22c55e", "Ostrzeżenie":"#f59e0b", "Krytyczne":"#ef4444"},
                             hole=0.4)
            fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=150, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        st.divider()
        if st.button("💾 Zapisz Stan Systemu", use_container_width=True, type="primary"):
            if sys.save_data(st.session_state.data): st.success("Zapisano!")
        if st.button("📦 Utwórz Kopię Zapasową", use_container_width=True):
            if sys.create_backup(): st.success("Backup OK!")

    # --- WIDOK: DASHBOARD ---
    if view == "📊 Dashboard":
        st.title("Panel Zarządzania")
        
        # KPI Row
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Wszystkie Maszyny", sum(status_counts.values()))
        kpi2.metric("Wymaga Serwisu", status_counts["Critical"], delta_color="inverse")
        kpi3.metric("Blisko Terminu", status_counts["Warning"], delta_color="off")
        
        # EXTRA: Obliczanie całkowitej liczby cykli w systemie
        total_cycles = sum(sum(m.get('daily_cycles', {}).values()) for m in st.session_state.data['machines'])
        kpi4.metric("Wykonane Cykle", f"{total_cycles:,}".replace(",", " "))
        
        st.divider()
        
        # Lista maszyn z paskami postępu
        st.subheader("Status Floty")
        
        if not st.session_state.data['machines']:
            st.info("Brak maszyn. Przejdź do Konfiguracji.")
        
        cols = st.columns(2)
        for idx, m in enumerate(st.session_state.data['machines']):
            # Oblicz ogólny status maszyny
            m_max_status = 0
            for i in m.get('service_intervals', []):
                m_max_status = max(m_max_status, Logic.get_status(i))
            
            badge_cls = ["badge-ok", "badge-warn", "badge-crit"][m_max_status]
            badge_txt = ["SPRAWNA", "UWAGA", "SERWIS!"][m_max_status]
            border_col = "red" if m_max_status == 2 else "orange" if m_max_status == 1 else "grey"
            
            with cols[idx % 2]:
                with st.expander(f"**{m['name']}** |  {m['location']}", expanded=(m_max_status > 0)):
                    st.markdown(f"<span class='badge {badge_cls}'>{badge_txt}</span>", unsafe_allow_html=True)
                    st.write("")
                    
                    # Tabela interwałów z paskami
                    for i in m.get('service_intervals', []):
                        if i.get('enabled', True):
                            prog = Logic.get_progress(i)
                            stat = Logic.get_status(i)
                            color_emoji = "🔴" if stat==2 else "🟡" if stat==1 else "🟢"
                            
                            c1, c2 = st.columns([3, 1])
                            c1.caption(f"{color_emoji} **{i['name']}**")
                            
                            if i['type'] == 'cycles':
                                val_text = f"{i['current_value']} / {i['interval']}"
                                # EXTRA: Predykcja
                                pred = Logic.predict_service_date(i, m.get('avg_daily_cycles', 0))
                                if pred: c2.caption(f"📅 {pred}")
                            else:
                                val_text = f"Ost: {i['last_service']}"
                                # Obliczanie następnej daty
                                last = datetime.strptime(i['last_service'], "%Y-%m-%d").date()
                                next_d = last + relativedelta(months=i['interval'])
                                c2.caption(f"📅 {next_d.strftime('%d.%m.%Y')}")

                            st.progress(prog, text=val_text)
                    
                    if st.button("Przejdź do karty", key=f"btn_goto_{idx}"):
                        st.session_state.goto_machine = m['id']
                        st.info("Przełącz widok na 'Karta Maszyny'")

    # --- WIDOK: KARTA MASZYNY ---
    elif view == "🔧 Karta Maszyny":
        st.title("Centrum Operacyjne")
        
        machines = st.session_state.data['machines']
        if not machines: st.warning("Brak maszyn."); st.stop()
        
        # Wybór maszyny
        opts = {f"[{m['location']}] {m['name']}": idx for idx, m in enumerate(machines)}
        sel_idx = st.selectbox("Wybierz maszynę:", list(opts.keys()), key="sel_machine_card")
        machine = machines[opts[sel_idx]]
        
        col_main, col_cal = st.columns([1, 2])
        
        with col_main:
            st.subheader("🛠️ Serwis i Operacje")
            
            with st.container(border=True):
                st.markdown("#### 1. Rejestracja Pracy")
                col_inp1, col_inp2 = st.columns(2)
                d_input = col_inp1.date_input("Data", datetime.now())
                c_input = col_inp2.number_input("Cykle", min_value=1, value=100)
                
                if st.button("➕ Dodaj przebieg", use_container_width=True, type="primary"):
                    d_str = str(d_input)
                    machine['daily_cycles'][d_str] = machine['daily_cycles'].get(d_str, 0) + c_input
                    # Aktualizacja średniej
                    cycles_hist = list(machine['daily_cycles'].values())
                    machine['avg_daily_cycles'] = sum(cycles_hist) / len(cycles_hist)
                    # Aktualizacja liczników
                    for i in machine['service_intervals']:
                        if i['type'] == 'cycles' and i.get('enabled'):
                            i['current_value'] += c_input
                    sys.save_data(st.session_state.data)
                    sys.log_event(machine['name'], f"Dodano {c_input} cykli")
                    st.success("Zapisano!")
                    st.rerun()

            st.write("")
            
            with st.container(border=True):
                st.markdown("#### 2. Zarządzanie Interwałami")
                st.info("Tutaj możesz zresetować interwał lub zmienić datę ostatniego przeglądu.")
                
                for i in machine['service_intervals']:
                    with st.expander(f"{i['name']} ({i['type']})"):
                        c_a, c_b = st.columns(2)
                        
                        # Edycja i Reset
                        if i['type'] == 'cycles':
                            curr = c_a.number_input(f"Stan licznika", value=i['current_value'], key=f"cnt_{machine['id']}_{i['name']}")
                            if curr != i['current_value']:
                                i['current_value'] = curr
                                sys.save_data(st.session_state.data) # Auto-save przy zmianie
                                
                            if c_b.button("Zeruj licznik", key=f"rst_c_{machine['id']}_{i['name']}"):
                                i['current_value'] = 0
                                sys.save_data(st.session_state.data)
                                sys.log_event(machine['name'], f"Reset: {i['name']}")
                                st.rerun()
                        else:
                            # TO CZEGO BRAKOWAŁO: Edycja daty ostatniego serwisu
                            last_date_obj = datetime.strptime(i['last_service'], "%Y-%m-%d").date()
                            new_date = c_a.date_input("Ostatni serwis", last_date_obj, key=f"date_{machine['id']}_{i['name']}")
                            
                            if str(new_date) != i['last_service']:
                                i['last_service'] = str(new_date)
                                sys.save_data(st.session_state.data)
                                st.toast("Zaktualizowano datę!")
                                
                            if c_b.button("Potwierdź Przegląd (Dziś)", key=f"rst_t_{machine['id']}_{i['name']}"):
                                i['last_service'] = str(datetime.now().date())
                                sys.save_data(st.session_state.data)
                                sys.log_event(machine['name'], f"Wykonano przegląd: {i['name']}")
                                st.rerun()

        with col_cal:
            st.subheader("📅 Kalendarz i Analityka")
            
            # EXTRA: Wykres przebiegu dziennego (Bar Chart)
            daily_data = machine.get('daily_cycles', {})
            if daily_data:
                # Sortowanie i ograniczenie do 30 dni
                sorted_dates = sorted(daily_data.keys(), reverse=True)[:30]
                df_chart = pd.DataFrame({
                    "Data": sorted_dates,
                    "Cykle": [daily_data[d] for d in sorted_dates]
                }).sort_values("Data")
                
                fig = px.bar(df_chart, x="Data", y="Cykle", title="Dzienne obciążenie (Ostatnie 30 dni)",
                             color="Cykle", color_continuous_scale="bluyl")
                fig.update_layout(height=250, margin=dict(l=0,r=0,t=30,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Brak danych historycznych do wyświetlenia wykresu.")

            # Heatmapa (uproszczona wizualnie)
            curr_y = datetime.now().year
            curr_m = datetime.now().month
            cal = calendar.monthcalendar(curr_y, curr_m)
            
            st.write(f"**{calendar.month_name[curr_m]} {curr_y}**")
            cols = st.columns(7)
            days_head = ['Pn','Wt','Śr','Cz','Pt','So','Nd']
            for idx, d in enumerate(days_head): cols[idx].caption(d)
            
            for week in cal:
                cols = st.columns(7)
                for idx, day in enumerate(week):
                    if day == 0: 
                        cols[idx].write("")
                        continue
                    
                    d_str = f"{curr_y}-{curr_m:02d}-{day:02d}"
                    cyc = machine['daily_cycles'].get(d_str, 0)
                    
                    bg = "#1a1c24"
                    if cyc > 0: bg = "#1e3a8a" if cyc < 100 else "#1d4ed8" if cyc < 500 else "#2563eb"
                    border = "1px solid #fbbf24" if d_str == str(datetime.now().date()) else "1px solid #333"
                    
                    cols[idx].markdown(f"""
                    <div style="background:{bg}; height:40px; border-radius:4px; border:{border}; 
                    display:flex; align-items:center; justify-content:center; font-size:0.8em;" title="Cykle: {cyc}">
                        {day}
                    </div>
                    """, unsafe_allow_html=True)

    # --- WIDOK: KONFIGURACJA (PEŁNA EDYCJA) ---
    elif view == "⚙️ Konfiguracja & Edycja":
        st.title("Panel Administracyjny")
        
        tab1, tab2 = st.tabs(["🏭 Zarządzanie Maszynami", "➕ Dodaj Nową"])
        
        with tab1:
            st.info("💡 Rozwiń maszynę, aby edytować jej nazwę, model lub interwały.")
            
            for idx, m in enumerate(st.session_state.data['machines']):
                with st.expander(f"EDYCJA: {m['name']} ({m['model']})"):
                    # Edycja danych podstawowych
                    c1, c2, c3 = st.columns(3)
                    new_name = c1.text_input("Nazwa", m['name'], key=f"ed_n_{idx}")
                    new_loc = c2.text_input("Lokalizacja", m['location'], key=f"ed_l_{idx}")
                    new_mod = c3.text_input("Model", m['model'], key=f"ed_m_{idx}")
                    
                    if new_name != m['name'] or new_loc != m['location'] or new_mod != m['model']:
                        m['name'] = new_name
                        m['location'] = new_loc
                        m['model'] = new_mod
                        sys.save_data(st.session_state.data)
                        st.toast("Zapisano zmiany w nagłówku!")

                    st.markdown("---")
                    st.markdown("**Interwały Serwisowe:**")
                    
                    # Tabela interwałów do edycji
                    if not m['service_intervals']: st.caption("Brak zdefiniowanych interwałów.")
                    
                    intervals_to_remove = []
                    for i_idx, interval in enumerate(m['service_intervals']):
                        col_a, col_b, col_c, col_d = st.columns([3, 2, 2, 1])
                        
                        # Edycja nazwy interwału
                        int_name = col_a.text_input("Nazwa czynności", interval['name'], key=f"int_n_{idx}_{i_idx}")
                        if int_name != interval['name']:
                            interval['name'] = int_name
                            sys.save_data(st.session_state.data)
                        
                        # Edycja limitu
                        if interval['type'] == 'cycles':
                            int_limit = col_b.number_input("Limit (cykle)", value=interval['interval'], key=f"int_l_{idx}_{i_idx}")
                        else:
                            int_limit = col_b.number_input("Limit (miesiące)", value=interval['interval'], key=f"int_l_{idx}_{i_idx}")
                            
                        if int_limit != interval['interval']:
                            interval['interval'] = int_limit
                            sys.save_data(st.session_state.data)
                        
                        # Przełącznik aktywności
                        is_active = col_c.checkbox("Aktywny", value=interval.get('enabled', True), key=f"int_e_{idx}_{i_idx}")
                        if is_active != interval.get('enabled', True):
                            interval['enabled'] = is_active
                            sys.save_data(st.session_state.data)
                            
                        # Usuwanie
                        if col_d.button("🗑️", key=f"del_int_{idx}_{i_idx}"):
                            intervals_to_remove.append(i_idx)
                    
                    # Aplikacja usuwania
                    if intervals_to_remove:
                        for i_rem in sorted(intervals_to_remove, reverse=True):
                            del m['service_intervals'][i_rem]
                        sys.save_data(st.session_state.data)
                        st.rerun()
                        
                    st.markdown("---")
                    
                    # Dodawanie nowego interwału do tej maszyny
                    with st.form(key=f"add_int_form_{idx}"):
                        c_new1, c_new2, c_new3 = st.columns([3, 2, 2])
                        n_i_name = c_new1.text_input("Nowa czynność")
                        n_i_type = c_new2.selectbox("Typ", ["cycles", "time"])
                        n_i_val = c_new3.number_input("Wartość", min_value=1, value=100)
                        if st.form_submit_button("➕ Dodaj Interwał"):
                            m['service_intervals'].append({
                                "name": n_i_name, "type": n_i_type, "interval": n_i_val,
                                "current_value": 0, "last_service": str(datetime.now().date()), "enabled": True
                            })
                            sys.save_data(st.session_state.data)
                            st.rerun()

                    # Usuwanie maszyny
                    if st.button("❌ Usuń Maszynę Całkowicie", key=f"del_mach_{idx}"):
                        st.session_state.data['machines'].pop(idx)
                        sys.save_data(st.session_state.data)
                        st.rerun()

        with tab2:
            st.subheader("Kreator Nowej Maszyny")
            with st.form("create_machine"):
                new_m_name = st.text_input("Nazwa Maszyny")
                new_m_loc = st.text_input("Lokalizacja (Hala/Linia)")
                new_m_model = st.text_input("Model/Numer Seryjny")
                
                if st.form_submit_button("Utwórz Maszynę"):
                    new_id = f"M{len(st.session_state.data['machines'])+1:04d}"
                    st.session_state.data['machines'].append({
                        "id": new_id,
                        "name": new_m_name,
                        "location": new_m_loc,
                        "model": new_m_model,
                        "daily_cycles": {},
                        "avg_daily_cycles": 0,
                        "service_intervals": [],
                        "documents": []
                    })
                    sys.save_data(st.session_state.data)
                    st.success("Maszyna dodana!")
                    st.rerun()

    # --- WIDOK: DOKUMENTACJA (Uproszczona) ---
    elif view == "📄 Dokumenty":
        st.title("Repozytorium Plików")
        st.caption("Symulacja systemu plików")
        
        machines = st.session_state.data['machines']
        if machines:
            sel_m = st.selectbox("Maszyna", [m['name'] for m in machines])
            curr_m = next(m for m in machines if m['name'] == sel_m)
            
            up_file = st.file_uploader("Wgraj dokumentację (PDF, JPG)")
            up_desc = st.text_input("Opis pliku")
            
            if st.button("Zapisz w rejestrze") and up_file:
                curr_m['documents'].append({
                    "filename": up_file.name,
                    "description": up_desc,
                    "date": str(datetime.now().date())
                })
                sys.save_data(st.session_state.data)
                st.success("Plik dodany do rejestru!")
            
            st.markdown("### Dostępne pliki:")
            for doc in curr_m.get('documents', []):
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"📄 **{doc['description']}**")
                    c1.caption(f"{doc['filename']} | {doc['date']}")
                    c2.button("Pobierz", key=f"dl_{doc['filename']}") # Placeholder button

if __name__ == "__main__":
    main()
