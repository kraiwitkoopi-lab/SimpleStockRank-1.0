import sqlite3
import json
from typing import List, Dict, Any, Optional

DB_NAME = "jomo.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Create projects table
    # We store the entire project state as a JSON blob for simplicity
    # matching the "Document Store" pattern suitable for this SPA.
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            data TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_all_projects() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    projects = conn.execute('SELECT data FROM projects').fetchall()
    conn.close()
    return [json.loads(row['data']) for row in projects]

def save_project(project_data: Dict[str, Any]):
    conn = get_db_connection()
    project_id = project_data.get('id')
    name = project_data.get('name')
    data_json = json.dumps(project_data)
    
    conn.execute('''
        INSERT OR REPLACE INTO projects (id, name, data)
        VALUES (?, ?, ?)
    ''', (project_id, name, data_json))
    conn.commit()
    conn.close()

def delete_project(project_id: str):
    conn = get_db_connection()
    conn.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()
