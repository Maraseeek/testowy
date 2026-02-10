import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import os
from pathlib import Path
import calendar
import base64

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Warsztat Ziołolek", 
    page_icon="🔧", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ZAAWANSOWANE STYLE CSS ---
st.markdown("""
    <style>
    /* Import profesjonalnej czcionki */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* ========== TRYB CIEMNY (DOMYŚLNY) - PROFESJONALNA PALETA ========== */
    
    /* Tło aplikacji - głęboki granat */
    .stApp {
        background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 100%);
    }
    
    /* Sidebar - panel kontrolny */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #13181f 0%, #0a0d12 100%);
        border-right: 2px solid #1e2532;
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #60a5fa !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Metryki - status indicators */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e2532 0%, #252d3f 100%);
        border: 2px solid #2d3748;
        border-left: 4px solid #3b82f6;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        transition: all 0.3s ease;
    }
    
    div[data-testid="stMetric"]:hover {
        border-left-color: #60a5fa;
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.3);
        transform: translateY(-2px);
    }
    
    div[data-testid="stMetricLabel"] {
        color: #9ca3af !important;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    div[data-testid="stMetricValue"] {
        color: #f9fafb !important;
        font-family: 'JetBrains Mono', monospace;
        font-size: 2rem !important;
        font-weight: 700;
    }
    
    /* Kontenery z ramką */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(135deg, #1a1f2e 0%, #252d3f 100%);
        border: 2px solid #2d3748;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }
    
    /* Pasek postępu - wielokolorowy system */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #3b82f6 0%, #60a5fa 100%);
        border-radius: 4px;
    }
    
    /* Przyciski - system hierarchiczny */
    .stButton > button {
        border-radius: 6px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 12px 24px !important;
        border: 2px solid transparent !important;
        transition: all 0.3s ease;
        font-size: 0.9rem !important;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        border-color: #3b82f6 !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        color: #ffffff !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%) !important;
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.6);
        transform: translateY(-2px);
    }
    
    .stButton > button[kind="secondary"] {
        background: transparent !important;
        border-color: #3b82f6 !important;
        color: #60a5fa !important;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background: rgba(59, 130, 246, 0.15) !important;
        border-color: #60a5fa !important;
    }
    
    /* Nagłówki - hierarchia wizualna */
    h1, h2, h3 {
        color: #f9fafb !important;
        font-weight: 700 !important;
    }
    
    h1 {
        font-size: 2.5rem !important;
        border-bottom: 3px solid #3b82f6;
        padding-bottom: 10px;
        margin-bottom: 30px !important;
    }
    
    h2 {
        font-size: 1.8rem !important;
        color: #60a5fa !important;
        margin-top: 20px !important;
    }
    
    h3 {
        font-size: 1.3rem !important;
        color: #93c5fd !important;
    }
    
    h4 {
        color: #9ca3af !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Tabele - profesjonalny wygląd */
    .stDataFrame {
        border: 2px solid #2d3748 !important;
        border-radius: 8px !important;
        overflow: hidden;
    }
    
    thead tr th {
        background: linear-gradient(135deg, #2d3748 0%, #374151 100%) !important;
        color: #60a5fa !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 15px !important;
        border-bottom: 2px solid #3b82f6 !important;
    }
    
    tbody tr {
        background-color: #1a1f2e !important;
        transition: all 0.2s ease;
    }
    
    tbody tr:hover {
        background-color: #252d3f !important;
        box-shadow: inset 0 0 0 2px #3b82f6;
    }
    
    tbody tr td {
        padding: 12px !important;
        color: #e5e7eb !important;
        border-bottom: 1px solid #2d3748 !important;
    }
    
    /* Alerty - system kolorystyczny */
    .stAlert {
        border-radius: 8px !important;
        border-left: 5px solid !important;
        padding: 15px 20px !important;
        font-weight: 500 !important;
    }
    
    div[data-baseweb="notification"][kind="error"] {
        background-color: rgba(239, 68, 68, 0.15) !important;
        border-left-color: #ef4444 !important;
    }
    
    div[data-baseweb="notification"][kind="warning"] {
        background-color: rgba(251, 191, 36, 0.15) !important;
        border-left-color: #fbbf24 !important;
    }
    
    div[data-baseweb="notification"][kind="success"] {
        background-color: rgba(34, 197, 94, 0.15) !important;
        border-left-color: #22c55e !important;
    }
    
    div[data-baseweb="notification"][kind="info"] {
        background-color: rgba(59, 130, 246, 0.15) !important;
        border-left-color: #3b82f6 !important;
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > div {
        background-color: #1a1f2e !important;
        border: 2px solid #2d3748 !important;
        border-radius: 6px !important;
        color: #f9fafb !important;
        padding: 10px !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
    }
    
    /* Calendar Heatmap */
    .calendar-day {
        display: inline-block;
        width: 35px;
        height: 35px;
        margin: 2px;
        border-radius: 4px;
        text-align: center;
        line-height: 35px;
        font-size: 0.9rem;
        font-weight: 600;
        border: 1px solid #2d3748;
        transition: all 0.2s ease;
    }
    
    .calendar-day:hover {
        transform: scale(1.1);
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
    }
    
    .day-0 { background-color: #1a1f2e; color: #4b5563; }
    .day-1 { background-color: #1e3a5f; color: #93c5fd; }
    .day-2 { background-color: #2563eb; color: #ffffff; }
    .day-3 { background-color: #1d4ed8; color: #ffffff; }
    .day-4 { background-color: #1e40af; color: #ffffff; }
    .day-5 { background-color: #1e3a8a; color: #ffffff; }
    .day-6 { background-color: #dc2626; color: #ffffff; font-weight: 700; }
    
    .day-weekend { background-color: #111827; color: #4b5563; opacity: 0.5; }
    .day-today { border: 3px solid #fbbf24; box-shadow: 0 0 15px rgba(251, 191, 36, 0.6); }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .badge-critical {
        background-color: rgba(220, 38, 38, 0.2);
        color: #f87171;
        border: 2px solid #dc2626;
    }
    
    .badge-warning {
        background-color: rgba(245, 158, 11, 0.2);
        color: #fbbf24;
        border: 2px solid #f59e0b;
    }
    
    .badge-ok {
        background-color: rgba(34, 197, 94, 0.2);
        color: #4ade80;
        border: 2px solid #22c55e;
    }
    
    /* Separator */
    hr {
        border: none;
        border-top: 2px solid #2d3748;
        margin: 30px 0;
    }
    
    /* Tooltips i caption */
    .stCaption {
        color: #9ca3af !important;
        font-size: 0.85rem !important;
    }
    
    /* Radio buttons */
    div[role="radiogroup"] label {
        background-color: #1a1f2e !important;
        padding: 12px 20px !important;
        border-radius: 6px !important;
        border: 2px solid #2d3748 !important;
        margin: 5px 0 !important;
        transition: all 0.3s ease;
    }
    
    div[role="radiogroup"] label:hover {
        border-color: #3b82f6 !important;
        background-color: #252d3f !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #1a1f2e !important;
        border: 2px solid #2d3748 !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        color: #f9fafb !important;
    }
    
    .streamlit-expanderHeader:hover {
        border-color: #3b82f6 !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1f2e;
        border: 2px solid #2d3748;
        border-radius: 6px 6px 0 0;
        padding: 12px 24px;
        font-weight: 600;
        color: #9ca3af;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #252d3f;
        border-color: #3b82f6;
        border-bottom: none;
        color: #60a5fa;
    }
    
    /* ========== TRYB JASNY - PROFESJONALNA PALETA ========== */
    @media (prefers-color-scheme: light) {
        .stApp {
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
        }
        
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border-right: 2px solid #e2e8f0;
            box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
        }
        
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3 {
            color: #1d4ed8 !important;
        }
        
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 2px solid #e2e8f0;
            border-left: 4px solid #2563eb;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }
        
        div[data-testid="stMetric"]:hover {
            border-left-color: #1d4ed8;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
        }
        
        div[data-testid="stMetricLabel"] {
            color: #64748b !important;
        }
        
        div[data-testid="stMetricValue"] {
            color: #0f172a !important;
        }
        
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 2px solid #e2e8f0;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        }
        
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%);
        }
        
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
            border-color: #2563eb !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
            color: #ffffff !important;
        }
        
        .stButton > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.4);
        }
        
        .stButton > button[kind="secondary"] {
            background: transparent !important;
            border-color: #2563eb !important;
            color: #1d4ed8 !important;
        }
        
        .stButton > button[kind="secondary"]:hover {
            background: rgba(37, 99, 235, 0.08) !important;
            border-color: #1d4ed8 !important;
        }
        
        h1, h2, h3 {
            color: #0f172a !important;
        }
        
        h1 {
            border-bottom: 3px solid #2563eb;
        }
        
        h2 {
            color: #1d4ed8 !important;
        }
        
        h3 {
            color: #2563eb !important;
        }
        
        h4 {
            color: #475569 !important;
        }
        
        .stDataFrame {
            border: 2px solid #e2e8f0 !important;
        }
        
        thead tr th {
            background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%) !important;
            color: #1d4ed8 !important;
            border-bottom: 2px solid #2563eb !important;
        }
        
        tbody tr {
            background-color: #ffffff !important;
        }
        
        tbody tr:hover {
            background-color: #f8fafc !important;
            box-shadow: inset 0 0 0 2px #2563eb;
        }
        
        tbody tr td {
            color: #1e293b !important;
            border-bottom: 1px solid #f1f5f9 !important;
        }
        
        div[data-baseweb="notification"][kind="error"] {
            background-color: rgba(220, 38, 38, 0.08) !important;
            border-left-color: #dc2626 !important;
        }
        
        div[data-baseweb="notification"][kind="warning"] {
            background-color: rgba(245, 158, 11, 0.08) !important;
            border-left-color: #f59e0b !important;
        }
        
        div[data-baseweb="notification"][kind="success"] {
            background-color: rgba(34, 197, 94, 0.08) !important;
            border-left-color: #22c55e !important;
        }
        
        div[data-baseweb="notification"][kind="info"] {
            background-color: rgba(37, 99, 235, 0.08) !important;
            border-left-color: #2563eb !important;
        }
        
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > div {
            background-color: #ffffff !important;
            border: 2px solid #e2e8f0 !important;
            color: #0f172a !important;
        }
        
        .stTextInput > div > div > input:focus,
        .stNumberInput > div > div > input:focus {
            border-color: #2563eb !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
        }
        
        .calendar-day {
            border: 1px solid #e2e8f0;
        }
        
        .day-0 { background-color: #f8fafc; color: #64748b; }
        .day-1 { background-color: #dbeafe; color: #1e40af; }
        .day-2 { background-color: #93c5fd; color: #1e3a8a; }
        .day-3 { background-color: #60a5fa; color: #ffffff; }
        .day-4 { background-color: #3b82f6; color: #ffffff; }
        .day-5 { background-color: #2563eb; color: #ffffff; }
        .day-6 { background-color: #dc2626; color: #ffffff; font-weight: 700; }
        
        .day-weekend { background-color: #f1f5f9; color: #94a3b8; opacity: 0.7; }
        
        .badge-critical {
            background-color: rgba(220, 38, 38, 0.15);
            color: #dc2626;
            border: 2px solid #dc2626;
        }
        
        .badge-warning {
            background-color: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
            border: 2px solid #f59e0b;
        }
        
        .badge-ok {
            background-color: rgba(34, 197, 94, 0.15);
            color: #16a34a;
            border: 2px solid #22c55e;
        }
        
        hr {
            border-top: 2px solid #e2e8f0;
        }
        
        .stCaption {
            color: #64748b !important;
        }
        
        div[role="radiogroup"] label {
            background-color: #ffffff !important;
            border: 2px solid #e2e8f0 !important;
        }
        
        div[role="radiogroup"] label:hover {
            border-color: #2563eb !important;
            background-color: #f8fafc !important;
        }
        
        .streamlit-expanderHeader {
            background-color: #ffffff !important;
            border: 2px solid #e2e8f0 !important;
            color: #0f172a !important;
        }
        
        .streamlit-expanderHeader:hover {
            border-color: #2563eb !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: #ffffff;
            border: 2px solid #e2e8f0;
            color: #64748b;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #f8fafc;
            border-color: #2563eb;
            color: #1d4ed8;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# --- KLASY DANYCH ---
@dataclass
class ServiceInterval:
    """Pojedynczy interwał serwisowy"""
    name: str
    type: str  # 'cycles' lub 'time'
    interval: int  # liczba cykli lub miesięcy
    current_value: int
    last_service: str
    enabled: bool = True
    
    def get_status(self):
        """Zwraca status: 0=OK, 1=Warning, 2=Critical"""
        if not self.enabled:
            return 0
            
        if self.type == 'cycles':
            remaining = self.interval - self.current_value
            if remaining <= 0:
                return 2
            elif remaining <= self.interval * 0.15:
                return 1
        else:  # time
            last = datetime.strptime(self.last_service, "%Y-%m-%d").date()
            next_date = add_months(last, self.interval)
            days_remaining = (next_date - datetime.now().date()).days
            if days_remaining <= 0:
                return 2
            elif days_remaining <= 7:
                return 1
        return 0
    
    def get_progress(self):
        """Zwraca postęp jako wartość 0-1"""
        if not self.enabled:
            return 0
        if self.type == 'cycles':
            return min(self.current_value / self.interval, 1.0)
        else:
            last = datetime.strptime(self.last_service, "%Y-%m-%d").date()
            next_date = add_months(last, self.interval)
            total_days = (next_date - last).days
            elapsed_days = (datetime.now().date() - last).days
            return min(elapsed_days / total_days, 1.0) if total_days > 0 else 0

# --- FUNKCJE POMOCNICZE ---
def add_months(source_date, months):
    """Dodaje miesiące do daty"""
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, [31,29,31,30,31,30,31,31,30,31,30,31][month-1])
    return source_date.replace(year=year, month=month, day=day)

def is_weekend(date):
    """Sprawdza czy data to weekend (sobota=5, niedziela=6)"""
    return date.weekday() >= 5

def get_next_workday(start_date, days_to_add):
    """Dodaje dni robocze (pomija weekendy)"""
    current = start_date
    days_added = 0
    
    while days_added < days_to_add:
        current += timedelta(days=1)
        if not is_weekend(current):
            days_added += 1
    
    return current

# --- SYSTEM ZAPISU DANYCH (PERSISTENCE) ---
DATA_DIR = Path("warsztat_data")
DATABASE_FILE = DATA_DIR / "database.json"
HISTORY_FILE = DATA_DIR / "history.json"
BACKUP_DIR = DATA_DIR / "backups"
DOCS_DIR = DATA_DIR / "dokumentacja"

def ensure_data_directory():
    """Tworzy katalog na dane jeśli nie istnieje"""
    DATA_DIR.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)

def create_backup():
    """Tworzy kopię zapasową bazy danych"""
    try:
        if DATABASE_FILE.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = BACKUP_DIR / f"database_backup_{timestamp}.json"
            
            with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Zachowaj tylko 10 ostatnich backupów
            backups = sorted(BACKUP_DIR.glob("database_backup_*.json"))
            if len(backups) > 10:
                for old_backup in backups[:-10]:
                    old_backup.unlink()
            
            return True
    except Exception as e:
        st.error(f"Błąd tworzenia backupu: {e}")
        return False

def migrate_old_data(data):
    """Migruje stare dane do nowego formatu z historią dzienną"""
    migrated = False
    
    for machine in data.get('machines', []):
        # Dodaj daily_cycles jeśli nie istnieje
        if 'daily_cycles' not in machine:
            machine['daily_cycles'] = {}
            migrated = True
        
        # Dodaj documents jeśli nie istnieje
        if 'documents' not in machine:
            machine['documents'] = []
            migrated = True
        
        # Sprawdź czy wszystkie interwały mają wymagane pola
        for interval in machine.get('service_intervals', []):
            if 'enabled' not in interval:
                interval['enabled'] = True
                migrated = True
    
    if migrated:
        st.info("✅ Dane zostały automatycznie zaktualizowane do nowej wersji systemu.")
        save_database(data)
    
    return data

def save_database(data):
    """Zapisuje bazę danych do pliku JSON"""
    try:
        ensure_data_directory()
        
        # Walidacja danych przed zapisem
        if not isinstance(data, dict) or 'machines' not in data:
            st.error("Nieprawidłowa struktura danych!")
            return False
        
        # Zapisz dane
        with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        st.error(f"Błąd zapisu bazy danych: {e}")
        return False

def load_database():
    """Wczytuje bazę danych z pliku JSON lub tworzy nową"""
    try:
        ensure_data_directory()
        
        if DATABASE_FILE.exists():
            with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Walidacja struktury
            if isinstance(data, dict) and 'machines' in data:
                # Migracja starych danych
                data = migrate_old_data(data)
                return data
            else:
                st.warning("Nieprawidłowa struktura pliku database.json - tworzę nową bazę")
                return get_initial_data()
        else:
            # Pierwsza inicjalizacja - utwórz pustą bazę
            initial_data = get_initial_data()
            save_database(initial_data)
            return initial_data
            
    except json.JSONDecodeError:
        st.error("Błąd odczytu database.json - plik uszkodzony. Tworzę nową bazę.")
        return get_initial_data()
    except Exception as e:
        st.error(f"Błąd wczytywania bazy danych: {e}")
        return get_initial_data()

def save_history(history):
    """Zapisuje historię operacji do pliku JSON"""
    try:
        ensure_data_directory()
        
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        st.error(f"Błąd zapisu historii: {e}")
        return False

def load_history():
    """Wczytuje historię operacji z pliku JSON"""
    try:
        ensure_data_directory()
        
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
            return history if isinstance(history, list) else []
        else:
            return []
            
    except json.JSONDecodeError:
        st.warning("Błąd odczytu history.json - tworzę nową historię")
        return []
    except Exception as e:
        st.error(f"Błąd wczytywania historii: {e}")
        return []

def get_status_color(status):
    """Zwraca kolor dla statusu"""
    colors = {0: "#22c55e", 1: "#fbbf24", 2: "#ef4444"}
    return colors.get(status, "#8b95a8")

def get_status_label(status):
    """Zwraca etykietę dla statusu"""
    labels = {0: "OK", 1: "OSTRZEŻENIE", 2: "KRYTYCZNY"}
    return labels.get(status, "NIEZNANY")

def get_initial_data():
    """Pusta struktura danych - użytkownik wprowadzi dane samodzielnie"""
    return {
        "machines": []
    }

def save_document(machine_id, uploaded_file):
    """Zapisuje dokument dla maszyny"""
    try:
        ensure_data_directory()
        
        # Utwórz folder dla maszyny
        machine_docs_dir = DOCS_DIR / machine_id
        machine_docs_dir.mkdir(exist_ok=True)
        
        # Zapisz plik
        file_path = machine_docs_dir / uploaded_file.name
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        return uploaded_file.name
    except Exception as e:
        st.error(f"Błąd zapisu dokumentu: {e}")
        return None

def get_document_path(machine_id, filename):
    """Zwraca ścieżkę do dokumentu"""
    return DOCS_DIR / machine_id / filename

def delete_document(machine_id, filename):
    """Usuwa dokument"""
    try:
        file_path = get_document_path(machine_id, filename)
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    except Exception as e:
        st.error(f"Błąd usuwania dokumentu: {e}")
        return False

# Inicjalizacja session_state
if 'data' not in st.session_state:
    st.session_state.data = load_database()
if 'history' not in st.session_state:
    st.session_state.history = load_history()
if 'unsaved_changes' not in st.session_state:
    st.session_state.unsaved_changes = False
if 'config_authenticated' not in st.session_state:
    st.session_state.config_authenticated = False
if 'selected_machine' not in st.session_state:
    st.session_state.selected_machine = None
if 'calendar_month' not in st.session_state:
    st.session_state.calendar_month = datetime.now().month
if 'calendar_year' not in st.session_state:
    st.session_state.calendar_year = datetime.now().year

# --- FUNKCJE OPERACYJNE ---
def add_cycle(machine_id, cycles, date_str=None):
    """Dodaje cykle do historii dziennej i wszystkich interwałów cyklicznych"""
    if date_str is None:
        date_str = str(datetime.now().date())
    
    for machine in st.session_state.data['machines']:
        if machine['id'] == machine_id:
            # Dodaj do historii dziennej
            if date_str not in machine['daily_cycles']:
                machine['daily_cycles'][date_str] = 0
            machine['daily_cycles'][date_str] += cycles
            
            # Dodaj do interwałów cyklicznych
            for interval in machine['service_intervals']:
                if interval['type'] == 'cycles' and interval['enabled']:
                    interval['current_value'] += cycles
            
            # Dodaj do historii
            st.session_state.history.insert(0, {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "machine": machine['name'],
                "action": f"Dodano {cycles} cykli (data: {date_str})",
                "user": "System"
            })
            
            # Automatyczny zapis
            save_database(st.session_state.data)
            save_history(st.session_state.history)
            break

def reset_service_interval(machine_id, interval_name):
    """Resetuje konkretny interwał serwisowy"""
    for machine in st.session_state.data['machines']:
        if machine['id'] == machine_id:
            for interval in machine['service_intervals']:
                if interval['name'] == interval_name:
                    interval['current_value'] = 0
                    interval['last_service'] = str(datetime.now().date())
                    
                    # Dodaj do historii
                    st.session_state.history.insert(0, {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "machine": machine['name'],
                        "action": f"Wykonano: {interval_name}",
                        "user": "System"
                    })
                    
                    # Automatyczny zapis
                    save_database(st.session_state.data)
                    save_history(st.session_state.history)
                    break
            break

def get_machine_critical_status(machine):
    """Zwraca najwyższy status krytyczny dla maszyny"""
    max_status = 0
    critical_intervals = []
    
    for interval_data in machine['service_intervals']:
        interval = ServiceInterval(**interval_data)
        status = interval.get_status()
        if status > max_status:
            max_status = status
        if status == 2:
            critical_intervals.append(interval.name)
    
    return max_status, critical_intervals

def get_total_cycles_for_machine(machine):
    """Oblicza łączną liczbę cykli z historii dziennej"""
    return sum(machine.get('daily_cycles', {}).values())

def render_calendar_heatmap(machine, year=None, month=None):
    """Renderuje kalendarz heatmap dla maszyny"""
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month
    
    # Pobierz dane z tego miesiąca
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    daily_cycles = machine.get('daily_cycles', {})
    
    # Znajdź maksymalną liczbę cykli w miesiącu dla skalowania kolorów
    month_dates = [f"{year}-{month:02d}-{day:02d}" for week in cal for day in week if day != 0]
    month_cycles = [daily_cycles.get(date, 0) for date in month_dates]
    max_cycles = max(month_cycles) if month_cycles else 6
    
    html = f"""
    <div style='background: #1a1f2e; padding: 20px; border-radius: 8px; border: 2px solid #2d3748;'>
        <h4 style='color: #60a5fa; text-align: center; margin-bottom: 20px;'>{month_name} {year}</h4>
        <div style='text-align: center;'>
    """
    
    # Nagłówki dni tygodnia
    days_header = ['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'So', 'Nd']
    html += "<div style='margin-bottom: 10px;'>"
    for day_name in days_header:
        html += f"<span style='display: inline-block; width: 35px; color: #9ca3af; font-size: 0.8rem; font-weight: 600;'>{day_name}</span>"
    html += "</div>"
    
    # Renderuj kalendarz
    today = datetime.now().date()
    
    for week in cal:
        html += "<div style='margin-bottom: 2px;'>"
        for day in week:
            if day == 0:
                html += "<span class='calendar-day' style='background: transparent; border: none;'></span>"
            else:
                date = datetime(year, month, day).date()
                date_str = str(date)
                cycles = daily_cycles.get(date_str, 0)
                
                # Określ klasę CSS
                if is_weekend(date):
                    css_class = "day-weekend"
                elif cycles == 0:
                    css_class = "day-0"
                elif cycles <= max_cycles / 6:
                    css_class = "day-1"
                elif cycles <= max_cycles / 3:
                    css_class = "day-2"
                elif cycles <= max_cycles / 2:
                    css_class = "day-3"
                elif cycles <= 2 * max_cycles / 3:
                    css_class = "day-4"
                elif cycles <= 5 * max_cycles / 6:
                    css_class = "day-5"
                else:
                    css_class = "day-6"
                
                today_class = " day-today" if date == today else ""
                
                html += f"<span class='calendar-day {css_class}{today_class}' title='{date_str}: {cycles} cykli'>{day}</span>"
        html += "</div>"
    
    html += """
        </div>
        <div style='margin-top: 20px; text-align: center;'>
            <small style='color: #9ca3af;'>
                <span style='color: #1e3a5f;'>█</span> 1 cykl &nbsp;
                <span style='color: #2563eb;'>█</span> 2 cykle &nbsp;
                <span style='color: #1e40af;'>█</span> 3-4 &nbsp;
                <span style='color: #dc2626;'>█</span> 5+ &nbsp;
                <span style='border: 2px solid #fbbf24; padding: 2px 6px;'>⬜</span> Dziś
            </small>
        </div>
    </div>
    """
    
    return html

# --- SIDEBAR ---
st.sidebar.markdown("### 🔧 WARSZTAT ZIOŁOLEK")
st.sidebar.markdown("#### System Utrzymania Ruchu")
st.sidebar.markdown("---")

view_options = ["🏠 Panel Główny", "🔧 Karta Maszyny", "📄 Dokumentacja", "⚙️ Konfiguracja", "📊 Historia"]

view = st.sidebar.radio(
    "NAWIGACJA",
    view_options,
    label_visibility="visible"
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Data systemu:** {datetime.now().strftime('%d.%m.%Y')}")
st.sidebar.markdown(f"**Godzina:** {datetime.now().strftime('%H:%M:%S')}")

# POPRAWIONE LICZNIKI ALERTÓW - zliczają wszystkie interwały, nie tylko maszyny
critical_count = 0
warning_count = 0
for machine in st.session_state.data['machines']:
    for interval_data in machine.get('service_intervals', []):
        if interval_data.get('enabled', True):
            try:
                interval = ServiceInterval(**interval_data)
                status = interval.get_status()
                if status == 2:
                    critical_count += 1
                elif status == 1:
                    warning_count += 1
            except:
                pass

st.sidebar.markdown("---")
st.sidebar.markdown("#### STATUS FLOTY")
if critical_count > 0:
    st.sidebar.error(f"🚨 Krytyczne: {critical_count}")
if warning_count > 0:
    st.sidebar.warning(f"⚠️ Ostrzeżenia: {warning_count}")
if critical_count == 0 and warning_count == 0:
    st.sidebar.success(f"✅ Wszystko OK")

st.sidebar.markdown("---")
st.sidebar.markdown("#### 💾 SYSTEM ZAPISU")
if DATABASE_FILE.exists():
    file_time = datetime.fromtimestamp(DATABASE_FILE.stat().st_mtime)
    st.sidebar.caption(f"Ostatni zapis: {file_time.strftime('%d.%m %H:%M')}")
else:
    st.sidebar.caption("Brak zapisanej bazy")

# Przycisk tworzenia backupu
if st.sidebar.button("📦 Utwórz Backup", use_container_width=True):
    if create_backup():
        st.sidebar.success("✅ Backup utworzony!")
    else:
        st.sidebar.error("❌ Błąd backupu")

# --- WIDOK 1: PANEL GŁÓWNY ---
if view == "🏠 Panel Główny":
    st.title("DASHBOARD UTRZYMANIA RUCHU")
    
    if len(st.session_state.data['machines']) == 0:
        st.info("ℹ️ **Brak maszyn w systemie.** Przejdź do zakładki **Konfiguracja** (wymagane hasło: 1111) aby dodać pierwsze maszyny.")
    else:
        # Sekcja alertów
        alerts_critical = []
        alerts_warning = []
        
        for machine in st.session_state.data['machines']:
            for interval_data in machine['service_intervals']:
                try:
                    interval = ServiceInterval(**interval_data)
                    status = interval.get_status()
                    
                    if status == 2:
                        alerts_critical.append(f"**{machine['name']}** - {interval.name}")
                    elif status == 1:
                        alerts_warning.append(f"**{machine['name']}** - {interval.name}")
                except:
                    pass
        
        # Wyświetlanie alertów
        col_alert1, col_alert2 = st.columns(2)
        
        with col_alert1:
            if alerts_critical:
                st.error(f"### 🚨 PILNE INTERWENCJE ({len(alerts_critical)})")
                for alert in alerts_critical:
                    st.markdown(f"- {alert}")
            else:
                st.success("### ✅ Brak krytycznych alertów")
        
        with col_alert2:
            if alerts_warning:
                st.warning(f"### ⚠️ OSTRZEŻENIA ({len(alerts_warning)})")
                for alert in alerts_warning:
                    st.markdown(f"- {alert}")
            else:
                st.info("### ℹ️ Brak ostrzeżeń")
        
        st.markdown("---")
        
        # Statystyki ogólne
        st.subheader("PRZEGLĄD FLOTY")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_machines = len(st.session_state.data['machines'])
        
        # Liczba maszyn bez alertów
        machines_with_alerts = set()
        for machine in st.session_state.data['machines']:
            for interval_data in machine.get('service_intervals', []):
                if interval_data.get('enabled', True):
                    try:
                        interval = ServiceInterval(**interval_data)
                        status = interval.get_status()
                        if status > 0:
                            machines_with_alerts.add(machine['id'])
                    except:
                        pass
        
        machines_ok = total_machines - len(machines_with_alerts)
        
        col1.metric("Maszyny w systemie", total_machines, delta=None)
        col2.metric("Stan sprawny", machines_ok, delta="OK" if machines_ok == total_machines else None)
        col3.metric("Ostrzeżenia", warning_count, delta="⚠️" if warning_count > 0 else None)
        col4.metric("Krytyczne", critical_count, delta="🚨" if critical_count > 0 else None)
        
        st.markdown("---")
        
        # Lista maszyn - kafelki
        st.subheader("STATUS MASZYN")
        
        cols = st.columns(2)
        for idx, machine in enumerate(st.session_state.data['machines']):
            col = cols[idx % 2]
            
            with col:
                with st.container(border=True):
                    # Nagłówek z statusem
                    machine_status, critical_intervals = get_machine_critical_status(machine)
                    status_color = get_status_color(machine_status)
                    status_label = get_status_label(machine_status)
                    
                    col_name, col_status = st.columns([3, 1])
                    col_name.markdown(f"### {machine['name']}")
                    col_status.markdown(f"<div class='status-badge badge-{'critical' if machine_status == 2 else 'warning' if machine_status == 1 else 'ok'}'>{status_label}</div>", unsafe_allow_html=True)
                    
                    st.caption(f"📍 {machine['location']} | 🏭 {machine['model']}")
                    
                    st.markdown("---")
                    
                    # Interwały serwisowe
                    if len(machine['service_intervals']) > 0:
                        st.markdown("#### Interwały serwisowe:")
                        
                        for interval_data in machine['service_intervals']:
                            if interval_data['enabled']:
                                try:
                                    interval = ServiceInterval(**interval_data)
                                    status = interval.get_status()
                                    progress = interval.get_progress()
                                    
                                    col_label, col_value = st.columns([2, 1])
                                    col_label.caption(interval.name)
                                    
                                    if interval.type == 'cycles':
                                        col_value.write(f"{interval.current_value}/{interval.interval}")
                                    else:
                                        last = datetime.strptime(interval.last_service, "%Y-%m-%d").date()
                                        next_date = add_months(last, interval.interval)
                                        days = (next_date - datetime.now().date()).days
                                        col_value.write(f"{days} dni")
                                    
                                    # Pasek postępu z kolorem
                                    progress_color = get_status_color(status)
                                    st.progress(progress)
                                except:
                                    pass
                    else:
                        st.caption("Brak skonfigurowanych interwałów")
                    
                    st.markdown("")

# --- WIDOK 2: KARTA MASZYNY ---
elif view == "🔧 Karta Maszyny":
    st.title("KARTA MASZYNY")
    
    if len(st.session_state.data['machines']) == 0:
        st.info("ℹ️ **Brak maszyn w systemie.** Przejdź do zakładki **Konfiguracja** (wymagane hasło: 1111) aby dodać pierwsze maszyny.")
    else:
        # ULEPSZONY WYBÓR MASZYNY - z filtrowaniem po lokalizacji
        machine_options = {}
        for m in st.session_state.data['machines']:
            display_name = f"[{m['location']}] {m['name']}"
            machine_options[display_name] = m['id']
        
        # Określ domyślny index
        default_index = 0
        if st.session_state.selected_machine:
            selected_machine_obj = next((m for m in st.session_state.data['machines'] if m['id'] == st.session_state.selected_machine), None)
            if selected_machine_obj:
                default_display = f"[{selected_machine_obj['location']}] {selected_machine_obj['name']}"
                if default_display in machine_options:
                    default_index = list(machine_options.keys()).index(default_display)
        
        selected_display = st.selectbox(
            "**Wybierz maszynę:**", 
            list(machine_options.keys()), 
            index=default_index,
            help="Wpisz nazwę hali aby odfiltrować maszyny",
            key="machine_selector"
        )
        
        selected_machine_id = machine_options[selected_display]
        machine = next(m for m in st.session_state.data['machines'] if m['id'] == selected_machine_id)
        
        st.markdown("---")
        
        # Informacje podstawowe
        col1, col2, col3 = st.columns(3)
        col1.metric("ID Maszyny", machine['id'])
        col2.metric("Lokalizacja", machine['location'])
        col3.metric("Model", machine['model'])
        
        st.markdown("---")
        
        # Dwie kolumny: Operacje i Interwały
        col_left, col_right = st.columns([1, 2])
        
        with col_left:
            st.markdown("### 📝 OPERACJE")
            
            with st.container(border=True):
                st.markdown("#### Rejestracja cykli")
                
                col_date, col_cycles = st.columns(2)
                with col_date:
                    cycle_date = st.date_input("Data:", datetime.now().date(), key="cycle_date")
                with col_cycles:
                    cycles_to_add = st.number_input("Liczba cykli:", min_value=1, step=1, value=1, key="cycles_input")
                
                if st.button("✅ Zatwierdź wpis", key="add_cycles", use_container_width=True, type="primary"):
                    add_cycle(machine['id'], cycles_to_add, str(cycle_date))
                    st.success(f"Dodano {cycles_to_add} cykli na dzień {cycle_date}")
                    st.rerun()
            
            st.markdown("")
            
            with st.container(border=True):
                st.markdown("#### Szybkie akcje")
                
                if len(machine['service_intervals']) > 0:
                    for interval_data in machine['service_intervals']:
                        if interval_data['enabled']:
                            try:
                                interval = ServiceInterval(**interval_data)
                                status = interval.get_status()
                                
                                button_label = f"🛠️ {interval.name}"
                                
                                if st.button(button_label, key=f"reset_{machine['id']}_{interval.name}", use_container_width=True, type="primary" if status == 2 else "secondary"):
                                    reset_service_interval(machine['id'], interval.name)
                                    st.success(f"Wykonano: {interval.name}")
                                    st.rerun()
                            except:
                                pass
                else:
                    st.caption("Brak skonfigurowanych interwałów")
        
        with col_right:
            # KALENDARZ HEATMAP
            st.markdown("### 📅 KALENDARZ PRACY")
            
            col_month_nav = st.columns([1, 2, 1])
            
            with col_month_nav[0]:
                if st.button("◀ Poprzedni", key="prev_month"):
                    if st.session_state.calendar_month == 1:
                        st.session_state.calendar_month = 12
                        st.session_state.calendar_year -= 1
                    else:
                        st.session_state.calendar_month -= 1
                    st.rerun()
            
            with col_month_nav[1]:
                st.markdown(f"<p style='text-align: center; color: #60a5fa; font-weight: 600;'>{calendar.month_name[st.session_state.calendar_month]} {st.session_state.calendar_year}</p>", unsafe_allow_html=True)
            
            with col_month_nav[2]:
                if st.button("Następny ▶", key="next_month"):
                    if st.session_state.calendar_month == 12:
                        st.session_state.calendar_month = 1
                        st.session_state.calendar_year += 1
                    else:
                        st.session_state.calendar_month += 1
                    st.rerun()
            
            # Renderuj kalendarz
            calendar_html = render_calendar_heatmap(machine, st.session_state.calendar_year, st.session_state.calendar_month)
            st.markdown(calendar_html, unsafe_allow_html=True)
            
            # Statystyki miesiąca
            month_dates = [f"{st.session_state.calendar_year}-{st.session_state.calendar_month:02d}-{day:02d}" 
                          for day in range(1, 32) if day <= calendar.monthrange(st.session_state.calendar_year, st.session_state.calendar_month)[1]]
            month_total = sum(machine.get('daily_cycles', {}).get(date, 0) for date in month_dates)
            
            col_stats = st.columns(3)
            col_stats[0].metric("Cykle w miesiącu", month_total)
            col_stats[1].metric("Cykle ogółem", get_total_cycles_for_machine(machine))
            col_stats[2].metric("Średnia dzienna", f"{machine.get('avg_daily_cycles', 0)}")
            
            st.markdown("---")
            
            # STATUS INTERWAŁÓW
            st.markdown("### 📊 STATUS INTERWAŁÓW")
            
            if len(machine['service_intervals']) > 0:
                # Szczegółowy widok każdego interwału
                for interval_data in machine['service_intervals']:
                    if interval_data['enabled']:
                        try:
                            interval = ServiceInterval(**interval_data)
                            status = interval.get_status()
                            progress = interval.get_progress()
                            
                            with st.expander(f"**{interval.name}** - {get_status_label(status)}", expanded=(status == 2)):
                                col_a, col_b = st.columns(2)
                                
                                with col_a:
                                    if interval.type == 'cycles':
                                        st.metric("Aktualny stan", f"{interval.current_value}/{interval.interval} cykli")
                                        remaining = interval.interval - interval.current_value
                                        st.metric("Pozostało", f"{remaining} cykli")
                                    else:
                                        last = datetime.strptime(interval.last_service, "%Y-%m-%d").date()
                                        next_date = add_months(last, interval.interval)
                                        days = (next_date - datetime.now().date()).days
                                        st.metric("Następny termin", next_date.strftime("%d.%m.%Y"))
                                        st.metric("Pozostało", f"{days} dni")
                                
                                with col_b:
                                    st.metric("Ostatni serwis", interval.last_service)
                                    st.metric("Status", get_status_label(status))
                                
                                st.progress(progress)
                                
                                # Prognoza
                                if interval.type == 'cycles' and machine['avg_daily_cycles'] > 0:
                                    remaining = interval.interval - interval.current_value
                                    if remaining > 0:
                                        days_to_service = int(remaining / machine['avg_daily_cycles'])
                                        service_date = get_next_workday(datetime.now().date(), days_to_service)
                                        st.info(f"📅 Estymowany termin serwisu: **{service_date.strftime('%d.%m.%Y')}** (za ~{days_to_service} dni roboczych)")
                        except:
                            pass
                
                st.markdown("---")
                
                # ULEPSZONA PROGNOZA 14-DNIOWA (pomija weekendy)
                st.markdown("### 📈 PROGNOZA 14-DNIOWA (DNI ROBOCZE)")
                
                if machine['avg_daily_cycles'] > 0:
                    forecast_data = []
                    current_date = datetime.now().date()
                    workdays_counted = 0
                    predicted_cycles = 0
                    
                    i = 1
                    while workdays_counted < 14:
                        day = current_date + timedelta(days=i)
                        
                        # Pomiń weekendy
                        if not is_weekend(day):
                            workdays_counted += 1
                            predicted_cycles += machine['avg_daily_cycles']
                            
                            day_status = "OK"
                            events = []
                            
                            # Sprawdź cykle
                            for interval_data in machine['service_intervals']:
                                if interval_data['enabled'] and interval_data['type'] == 'cycles':
                                    future_value = interval_data['current_value'] + predicted_cycles
                                    if future_value >= interval_data['interval']:
                                        events.append(interval_data['name'])
                                        day_status = "SERWIS"
                            
                            # Sprawdź daty
                            for interval_data in machine['service_intervals']:
                                if interval_data['enabled'] and interval_data['type'] == 'time':
                                    last = datetime.strptime(interval_data['last_service'], "%Y-%m-%d").date()
                                    next_date = add_months(last, interval_data['interval'])
                                    if day == next_date:
                                        events.append(interval_data['name'])
                                        if day_status != "SERWIS":
                                            day_status = "PRZEGLĄD"
                            
                            forecast_data.append({
                                "Data": day.strftime("%d.%m (%a)"),
                                "Status": day_status,
                                "Zdarzenia": ", ".join(events) if events else "-"
                            })
                        
                        i += 1
                    
                    df_forecast = pd.DataFrame(forecast_data)
                    
                    def highlight_forecast(val):
                        if 'SERWIS' in str(val) or 'PRZEGLĄD' in str(val):
                            return 'background-color: rgba(239, 68, 68, 0.3); color: #ef4444; font-weight: 700; font-size: 1.1rem;'
                        return ''
                    
                    st.dataframe(
                        df_forecast.style.map(highlight_forecast, subset=['Status']),
                        use_container_width=True,
                        hide_index=True,
                        height=520
                    )
                else:
                    st.info("⚠️ Prognoza niedostępna - maszyna nie ma cykli dziennych (avg_daily_cycles = 0).")
            else:
                st.info("Brak skonfigurowanych interwałów dla tej maszyny.")

# --- WIDOK 3: DOKUMENTACJA ---
elif view == "📄 Dokumentacja":
    st.title("ARCHIWUM DOKUMENTACJI TECHNICZNEJ")
    
    if len(st.session_state.data['machines']) == 0:
        st.info("ℹ️ **Brak maszyn w systemie.** Przejdź do zakładki **Konfiguracja** aby dodać pierwsze maszyny.")
    else:
        # Wybór maszyny
        machine_options = {}
        for m in st.session_state.data['machines']:
            display_name = f"[{m['location']}] {m['name']}"
            machine_options[display_name] = m['id']
        
        selected_display = st.selectbox(
            "**Wybierz maszynę:**", 
            list(machine_options.keys()),
            help="Wybierz maszynę aby zobaczyć lub dodać dokumentację"
        )
        
        selected_machine_id = machine_options[selected_display]
        machine = next(m for m in st.session_state.data['machines'] if m['id'] == selected_machine_id)
        
        st.markdown("---")
        
        # Informacje o maszynie
        col_info = st.columns(3)
        col_info[0].metric("Maszyna", machine['name'])
        col_info[1].metric("Lokalizacja", machine['location'])
        col_info[2].metric("Model", machine['model'])
        
        st.markdown("---")
        
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.markdown("### 📤 DODAJ DOKUMENTACJĘ")
            
            with st.container(border=True):
                st.markdown("#### Upload pliku")
                st.caption("Obsługiwane formaty: PDF, PNG, JPG, DOCX, XLSX")
                
                uploaded_file = st.file_uploader(
                    "Wybierz plik:",
                    type=['pdf', 'png', 'jpg', 'jpeg', 'docx', 'xlsx'],
                    key="doc_uploader"
                )
                
                doc_description = st.text_input(
                    "Opis dokumentu:",
                    placeholder="np. Schemat elektryczny, Instrukcja obsługi, DTR..."
                )
                
                if st.button("💾 Zapisz dokument", type="primary", disabled=(uploaded_file is None)):
                    if uploaded_file and doc_description:
                        filename = save_document(machine['id'], uploaded_file)
                        if filename:
                            # Dodaj do listy dokumentów
                            if 'documents' not in machine:
                                machine['documents'] = []
                            
                            machine['documents'].append({
                                "filename": filename,
                                "description": doc_description,
                                "upload_date": str(datetime.now().date()),
                                "size": uploaded_file.size
                            })
                            
                            save_database(st.session_state.data)
                            
                            # Historia
                            st.session_state.history.insert(0, {
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "machine": machine['name'],
                                "action": f"Dodano dokument: {doc_description}",
                                "user": "System"
                            })
                            save_history(st.session_state.history)
                            
                            st.success(f"✅ Dokument '{filename}' został zapisany!")
                            st.rerun()
                    else:
                        st.error("Uzupełnij opis dokumentu!")
        
        with col_right:
            st.markdown("### 📚 DOSTĘPNE DOKUMENTY")
            
            if 'documents' in machine and len(machine['documents']) > 0:
                for idx, doc in enumerate(machine['documents']):
                    with st.container(border=True):
                        col_doc = st.columns([3, 1, 1])
                        
                        with col_doc[0]:
                            st.markdown(f"**{doc['description']}**")
                            st.caption(f"📄 {doc['filename']}")
                            st.caption(f"📅 Dodano: {doc['upload_date']} | 💾 {doc['size']} bajtów")
                        
                        with col_doc[1]:
                            # Przycisk pobierania
                            doc_path = get_document_path(machine['id'], doc['filename'])
                            if doc_path.exists():
                                with open(doc_path, 'rb') as f:
                                    st.download_button(
                                        label="📥",
                                        data=f.read(),
                                        file_name=doc['filename'],
                                        mime="application/octet-stream",
                                        key=f"download_{machine['id']}_{idx}",
                                        use_container_width=True
                                    )
                        
                        with col_doc[2]:
                            # Przycisk usuwania
                            if st.button("🗑️", key=f"delete_{machine['id']}_{idx}", use_container_width=True):
                                if delete_document(machine['id'], doc['filename']):
                                    machine['documents'].pop(idx)
                                    save_database(st.session_state.data)
                                    
                                    st.session_state.history.insert(0, {
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "machine": machine['name'],
                                        "action": f"Usunięto dokument: {doc['description']}",
                                        "user": "System"
                                    })
                                    save_history(st.session_state.history)
                                    
                                    st.success("Dokument usunięty!")
                                    st.rerun()
            else:
                st.info("📭 Brak dokumentów dla tej maszyny. Dodaj pierwszy dokument używając formularza obok.")

# --- WIDOK 4: KONFIGURACJA ---
elif view == "⚙️ Konfiguracja":
    st.title("KONFIGURACJA SYSTEMU")
    
    # Sprawdzanie hasła
    if not st.session_state.config_authenticated:
        st.warning("🔒 **Dostęp chroniony hasłem**")
        st.markdown("Aby uzyskać dostęp do konfiguracji, wprowadź hasło:")
        
        password_input = st.text_input("Hasło:", type="password", key="config_password")
        
        col_login, col_cancel = st.columns(2)
        
        with col_login:
            if st.button("🔓 Zaloguj", type="primary", use_container_width=True):
                if password_input == "1111":
                    st.session_state.config_authenticated = True
                    st.success("✅ Zalogowano pomyślnie!")
                    st.rerun()
                else:
                    st.error("❌ Nieprawidłowe hasło!")
        
        with col_cancel:
            if st.button("❌ Anuluj", use_container_width=True):
                st.info("Powrót do panelu głównego...")
        
        st.stop()
    
    # Jeśli zalogowany - pokaż konfigurację
    col_logout, col_space = st.columns([1, 3])
    with col_logout:
        if st.button("🔒 Wyloguj", type="secondary"):
            st.session_state.config_authenticated = False
            st.rerun()
    
    st.markdown("---")
    
    # Ostrzeżenie o niezapisanych zmianach
    if st.session_state.unsaved_changes:
        st.warning("⚠️ **Masz niezapisane zmiany!** Kliknij 'Zapisz zmiany' aby je zachować.")
    
    # Przyciski akcji na górze
    col_save, col_backup, col_reset = st.columns(3)
    
    with col_save:
        if st.button("💾 Zapisz zmiany", type="primary", use_container_width=True):
            if save_database(st.session_state.data):
                st.session_state.unsaved_changes = False
                st.success("✅ Zmiany zapisane pomyślnie!")
                st.rerun()
            else:
                st.error("❌ Błąd zapisu!")
    
    with col_backup:
        if st.button("📦 Backup przed zmianami", use_container_width=True):
            if create_backup():
                st.success("✅ Backup utworzony!")
            else:
                st.error("❌ Błąd backupu!")
    
    with col_reset:
        if st.button("🔄 Odśwież dane", use_container_width=True):
            st.session_state.data = load_database()
            st.session_state.unsaved_changes = False
            st.success("✅ Dane odświeżone!")
            st.rerun()
    
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["🏭 Zarządzanie maszynami", "🔧 Interwały serwisowe", "📁 Zarządzanie plikami"])
    
    with tab1:
        st.subheader("Lista maszyn")
        
        if len(st.session_state.data['machines']) > 0:
            for idx, machine in enumerate(st.session_state.data['machines']):
                with st.expander(f"**{machine['name']}** ({machine['id']})", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        new_name = st.text_input("Nazwa", machine['name'], key=f"name_{idx}")
                        new_location = st.text_input("Lokalizacja", machine['location'], key=f"loc_{idx}")
                        
                        if new_name != machine['name']:
                            machine['name'] = new_name
                            st.session_state.unsaved_changes = True
                        if new_location != machine['location']:
                            machine['location'] = new_location
                            st.session_state.unsaved_changes = True
                    
                    with col2:
                        new_model = st.text_input("Model", machine['model'], key=f"model_{idx}")
                        new_avg = st.number_input("Średnia dzienna cykli", value=machine['avg_daily_cycles'], min_value=0, key=f"avg_{idx}")
                        
                        if new_model != machine['model']:
                            machine['model'] = new_model
                            st.session_state.unsaved_changes = True
                        if new_avg != machine['avg_daily_cycles']:
                            machine['avg_daily_cycles'] = new_avg
                            st.session_state.unsaved_changes = True
                    
                    if st.button(f"🗑️ Usuń maszynę", key=f"del_machine_{idx}"):
                        deleted_name = machine['name']
                        st.session_state.data['machines'].pop(idx)
                        save_database(st.session_state.data)
                        
                        # Dodaj do historii
                        st.session_state.history.insert(0, {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "machine": deleted_name,
                            "action": "Usunięto maszynę z systemu",
                            "user": "System"
                        })
                        save_history(st.session_state.history)
                        
                        st.success(f"Usunięto maszynę: {deleted_name}")
                        st.rerun()
        else:
            st.info("Brak maszyn w systemie. Użyj przycisku poniżej aby dodać pierwszą maszynę.")
        
        st.markdown("---")
        
        if st.button("➕ Dodaj nową maszynę", type="primary"):
            new_id = f"M{len(st.session_state.data['machines'])+1:02d}"
            new_machine = {
                "id": new_id,
                "name": f"Nowa maszyna {new_id}",
                "location": "Hala X",
                "model": "Model",
                "avg_daily_cycles": 0,
                "service_intervals": [],
                "daily_cycles": {},
                "documents": []
            }
            st.session_state.data['machines'].append(new_machine)
            save_database(st.session_state.data)
            
            # Dodaj do historii
            st.session_state.history.insert(0, {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "machine": new_machine['name'],
                "action": "Dodano nową maszynę do systemu",
                "user": "System"
            })
            save_history(st.session_state.history)
            
            st.success("Dodano nową maszynę!")
            st.rerun()
    
    with tab2:
        st.subheader("Konfiguracja interwałów serwisowych")
        
        if len(st.session_state.data['machines']) > 0:
            selected_machine_name_display = st.selectbox(
                "Wybierz maszynę:", 
                [f"[{m['location']}] {m['name']}" for m in st.session_state.data['machines']], 
                key="config_select"
            )
            # Wyciągnij nazwę maszyny
            machine_name = selected_machine_name_display.split('] ')[1]
            machine = next(m for m in st.session_state.data['machines'] if m['name'] == machine_name)
            
            st.markdown("---")
            
            st.markdown("#### Istniejące interwały:")
            
            if len(machine['service_intervals']) > 0:
                for idx, interval_data in enumerate(machine['service_intervals']):
                    with st.expander(f"**{interval_data['name']}**", expanded=False):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            new_int_name = st.text_input("Nazwa interwału", interval_data['name'], key=f"int_name_{machine['id']}_{idx}")
                            new_enabled = st.checkbox("Włączony", interval_data['enabled'], key=f"int_en_{machine['id']}_{idx}")
                            
                            if new_int_name != interval_data['name']:
                                interval_data['name'] = new_int_name
                                st.session_state.unsaved_changes = True
                            if new_enabled != interval_data['enabled']:
                                interval_data['enabled'] = new_enabled
                                st.session_state.unsaved_changes = True
                        
                        with col2:
                            new_type = st.selectbox("Typ", ['cycles', 'time'], index=0 if interval_data['type']=='cycles' else 1, key=f"int_type_{machine['id']}_{idx}")
                            interval_label = "Interwał (cykle)" if new_type == 'cycles' else "Interwał (miesiące)"
                            new_interval = st.number_input(interval_label, value=interval_data['interval'], min_value=1, key=f"int_val_{machine['id']}_{idx}")
                            
                            if new_type != interval_data['type']:
                                interval_data['type'] = new_type
                                st.session_state.unsaved_changes = True
                            if new_interval != interval_data['interval']:
                                interval_data['interval'] = new_interval
                                st.session_state.unsaved_changes = True
                        
                        with col3:
                            new_current = st.number_input("Bieżąca wartość", value=interval_data['current_value'], min_value=0, key=f"int_cur_{machine['id']}_{idx}")
                            new_last = st.date_input("Ostatni serwis", datetime.strptime(interval_data['last_service'], "%Y-%m-%d").date(), 
                                                                       key=f"int_date_{machine['id']}_{idx}").strftime("%Y-%m-%d")
                            
                            if new_current != interval_data['current_value']:
                                interval_data['current_value'] = new_current
                                st.session_state.unsaved_changes = True
                            if new_last != interval_data['last_service']:
                                interval_data['last_service'] = new_last
                                st.session_state.unsaved_changes = True
                        
                        if st.button(f"🗑️ Usuń interwał", key=f"del_int_{machine['id']}_{idx}"):
                            deleted_interval = interval_data['name']
                            machine['service_intervals'].pop(idx)
                            save_database(st.session_state.data)
                            
                            # Dodaj do historii
                            st.session_state.history.insert(0, {
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "machine": machine['name'],
                                "action": f"Usunięto interwał: {deleted_interval}",
                                "user": "System"
                            })
                            save_history(st.session_state.history)
                            
                            st.success("Usunięto interwał")
                            st.rerun()
            else:
                st.info("Brak interwałów dla tej maszyny. Dodaj pierwszy interwał poniżej.")
            
            st.markdown("---")
            
            st.markdown("#### Dodaj nowy interwał:")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            
            with col_a:
                new_int_name = st.text_input("Nazwa", "Nowy interwał", key="new_interval_name")
            with col_b:
                new_int_type = st.selectbox("Typ", ['cycles', 'time'], key="new_interval_type")
            with col_c:
                new_int_interval = st.number_input("Interwał", value=1, min_value=1, key="new_interval_value")
            with col_d:
                st.write("")
                st.write("")
                if st.button("➕ Dodaj interwał", type="primary"):
                    new_interval = {
                        "name": new_int_name,
                        "type": new_int_type,
                        "interval": new_int_interval,
                        "current_value": 0,
                        "last_service": str(datetime.now().date()),
                        "enabled": True
                    }
                    machine['service_intervals'].append(new_interval)
                    save_database(st.session_state.data)
                    
                    # Dodaj do historii
                    st.session_state.history.insert(0, {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "machine": machine['name'],
                        "action": f"Dodano interwał: {new_int_name}",
                        "user": "System"
                    })
                    save_history(st.session_state.history)
                    
                    st.success("Dodano nowy interwał")
                    st.rerun()
        else:
            st.info("Brak maszyn w systemie. Najpierw dodaj maszynę w zakładce 'Zarządzanie maszynami'.")
    
    with tab3:
        st.subheader("Zarządzanie plikami danych")
        
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.markdown("#### 📊 Baza danych")
            if DATABASE_FILE.exists():
                file_size = DATABASE_FILE.stat().st_size
                file_time = datetime.fromtimestamp(DATABASE_FILE.stat().st_mtime)
                st.info(f"**Plik:** `{DATABASE_FILE}`\n\n**Rozmiar:** {file_size} bajtów\n\n**Ostatnia modyfikacja:** {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Podgląd zawartości
                with st.expander("👁️ Podgląd JSON"):
                    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                        st.code(f.read(), language='json')
                
                # Pobieranie pliku
                with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                    st.download_button(
                        label="📥 Pobierz database.json",
                        data=f.read(),
                        file_name=f"database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
            else:
                st.warning("Plik database.json nie istnieje")
        
        with col_info2:
            st.markdown("#### 📜 Historia")
            if HISTORY_FILE.exists():
                file_size = HISTORY_FILE.stat().st_size
                file_time = datetime.fromtimestamp(HISTORY_FILE.stat().st_mtime)
                st.info(f"**Plik:** `{HISTORY_FILE}`\n\n**Rozmiar:** {file_size} bajtów\n\n**Ostatnia modyfikacja:** {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Pobieranie pliku
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    st.download_button(
                        label="📥 Pobierz history.json",
                        data=f.read(),
                        file_name=f"history_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
            else:
                st.warning("Plik history.json nie istnieje")
        
        st.markdown("---")
        
        st.markdown("#### 📦 Kopie zapasowe")
        
        backups = sorted(BACKUP_DIR.glob("database_backup_*.json"), reverse=True)
        
        if backups:
            st.info(f"Znaleziono {len(backups)} kopii zapasowych")
            
            for backup in backups[:5]:  # Pokaż tylko 5 ostatnich
                backup_time = datetime.strptime(backup.stem.replace("database_backup_", ""), "%Y%m%d_%H%M%S")
                col_b1, col_b2, col_b3 = st.columns([3, 1, 1])
                
                col_b1.caption(f"📦 {backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                with open(backup, 'r', encoding='utf-8') as f:
                    col_b2.download_button(
                        label="📥",
                        data=f.read(),
                        file_name=backup.name,
                        mime="application/json",
                        key=f"download_{backup.name}"
                    )
                
                if col_b3.button("♻️", key=f"restore_{backup.name}"):
                    # Przywróć backup
                    with open(backup, 'r', encoding='utf-8') as f:
                        restored_data = json.load(f)
                    
                    # Migruj przywrócone dane
                    restored_data = migrate_old_data(restored_data)
                    
                    st.session_state.data = restored_data
                    save_database(restored_data)
                    
                    st.success(f"Przywrócono backup z {backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.rerun()
        else:
            st.warning("Brak kopii zapasowych")
        
        st.markdown("---")
        
        # Niebezpieczne operacje
        with st.expander("⚠️ OPERACJE NIEBEZPIECZNE", expanded=False):
            st.error("**UWAGA!** Te operacje są nieodwracalne!")
            
            col_d1, col_d2 = st.columns(2)
            
            with col_d1:
                if st.button("🗑️ Wyczyść całą bazę danych", type="secondary"):
                    create_backup()  # Najpierw backup
                    st.session_state.data = get_initial_data()
                    save_database(st.session_state.data)
                    st.warning("Baza danych wyczyszczona! Utworzono backup.")
                    st.rerun()
            
            with col_d2:
                if st.button("🗑️ Wyczyść historię", type="secondary"):
                    st.session_state.history = []
                    save_history([])
                    st.warning("Historia wyczyszczona!")
                    st.rerun()

# --- WIDOK 5: HISTORIA ---
elif view == "📊 Historia":
    st.title("HISTORIA OPERACJI")
    
    if st.session_state.history:
        st.markdown(f"Pokazano **{len(st.session_state.history)}** ostatnich operacji")
        
        df_history = pd.DataFrame(st.session_state.history)
        st.dataframe(df_history, use_container_width=True, hide_index=True, height=600)
        
        col_export, col_clear = st.columns(2)
        
        with col_export:
            # Export do CSV
            csv = df_history.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Eksportuj do CSV",
                data=csv,
                file_name=f"historia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_clear:
            if st.button("🗑️ Wyczyść historię", use_container_width=True):
                st.session_state.history = []
                save_history([])
                st.rerun()
    else:
        st.info("Brak zapisanych operacji w historii")

# --- FOOTER ---
st.markdown("---")
st.markdown("""
    <div style='text-align: center; padding: 20px 0;'>
        <p style='color: #9ca3af; font-size: 0.9rem; margin: 0;'>
            🔧 <strong>Warsztat Ziołolek</strong> - System Utrzymania Ruchu
        </p>
        <p style='color: #60a5fa; font-size: 0.85rem; margin: 5px 0 0 0;'>
            Profesjonalne zarządzanie parkiem maszynowym | © 2026
        </p>
    </div>
""", unsafe_allow_html=True)
