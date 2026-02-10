import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path
import calendar
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Optional, Union

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Warsztat Ziołolek", 
    page_icon="🔧", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- KLASY DANYCH I LOGIKI BIZNESOWEJ ---

class MaintenanceSystem:
    """Klasa zarządzająca danymi i logiką systemu (Backend)"""
    
    def __init__(self, data_dir: str = "warsztat_data"):
        self.data_dir = Path(data_dir)
        self.db_file = self.data_dir / "database.json"
        self.history_file = self.data_dir / "history.json"
        self.backup_dir = self.data_dir / "backups"
        self.docs_dir = self.data_dir / "dokumentacja"
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Tworzy strukturę katalogów jeśli nie istnieje"""
        self.data_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        self.docs_dir.mkdir(exist_ok=True)

    def load_data(self) -> Dict:
        """Wczytuje bazę danych"""
        if not self.db_file.exists():
            return self._get_initial_data()
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self._migrate_data(data)
        except Exception as e:
            st.error(f"Błąd krytyczny bazy danych: {e}")
            return self._get_initial_data()

    def save_data(self, data: Dict) -> bool:
        """Zapisuje stan systemu"""
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            st.error(f"Nie udało się zapisać danych: {e}")
            return False

    def load_history(self) -> List[Dict]:
        """Wczytuje historię operacji"""
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def log_event(self, machine_name: str, action: str, user: str = "System"):
        """Dodaje wpis do historii"""
        history = self.load_history()
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "machine": machine_name,
            "action": action,
            "user": user
        }
        history.insert(0, entry)
        # Ogranicz historię do 1000 wpisów dla wydajności
        if len(history) > 1000:
            history = history[:1000]
            
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        # Aktualizuj stan sesji jeśli istnieje
        if 'history' in st.session_state:
            st.session_state.history = history

    def create_backup(self) -> bool:
        """Tworzy kopię zapasową"""
        if not self.db_file.exists():
            return False
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"database_backup_{timestamp}.json"
            
            with open(self.db_file, 'r', encoding='utf-8') as src:
                data = src.read()
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(data)
                
            # Rotacja backupów (trzymaj ostatnie 10)
            backups = sorted(self.backup_dir.glob("database_backup_*.json"))
            if len(backups) > 10:
                for old in backups[:-10]:
                    old.unlink()
            return True
        except Exception as e:
            st.error(f"Błąd backupu: {e}")
            return False

    def _get_initial_data(self) -> Dict:
        return {"machines": []}

    def _migrate_data(self, data: Dict) -> Dict:
        """Aktualizuje strukturę danych ze starszych wersji"""
        for machine in data.get('machines', []):
            if 'daily_cycles' not in machine: machine['daily_cycles'] = {}
            if 'documents' not in machine: machine['documents'] = []
            if 'avg_daily_cycles' not in machine: machine['avg_daily_cycles'] = 0
            for interval in machine.get('service_intervals', []):
                if 'enabled' not in interval: interval['enabled'] = True
        return data

class ServiceLogic:
    """Logika obliczania statusów serwisu"""
    
    @staticmethod
    def get_status(interval: Dict) -> int:
        """0=OK, 1=Warning, 2=Critical"""
        if not interval.get('enabled', True):
            return 0
            
        if interval['type'] == 'cycles':
            remaining = interval['interval'] - interval['current_value']
            if remaining <= 0: return 2
            elif remaining <= interval['interval'] * 0.15: return 1
        else:
            last = datetime.strptime(interval['last_service'], "%Y-%m-%d").date()
            next_date = last + relativedelta(months=interval['interval'])
            days = (next_date - datetime.now().date()).days
            if days <= 0: return 2
            elif days <= 7: return 1
        return 0

    @staticmethod
    def get_progress(interval: Dict) -> float:
        """Zwraca postęp 0.0 - 1.0"""
        if not interval.get('enabled', True): return 0.0
        
        if interval['type'] == 'cycles':
            if interval['interval'] == 0: return 0.0
            return min(interval['current_value'] / interval['interval'], 1.0)
        else:
            last = datetime.strptime(interval['last_service'], "%Y-%m-%d").date()
            next_date = last + relativedelta(months=interval['interval'])
            total_days = (next_date - last).days
            elapsed = (datetime.now().date() - last).days
            return min(elapsed / total_days, 1.0) if total_days > 0 else 0.0

# --- FUNKCJE UI (WIDOKI) ---

def render_heatmap(machine: Dict, year: int, month: int):
    """Generuje HTML dla kalendarza (Widok)"""
    cal = calendar.monthcalendar(year, month)
    daily_cycles = machine.get('daily_cycles', {})
    
    # Przygotowanie danych
    month_dates = [f"{year}-{month:02d}-{day:02d}" for week in cal for day in week if day != 0]
    month_cycles = [daily_cycles.get(d, 0) for d in month_dates]
    max_cycles = max(month_cycles) if month_cycles else 6
    if max_cycles == 0: max_cycles = 1
    
    # Budowanie HTML (uproszczone i zoptymalizowane)
    html_parts = [
        f"<div class='heatmap-container'>",
        f"<div class='heatmap-header'>{calendar.month_name[month]} {year}</div>",
        "<div class='heatmap-grid'>"
    ]
    
    # Nagłówki dni
    days = ['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'So', 'Nd']
    html_parts.append("<div class='heatmap-row header'>")
    for d in days: html_parts.append(f"<span>{d}</span>")
    html_parts.append("</div>")
    
    # Dni
    today_str = str(datetime.now().date())
    
    for week in cal:
        html_parts.append("<div class='heatmap-row'>")
        for day in week:
            if day == 0:
                html_parts.append("<span class='day-empty'></span>")
                continue
                
            date_str = f"{year}-{month:02d}-{day:02d}"
            cycles = daily_cycles.get(date_str, 0)
            
            # Logika klas CSS
            css_classes = ["calendar-day"]
            if date_str == today_str: css_classes.append("day-today")
            
            # Kolorowanie
            intensity = 0
            if cycles > 0:
                intensity = min(int((cycles / max_cycles) * 6) + 1, 6)
                css_classes.append(f"day-{intensity}")
            else:
                css_classes.append("day-0")
                
            if datetime(year, month, day).weekday() >= 5:
                css_classes.append("day-weekend")

            html_parts.append(f"<span class='{' '.join(css_classes)}' title='{date_str}: {cycles}'>{day}</span>")
        html_parts.append("</div>")
    
    html_parts.append("</div></div>") # Zamknięcie grid i container
    return "".join(html_parts)

def load_css():
    """Wstrzykuje style CSS"""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono&display=swap');
    
    /* Globalne */
    .stApp { background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 100%); font-family: 'Inter', sans-serif; }
    
    /* Metrics */
    div[data-testid="stMetric"] {
        background: rgba(30, 37, 50, 0.6);
        border: 1px solid #2d3748;
        border-left: 4px solid #3b82f6;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-2px); border-left-color: #60a5fa; }
    
    /* Heatmap CSS */
    .heatmap-container { background: #1a1f2e; padding: 15px; border-radius: 8px; border: 1px solid #2d3748; }
    .heatmap-header { color: #60a5fa; text-align: center; font-weight: 700; margin-bottom: 15px; text-transform: uppercase; }
    .heatmap-grid { display: flex; flex-direction: column; align-items: center; }
    .heatmap-row { display: flex; gap: 4px; margin-bottom: 4px; }
    .heatmap-row.header span { width: 35px; text-align: center; color: #9ca3af; font-size: 0.8rem; font-weight: 600; }
    
    .calendar-day {
        width: 35px; height: 35px;
        display: flex; align-items: center; justify-content: center;
        border-radius: 4px; border: 1px solid #2d3748;
        font-size: 0.9rem; font-weight: 500; cursor: default;
        transition: all 0.2s;
    }
    .calendar-day:hover { transform: scale(1.1); z-index: 2; box-shadow: 0 0 10px rgba(59, 130, 246, 0.5); }
    .day-empty { width: 35px; height: 35px; border: none; }
    
    /* Kolory heatmapy */
    .day-0 { background: #1a1f2e; color: #4b5563; }
    .day-1 { background: #1e3a5f; color: #93c5fd; }
    .day-2 { background: #2563eb; color: #fff; }
    .day-3 { background: #1d4ed8; color: #fff; }
    .day-4 { background: #1e40af; color: #fff; }
    .day-5 { background: #1e3a8a; color: #fff; }
    .day-6 { background: #dc2626; color: #fff; font-weight: 700; }
    .day-weekend { opacity: 0.6; }
    .day-today { border: 2px solid #fbbf24; }
    
    /* Status Badges */
    .status-badge { padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.8em; }
    .badge-ok { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid #22c55e; }
    .badge-warn { background: rgba(251, 191, 36, 0.15); color: #fbbf24; border: 1px solid #f59e0b; }
    .badge-crit { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid #dc2626; }
    </style>
    """, unsafe_allow_html=True)

# --- GŁÓWNA APLIKACJA ---

def main():
    # Inicjalizacja systemu
    sys = MaintenanceSystem()
    load_css()
    
    # Inicjalizacja stanu sesji
    if 'data' not in st.session_state:
        st.session_state.data = sys.load_data()
    if 'history' not in st.session_state:
        st.session_state.history = sys.load_history()
    if 'cal_date' not in st.session_state:
        st.session_state.cal_date = datetime.now()

    # --- SIDEBAR ---
    st.sidebar.title("🔧 WARSZTAT ZIOŁOLEK")
    st.sidebar.markdown("System Utrzymania Ruchu v2.0")
    st.sidebar.divider()
    
    view = st.sidebar.radio("NAWIGACJA", 
        ["🏠 Panel Główny", "🔧 Karta Maszyny", "📄 Dokumentacja", "⚙️ Konfiguracja", "📊 Historia"])
    
    # Liczniki alertów
    crit_count = 0
    warn_count = 0
    for m in st.session_state.data['machines']:
        for i in m.get('service_intervals', []):
            s = ServiceLogic.get_status(i)
            if s == 2: crit_count += 1
            elif s == 1: warn_count += 1
            
    st.sidebar.divider()
    if crit_count > 0: st.sidebar.error(f"🚨 Krytyczne: {crit_count}")
    if warn_count > 0: st.sidebar.warning(f"⚠️ Ostrzeżenia: {warn_count}")
    if crit_count == 0 and warn_count == 0: st.sidebar.success("✅ System OK")
    
    # Przycisk Backupu
    st.sidebar.divider()
    if st.sidebar.button("📦 Utwórz Backup", use_container_width=True):
        if sys.create_backup():
            st.sidebar.success("Backup OK!")

    # --- WIDOKI ---
    
    if view == "🏠 Panel Główny":
        st.title("Dashboard Utrzymania Ruchu")
        
        # Statystyki Top
        machines = st.session_state.data['machines']
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Maszyny", len(machines))
        col2.metric("Sprawne", len(machines) - crit_count - warn_count)
        col3.metric("Ostrzeżenia", warn_count)
        col4.metric("Krytyczne", crit_count)
        
        st.divider()
        
        # Lista maszyn
        cols = st.columns(2)
        for idx, m in enumerate(machines):
            with cols[idx % 2]:
                with st.container(border=True):
                    # Status maszyny
                    m_status = 0
                    for i in m.get('service_intervals', []):
                        m_status = max(m_status, ServiceLogic.get_status(i))
                    
                    status_class = ["badge-ok", "badge-warn", "badge-crit"][m_status]
                    status_text = ["OK", "UWAGA", "KRYTYCZNY"][m_status]
                    
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"### {m['name']}")
                    c2.markdown(f"<div class='status-badge {status_class}'>{status_text}</div>", unsafe_allow_html=True)
                    st.caption(f"📍 {m['location']} | {m['model']}")
                    
                    # Interwały (podgląd)
                    if m.get('service_intervals'):
                        st.markdown("---")
                        for i in m['service_intervals']:
                            if i.get('enabled', True):
                                s = ServiceLogic.get_status(i)
                                if s > 0: # Pokaż tylko jeśli problem, lub wszystkie? Pokażmy wszystkie compact
                                    col_n, col_v = st.columns([2,1])
                                    col_n.caption(f"{'🔴' if s==2 else '🟡' if s==1 else '🟢'} {i['name']}")
                                    
                                    if i['type'] == 'cycles':
                                        col_v.caption(f"{i['current_value']}/{i['interval']}")
                                    else:
                                        col_v.caption(f"{i['last_service']}")
                                    st.progress(ServiceLogic.get_progress(i))

    elif view == "🔧 Karta Maszyny":
        st.title("Karta Maszyny")
        machines = st.session_state.data['machines']
        
        if not machines:
            st.info("Brak maszyn. Przejdź do Konfiguracji.")
        else:
            opts = {f"[{m['location']}] {m['name']}": m['id'] for m in machines}
            sel_name = st.selectbox("Wybierz maszynę", list(opts.keys()))
            m = next(x for x in machines if x['id'] == opts[sel_name])
            
            c1, c2 = st.columns([1, 2])
            
            with c1: # Panel operacyjny
                st.subheader("Operacje")
                with st.container(border=True):
                    st.write("**Dodaj cykle**")
                    d = st.date_input("Data", datetime.now())
                    v = st.number_input("Ilość", 1, step=1)
                    if st.button("Zatwierdź", type="primary", use_container_width=True):
                        d_str = str(d)
                        # Aktualizacja słownika cykli dziennych
                        m['daily_cycles'][d_str] = m['daily_cycles'].get(d_str, 0) + v
                        # Aktualizacja interwałów
                        for i in m['service_intervals']:
                            if i['type'] == 'cycles' and i.get('enabled'):
                                i['current_value'] += v
                        
                        sys.save_data(st.session_state.data)
                        sys.log_event(m['name'], f"Dodano {v} cykli ({d_str})")
                        st.success("Zapisano!")
                        st.rerun()

                st.write("")
                st.subheader("Serwis")
                for i in m.get('service_intervals', []):
                    if i.get('enabled'):
                        status = ServiceLogic.get_status(i)
                        btn_type = "primary" if status == 2 else "secondary"
                        if st.button(f"🛠️ Reset: {i['name']}", key=f"rst_{m['id']}_{i['name']}", type=btn_type, use_container_width=True):
                            i['current_value'] = 0
                            i['last_service'] = str(datetime.now().date())
                            sys.save_data(st.session_state.data)
                            sys.log_event(m['name'], f"Serwis: {i['name']}")
                            st.rerun()

            with c2: # Kalendarz i detale
                st.subheader("Kalendarz Pracy")
                cur_date = st.session_state.cal_date
                
                bc1, bc2, bc3 = st.columns([1, 4, 1])
                if bc1.button("◀"): st.session_state.cal_date -= relativedelta(months=1); st.rerun()
                if bc3.button("▶"): st.session_state.cal_date += relativedelta(months=1); st.rerun()
                
                st.markdown(render_heatmap(m, cur_date.year, cur_date.month), unsafe_allow_html=True)
                
                # Szczegóły interwałów
                st.subheader("Szczegóły Interwałów")
                for i in m.get('service_intervals', []):
                    with st.expander(f"{i['name']} ({i['type']})", expanded=False):
                        if i['type'] == 'cycles':
                            st.progress(ServiceLogic.get_progress(i), text=f"Stan: {i['current_value']} / {i['interval']}")
                        else:
                            st.progress(ServiceLogic.get_progress(i), text=f"Ostatni: {i['last_service']} (Interwał: {i['interval']} msc)")

    elif view == "⚙️ Konfiguracja":
        st.title("Konfiguracja")
        
        if "auth" not in st.session_state:
            st.session_state.auth = False
            
        if not st.session_state.auth:
            pwd = st.text_input("Podaj hasło", type="password")
            if st.button("Zaloguj"):
                if pwd == "1111": st.session_state.auth = True; st.rerun()
                else: st.error("Błędne hasło")
        else:
            if st.button("Wyloguj"): st.session_state.auth = False; st.rerun()
            st.divider()
            
            tab1, tab2 = st.tabs(["Maszyny", "Interwały"])
            
            with tab1:
                # Dodawanie maszyny
                with st.form("new_machine"):
                    st.write("Nowa maszyna")
                    n_name = st.text_input("Nazwa")
                    n_loc = st.text_input("Lokalizacja")
                    n_model = st.text_input("Model")
                    if st.form_submit_button("Dodaj"):
                        new_id = f"M{len(st.session_state.data['machines'])+1:03d}"
                        st.session_state.data['machines'].append({
                            "id": new_id, "name": n_name, "location": n_loc, "model": n_model,
                            "daily_cycles": {}, "service_intervals": [], "documents": []
                        })
                        sys.save_data(st.session_state.data)
                        st.success("Dodano!")
                        st.rerun()
                
                # Usuwanie
                st.markdown("### Lista maszyn")
                for idx, m in enumerate(st.session_state.data['machines']):
                    c1, c2 = st.columns([4, 1])
                    c1.text(f"{m['name']} ({m['model']})")
                    if c2.button("Usuń", key=f"del_m_{idx}"):
                        st.session_state.data['machines'].pop(idx)
                        sys.save_data(st.session_state.data)
                        st.rerun()

            with tab2:
                # Zarządzanie interwałami
                machines = st.session_state.data['machines']
                if machines:
                    sel_m_name = st.selectbox("Wybierz maszynę do edycji", [m['name'] for m in machines])
                    sel_m = next(m for m in machines if m['name'] == sel_m_name)
                    
                    st.write(f"Interwały dla: **{sel_m['name']}**")
                    
                    with st.form("new_int"):
                        i_name = st.text_input("Nazwa czynności")
                        i_type = st.selectbox("Typ", ["cycles", "time"])
                        i_val = st.number_input("Wartość (cykle lub miesiące)", 1)
                        if st.form_submit_button("Dodaj interwał"):
                            sel_m['service_intervals'].append({
                                "name": i_name, "type": i_type, "interval": i_val,
                                "current_value": 0, "last_service": str(datetime.now().date()),
                                "enabled": True
                            })
                            sys.save_data(st.session_state.data)
                            st.success("Dodano!")
                            st.rerun()
                    
                    st.divider()
                    for idx, i in enumerate(sel_m['service_intervals']):
                        c1, c2 = st.columns([4, 1])
                        c1.text(f"{i['name']} ({i['interval']} {i['type']})")
                        if c2.button("Usuń", key=f"del_int_{sel_m['id']}_{idx}"):
                            sel_m['service_intervals'].pop(idx)
                            sys.save_data(st.session_state.data)
                            st.rerun()

    elif view == "📄 Dokumentacja":
        st.title("Dokumentacja")
        machines = st.session_state.data['machines']
        if machines:
            m_name = st.selectbox("Wybierz maszynę", [m['name'] for m in machines])
            m = next(x for x in machines if x['name'] == m_name)
            
            uploaded = st.file_uploader("Dodaj plik")
            desc = st.text_input("Opis pliku")
            if st.button("Zapisz plik") and uploaded and desc:
                # Zapis fizyczny (symulacja w prostym skrypcie)
                # W pełnej wersji tutaj byłby zapis na dysk
                m['documents'].append({
                    "filename": uploaded.name,
                    "description": desc,
                    "date": str(datetime.now().date())
                })
                sys.save_data(st.session_state.data)
                st.success("Dodano (metadata)!")
            
            st.divider()
            for doc in m.get('documents', []):
                st.info(f"📄 {doc['description']} ({doc['filename']}) - {doc['date']}")

    elif view == "📊 Historia":
        st.title("Logi Systemowe")
        hist = st.session_state.history
        if hist:
            df = pd.DataFrame(hist)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if st.button("Wyczyść historię"):
                st.session_state.history = []
                # Tu powinno być wywołanie sys.clear_history() ale dla uproszczenia
                with open(sys.history_file, 'w') as f: json.dump([], f)
                st.rerun()
        else:
            st.info("Pusto.")

if __name__ == "__main__":
    main()
