import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from pathlib import Path
import calendar
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Optional, Union
import shutil

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
        self.docs_dir = self.data_dir / "dokumentacja"
        self._ensure_directories()
        
    def _ensure_directories(self):
        self.data_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        self.docs_dir.mkdir(exist_ok=True)

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

    def log_event(self, machine_name: str, action: str, user: str = "System"):
        history = self.load_history()
        history.insert(0, {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "machine": machine_name, "action": action, "user": user
        })
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history[:1000], f, indent=2, ensure_ascii=False)
        if 'history' in st.session_state: st.session_state.history = history

    def create_backup(self):
        if not self.db_file.exists(): return False
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            shutil.copy2(self.db_file, self.backup_dir / f"backup_{ts}.json")
            # Rotacja (10 ostatnich)
            backups = sorted(self.backup_dir.glob("backup_*.json"))
            if len(backups) > 10:
                for b in backups[:-10]: b.unlink()
            return True
        except: return False
    
    def save_document(self, machine_id: str, uploaded_file) -> Optional[str]:
        """Zapisuje plik fizycznie na dysku"""
        try:
            m_dir = self.docs_dir / machine_id
            m_dir.mkdir(exist_ok=True)
            file_path = m_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            return uploaded_file.name
        except Exception as e:
            st.error(f"Błąd zapisu pliku: {e}")
            return None

    def delete_document(self, machine_id: str, filename: str):
        try:
            file_path = self.docs_dir / machine_id / filename
            if file_path.exists(): file_path.unlink()
            return True
        except: return False

    def _get_initial_data(self) -> Dict: return {"machines": []}

    def _migrate_data(self, data: Dict) -> Dict:
        for m in data.get('machines', []):
            if 'daily_cycles' not in m: m['daily_cycles'] = {}
            if 'documents' not in m: m['documents'] = []
            if 'avg_daily_cycles' not in m: m['avg_daily_cycles'] = 0
            if m['avg_daily_cycles'] == 0 and m['daily_cycles']:
                 vals = list(m['daily_cycles'].values())
                 m['avg_daily_cycles'] = int(sum(vals) / len(vals))
        return data

class MaintenanceLogic:
    @staticmethod
    def is_weekend(date_obj):
        return date_obj.weekday() >= 5

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
    def predict_14_days(machine: Dict) -> pd.DataFrame:
        """Generuje prognozę 14-dniową (roboczą)"""
        forecast_data = []
        current_date = datetime.now().date()
        avg_cycles = machine.get('avg_daily_cycles', 0)
        
        workdays = 0
        i = 1
        acc_cycles = 0
        
        while workdays < 14:
            day = current_date + timedelta(days=i)
            i += 1
            if MaintenanceLogic.is_weekend(day): continue
            
            workdays += 1
            acc_cycles += avg_cycles
            
            status = "OK"
            events = []
            
            for interval in machine.get('service_intervals', []):
                if not interval.get('enabled', True): continue
                
                # Check Cycles
                if interval['type'] == 'cycles':
                    predicted_val = interval['current_value'] + acc_cycles
                    if predicted_val >= interval['interval']:
                        events.append(f"🔴 {interval['name']}")
                        status = "SERWIS"
                
                # Check Time
                elif interval['type'] == 'time':
                    last = datetime.strptime(interval['last_service'], "%Y-%m-%d").date()
                    next_d = last + relativedelta(months=interval['interval'])
                    if day >= next_d:
                         events.append(f"🕒 {interval['name']}")
                         status = "SERWIS" if status != "SERWIS" else status

            forecast_data.append({
                "Data": day.strftime("%d.%m (%a)"),
                "Status": status,
                "Zdarzenia": ", ".join(events) if events else "-"
            })
            
        return pd.DataFrame(forecast_data)

# --- CSS (High-End Dark UI) ---
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp { background-color: #0e1117; font-family: 'Inter', sans-serif; }
    
    /* Karty Maszyn */
    div[data-testid="stExpander"] {
        background-color: #1a1c24;
        border: 1px solid #2d3748;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    
    /* Metryki */
    div[data-testid="stMetric"] {
        background-color: #1a1c24;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
    }
    
    /* Badges */
    .badge { padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; }
    .badge-ok { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid #22c55e; }
    .badge-warn { background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid #eab308; }
    .badge-crit { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid #dc2626; }
    
    /* Kalendarz Heatmap */
    .heatmap-cell {
        width: 100%; height: 35px; border-radius: 4px; display: flex; 
        align-items: center; justify-content: center; font-size: 0.85em; font-weight: 600;
        transition: 0.2s; border: 1px solid #2d3748;
    }
    .heatmap-cell:hover { transform: scale(1.1); z-index: 10; border-color: white; }
    
    /* Progress Bar Hack */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #3b82f6, #60a5fa);
    }
    </style>
    """, unsafe_allow_html=True)

# --- GŁÓWNA APLIKACJA ---

def main():
    sys = MaintenanceSystem()
    load_css()
    
    if 'data' not in st.session_state: st.session_state.data = sys.load_data()
    if 'history' not in st.session_state: st.session_state.history = sys.load_history()
    
    # Sidebar
    with st.sidebar:
        st.title("🏭 Ziołolek GIGA")
        st.caption("System CMMS v4.0")
        view = st.radio("MENU", ["📊 Dashboard", "🔧 Karta Maszyny", "📄 Dokumentacja", "⚙️ Konfiguracja"], label_visibility="collapsed")
        
        st.divider()
        if st.button("💾 Zapisz System", type="primary", use_container_width=True):
            if sys.save_data(st.session_state.data): st.toast("Zapisano pomyślnie!", icon="✅")
        
        # Backup Restore (Mini)
        with st.expander("♻️ Przywracanie"):
            backups = sorted(sys.backup_dir.glob("backup_*.json"), reverse=True)
            if backups:
                b_sel = st.selectbox("Wybierz kopię", [b.name for b in backups], label_visibility="collapsed")
                if st.button("Wczytaj"):
                    with open(sys.backup_dir / b_sel, 'r', encoding='utf-8') as f:
                        st.session_state.data = sys._migrate_data(json.load(f))
                        sys.save_data(st.session_state.data)
                    st.success("Przywrócono!")
                    st.rerun()

    # --- DASHBOARD (Wizualizacja + Karty) ---
    if view == "📊 Dashboard":
        st.title("Panel Zarządzania")
        
        # KPI + Wykresy (Naprawione wizualnie)
        machines = st.session_state.data['machines']
        crit_count = sum(1 for m in machines for i in m.get('service_intervals',[]) if MaintenanceLogic.get_status(i)==2)
        warn_count = sum(1 for m in machines for i in m.get('service_intervals',[]) if MaintenanceLogic.get_status(i)==1)
        
        col_kpi, col_chart1, col_chart2 = st.columns([1, 2, 2])
        
        with col_kpi:
            st.metric("Maszyny", len(machines))
            st.metric("Krytyczne", crit_count, delta_color="inverse")
            st.metric("Ostrzeżenia", warn_count, delta_color="off")
            
        with col_chart1:
            # Status Donut Chart (Plotly)
            status_data = {"OK": 0, "Warning": 0, "Critical": 0}
            for m in machines:
                m_stat = max([MaintenanceLogic.get_status(i) for i in m.get('service_intervals',[])] or [0])
                if m_stat == 0: status_data["OK"] += 1
                elif m_stat == 1: status_data["Warning"] += 1
                else: status_data["Critical"] += 1
            
            fig_pie = px.pie(values=list(status_data.values()), names=list(status_data.keys()), hole=0.6,
                             color=list(status_data.keys()),
                             color_discrete_map={"OK":"#22c55e", "Warning":"#eab308", "Critical":"#ef4444"})
            fig_pie.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0), height=200, 
                                  paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  annotations=[dict(text=f"{len(machines)}", x=0.5, y=0.5, font_size=20, showarrow=False, font_color="white")])
            st.plotly_chart(fig_pie, use_container_width=True)
            st.caption("Stan techniczny floty")

        with col_chart2:
            # Cykle Bar Chart
            top_m = sorted(machines, key=lambda x: x.get('avg_daily_cycles', 0), reverse=True)[:5]
            if top_m:
                df_bar = pd.DataFrame({"Maszyna": [m['name'] for m in top_m], "Śr. Cykle": [m.get('avg_daily_cycles', 0) for m in top_m]})
                fig_bar = px.bar(df_bar, x="Maszyna", y="Śr. Cykle", color="Śr. Cykle", color_continuous_scale="bluyl")
                fig_bar.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=200, 
                                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                      xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#333'))
                st.plotly_chart(fig_bar, use_container_width=True)
                st.caption("Najbardziej obciążone maszyny")

        st.divider()
        st.subheader("Status Floty")
        
        # Grid Kart Maszyn (UI ze zdjęcia)
        cols = st.columns(2)
        for idx, m in enumerate(machines):
            m_stat = max([MaintenanceLogic.get_status(i) for i in m.get('service_intervals',[])] or [0])
            badge_cls = ["badge-ok", "badge-warn", "badge-crit"][m_stat]
            badge_txt = ["SPRAWNA", "UWAGA", "SERWIS!"][m_stat]
            
            with cols[idx % 2]:
                with st.expander(f"**{m['name']}** | {m['location']}", expanded=(m_stat > 0)):
                    # Header Karty
                    c_h1, c_h2 = st.columns([3, 1])
                    c_h1.caption(f"Model: {m['model']}")
                    c_h2.markdown(f"<span class='badge {badge_cls}'>{badge_txt}</span>", unsafe_allow_html=True)
                    
                    st.write("")
                    
                    # Interwały (Paski ze zdjęcia)
                    for i in m.get('service_intervals', []):
                        if not i.get('enabled', True): continue
                        stat = MaintenanceLogic.get_status(i)
                        prog = MaintenanceLogic.get_progress(i)
                        
                        icon = "🔴" if stat==2 else "🟡" if stat==1 else "🟢"
                        
                        # Wiersz nagłówka interwału
                        ci1, ci2 = st.columns([2, 1])
                        ci1.markdown(f"{icon} **{i['name']}**")
                        
                        if i['type'] == 'cycles':
                            ci2.caption(f"📅 Cykli: {i['current_value']}/{i['interval']}")
                            st.progress(prog)
                        else:
                            # Obliczanie daty
                            last = datetime.strptime(i['last_service'], "%Y-%m-%d").date()
                            next_d = last + relativedelta(months=i['interval'])
                            days_left = (next_d - datetime.now().date()).days
                            
                            ci2.caption(f"📅 {next_d} ({days_left} dni)")
                            st.progress(prog)
                    
                    if st.button("Przejdź do karty", key=f"go_{m['id']}"):
                        st.session_state.goto_id = m['id']
                        # Hack to switch tabs
                        st.info("Przełącz na zakładkę 'Karta Maszyny' w menu bocznym")

    # --- KARTA MASZYNY (Szczegóły + Prognozy) ---
    elif view == "🔧 Karta Maszyny":
        machines = st.session_state.data['machines']
        if not machines: st.warning("Brak maszyn"); st.stop()
        
        # Auto-select from Dashboard
        def_idx = 0
        if 'goto_id' in st.session_state:
            for i, m in enumerate(machines):
                if m['id'] == st.session_state.goto_id: def_idx = i; break
        
        names = [f"{m['name']} ({m['location']})" for m in machines]
        sel_name = st.selectbox("Wybierz maszynę", names, index=def_idx)
        m = machines[names.index(sel_name)]
        
        st.title(f"{m['name']}")
        
        col_op, col_anal = st.columns([1, 2])
        
        # Panel Operacyjny (Lewa)
        with col_op:
            with st.container(border=True):
                st.subheader("📝 Rejestracja")
                d_in = st.date_input("Data", datetime.now())
                c_in = st.number_input("Cykle", 1, value=100)
                if st.button("Dodaj przebieg", type="primary", use_container_width=True):
                    d_s = str(d_in)
                    m['daily_cycles'][d_s] = m['daily_cycles'].get(d_s, 0) + c_in
                    
                    # Update average
                    vals = list(m['daily_cycles'].values())
                    m['avg_daily_cycles'] = int(sum(vals)/len(vals))
                    
                    # Update intervals
                    for i in m['service_intervals']:
                        if i['type'] == 'cycles': i['current_value'] += c_in
                    
                    sys.save_data(st.session_state.data)
                    st.success("Zapisano!")
                    st.rerun()

            st.write("")
            with st.container(border=True):
                st.subheader("🛠️ Szybki Serwis")
                for i in m.get('service_intervals', []):
                    if not i.get('enabled'): continue
                    if st.button(f"Reset: {i['name']}", key=f"rst_{i['name']}"):
                        if i['type'] == 'cycles': i['current_value'] = 0
                        i['last_service'] = str(datetime.now().date())
                        sys.save_data(st.session_state.data)
                        sys.log_event(m['name'], f"Serwis: {i['name']}")
                        st.rerun()

        # Panel Analityczny (Prawa)
        with col_anal:
            tab_cal, tab_fore = st.tabs(["📅 Kalendarz", "🔮 Prognoza 14-dni"])
            
            with tab_cal:
                # Heatmapa (Better Logic)
                now = datetime.now()
                cal = calendar.monthcalendar(now.year, now.month)
                st.markdown(f"**{calendar.month_name[now.month]} {now.year}**")
                
                cols = st.columns(7)
                for d in ['Pn','Wt','Śr','Cz','Pt','So','Nd']: cols[0].write(d) # Hack header in 1st iter? No.
                
                # Render Grid
                for week in cal:
                    cc = st.columns(7)
                    for i, day in enumerate(week):
                        if day == 0: continue
                        d_str = f"{now.year}-{now.month:02d}-{day:02d}"
                        cyc = m['daily_cycles'].get(d_str, 0)
                        
                        # Color logic
                        bg = "#1a1c24"
                        if cyc > 0: bg = "#1e3a8a" if cyc < m.get('avg_daily_cycles', 100) else "#2563eb"
                        border = "2px solid #eab308" if d_str == str(now.date()) else "1px solid #333"
                        
                        cc[i].markdown(f"""
                        <div class='heatmap-cell' style='background:{bg}; border:{border}' title='{cyc} cykli'>
                            {day}<br><span style='font-size:0.6em; opacity:0.7'>{cyc if cyc>0 else ''}</span>
                        </div>
                        """, unsafe_allow_html=True)
            
            with tab_fore:
                # 14-Day Forecast Logic (From Claude)
                if m.get('avg_daily_cycles', 0) > 0:
                    df_pred = MaintenanceLogic.predict_14_days(m)
                    
                    def style_df(v):
                        return ['background-color: rgba(239, 68, 68, 0.2); color: #fca5a5' if 'SERWIS' in r['Status'] else '' for r in df_pred.to_dict('records')]

                    st.dataframe(df_pred, use_container_width=True, hide_index=True, height=400)
                else:
                    st.info("Za mało danych o cyklach, aby generować prognozę.")

    # --- DOKUMENTACJA (Pełna obsługa plików) ---
    elif view == "📄 Dokumentacja":
        st.title("Repozytorium Plików")
        machines = st.session_state.data['machines']
        
        m_sel = st.selectbox("Wybierz maszynę", [m['name'] for m in machines])
        curr_m = next(m for m in machines if m['name'] == m_sel)
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.subheader("Upload")
            up_file = st.file_uploader("Wybierz plik (PDF, JPG)")
            desc = st.text_input("Opis")
            if st.button("Wgraj", type="primary") and up_file:
                fname = sys.save_document(curr_m['id'], up_file)
                if fname:
                    curr_m['documents'].append({
                        "filename": fname, "desc": desc, "date": str(datetime.now().date())
                    })
                    sys.save_data(st.session_state.data)
                    st.success("Wgrano!")
                    st.rerun()
        
        with c2:
            st.subheader("Pliki")
            if not curr_m.get('documents'): st.info("Brak dokumentów")
            
            for idx, doc in enumerate(curr_m.get('documents', [])):
                with st.container(border=True):
                    dc1, dc2, dc3 = st.columns([3, 1, 1])
                    dc1.markdown(f"📄 **{doc['desc']}**")
                    dc1.caption(f"{doc['filename']} | {doc['date']}")
                    
                    # Download Button Logic (Reading file)
                    f_path = sys.docs_dir / curr_m['id'] / doc['filename']
                    if f_path.exists():
                        with open(f_path, "rb") as f:
                            dc2.download_button("📥", f.read(), file_name=doc['filename'], key=f"dl_{idx}")
                    else:
                        dc2.error("Brak pliku")
                        
                    if dc3.button("🗑️", key=f"del_{idx}"):
                        sys.delete_document(curr_m['id'], doc['filename'])
                        curr_m['documents'].pop(idx)
                        sys.save_data(st.session_state.data)
                        st.rerun()

    # --- KONFIGURACJA (Hasło + CRUD) ---
    elif view == "⚙️ Konfiguracja":
        st.title("Panel Administratora")
        
        if not st.session_state.get('auth', False):
            pwd = st.text_input("Hasło", type="password")
            if st.button("Zaloguj"):
                if pwd == "1111": st.session_state.auth = True; st.rerun()
                else: st.error("Złe hasło")
            st.stop()
            
        if st.button("Wyloguj"): st.session_state.auth = False; st.rerun()
        
        tab_m, tab_new = st.tabs(["Edycja Maszyn", "Nowa Maszyna"])
        
        with tab_m:
            for i, m in enumerate(st.session_state.data['machines']):
                with st.expander(f"Edycja: {m['name']}"):
                    c1, c2 = st.columns(2)
                    m['name'] = c1.text_input("Nazwa", m['name'], key=f"nm_{i}")
                    m['location'] = c2.text_input("Lokalizacja", m['location'], key=f"loc_{i}")
                    
                    st.subheader("Interwały")
                    # CRUD Interwałów
                    to_del = []
                    for j, interval in enumerate(m['service_intervals']):
                        cc1, cc2, cc3, cc4 = st.columns([2, 1, 1, 1])
                        interval['name'] = cc1.text_input("Czynność", interval['name'], key=f"in_{i}_{j}")
                        interval['interval'] = cc2.number_input("Limit", value=interval['interval'], key=f"iv_{i}_{j}")
                        interval['enabled'] = cc3.checkbox("Aktywny", interval.get('enabled', True), key=f"ie_{i}_{j}")
                        if cc4.button("🗑️", key=f"id_{i}_{j}"): to_del.append(j)
                    
                    if to_del:
                        for idx in sorted(to_del, reverse=True): del m['service_intervals'][idx]
                        st.rerun()
                        
                    # Dodaj interwał
                    with st.form(f"add_int_{i}"):
                        fn = st.text_input("Nowa czynność")
                        ft = st.selectbox("Typ", ["cycles", "time"])
                        fv = st.number_input("Wartość", 100)
                        if st.form_submit_button("Dodaj"):
                            m['service_intervals'].append({
                                "name": fn, "type": ft, "interval": fv, 
                                "current_value": 0, "last_service": str(datetime.now().date()), "enabled": True
                            })
                            st.rerun()
                            
                    st.divider()
                    if st.button("USUŃ MASZYNĘ", key=f"del_m_{i}"):
                        st.session_state.data['machines'].pop(i)
                        sys.save_data(st.session_state.data)
                        st.rerun()

        with tab_new:
            with st.form("new_m"):
                nn = st.text_input("Nazwa")
                nl = st.text_input("Lokalizacja")
                nm = st.text_input("Model")
                if st.form_submit_button("Utwórz"):
                    st.session_state.data['machines'].append({
                        "id": f"M{len(st.session_state.data['machines']):03d}",
                        "name": nn, "location": nl, "model": nm,
                        "daily_cycles": {}, "documents": [], "service_intervals": [], "avg_daily_cycles": 0
                    })
                    sys.save_data(st.session_state.data)
                    st.success("Utworzono!")
                    st.rerun()

if __name__ == "__main__":
    main()
