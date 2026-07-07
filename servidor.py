import sqlite3
import os
import re
import math
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from fastapi.responses import FileResponse

# === RUTAS ABSOLUTAS PARA QUE RENDER ENCUENTRE LOS ARCHIVOS ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "farmacia_hospital.db")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def inicializar_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, password TEXT, rol TEXT)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS pacientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, edad TEXT, fecha_ingreso TEXT, fecha_egreso TEXT, medico TEXT)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS habitaciones (numero TEXT PRIMARY KEY, tipo TEXT, estado TEXT, paciente_id INTEGER, color TEXT)""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, paciente_id INTEGER, nombre_medicamento TEXT, presentacion TEXT,
            cantidad REAL, precio_base REAL, precio_final REAL, total_articulo REAL, fecha_registro TEXT, registrado_por TEXT,
            autorizado_por TEXT DEFAULT NULL, fecha_modificacion TEXT DEFAULT NULL
        )
    """)
    cursor.execute("""CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY, valor TEXT)""")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('PIN_MAESTRO', '1234')") 
    
    for u, p, r in [("admin", "admin123", "administrador"), ("farmacia", "farma123", "farmacia"), ("recepcion", "recep123", "recepcion")]:
        cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, password, rol) VALUES (?, ?, ?)", (u, p, r))
        
    habitaciones_base = [
        ("Habitación 1", "Habitación"), ("Habitación 2", "Habitación"), ("Habitación 3", "Habitación"),
        ("Habitación 4", "Habitación"), ("Habitación 5", "Habitación"), ("Habitación 7", "Habitación"),
        ("Habitación 8", "Habitación"), ("Habitación 9", "Habitación"), ("Habitación 10", "Habitación"),
        ("Habitación 11", "Habitación"), ("Habitación 12", "Habitación"), ("Habitación 13", "Habitación"),
        ("Habitación 15", "Habitación"), ("Valoración", "Urgencias"),
        ("Incubadora 1", "Incubadora"), ("Incubadora 2", "Incubadora"),
        ("Consultorio 1", "Consultorio"), ("Consultorio 2", "Consultorio"), ("Consultorio 3", "Consultorio")
    ]
    for hab, tipo in habitaciones_base:
        cursor.execute("INSERT OR IGNORE INTO habitaciones (numero, tipo, estado, paciente_id) VALUES (?, ?, 'LIBRE', NULL)", (hab, tipo))
    conn.commit()
    conn.close()

inicializar_db()

class LoginReq(BaseModel): usuario: str; password: str
class OcuparReq(BaseModel): numero_hab: str; nombre_paciente: str; edad: str; medico: str
class MedReq(BaseModel): paciente_id: int; nombre_med: str; presentacion: str; cantidad: float; precio_base: float; registrado_por: str
class PassReq(BaseModel): usuario_a_cambiar: str; nueva_password: str
class HabReq(BaseModel): numero: str; tipo: str
class EditReq(BaseModel): id_consumo: int; nueva_cantidad: float; nuevo_precio: float; pin_autorizacion: str
class PinReq(BaseModel): nuevo_pin: str

def natural_sort_key(hab):
    orden_tipo = {"Habitación": 1, "Suite": 2, "Incubadora": 3, "Urgencias": 4, "Consultorio": 5}
    tipo_val = orden_tipo.get(hab["tipo"], 99)
    partes_num = [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', hab["numero"])]
    return (tipo_val, partes_num)

@app.get("/")
def pagina_principal():
    ruta_index = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(ruta_index): return FileResponse(ruta_index)
    return {"error": "index.html no encontrado"}

@app.get("/index.html")
def pagina_principal_html():
    ruta_index = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(ruta_index): return FileResponse(ruta_index)
    return {"error": "index.html no encontrado"}

@app.get("/logo")
def obtener_logo():
    ruta_logo = os.path.join(BASE_DIR, "logo fatima.jpg")
    if os.path.exists(ruta_logo): return FileResponse(ruta_logo)
    return {"error": "Logo no encontrado"}

@app.post("/login")
def login(req: LoginReq):
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("SELECT rol FROM usuarios WHERE usuario = ? AND password = ?", (req.usuario.strip(), req.password.strip()))
    res = cursor.fetchone(); conn.close()
    if res: return {"status": "ok", "rol": res[0], "usuario": req.usuario}
    raise HTTPException(status_code=401, detail="Error")

@app.get("/habitaciones")
def obtener_habitaciones():
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("SELECT h.numero, h.estado, h.paciente_id, h.tipo, p.nombre, p.edad, p.fecha_ingreso, p.medico FROM habitaciones h LEFT JOIN pacientes p ON h.paciente_id = p.id")
    filas = cursor.fetchall(); conn.close()
    lista = [{"numero": f[0], "estado": f[1], "paciente_id": f[2], "tipo": f[3], "nombre": f[4], "edad": f[5], "fecha_ingreso": f[6], "medico": f[7]} for f in filas]
    lista.sort(key=natural_sort_key) 
    return lista

@app.post("/agregar-habitacion")
def agregar_hab(req: HabReq):
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO habitaciones (numero, tipo, estado) VALUES (?, ?, 'LIBRE')", (req.numero, req.tipo))
    conn.commit(); conn.close()
    return {"status": "ok"}

@app.post("/eliminar-habitacion/{numero}")
def eliminar_hab(numero: str):
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("DELETE FROM habitaciones WHERE numero=?", (numero,))
    conn.commit(); conn.close()
    return {"status": "ok"}

@app.post("/ocupar-habitacion")
def ocupar(req: OcuparReq):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("INSERT INTO pacientes (nombre, edad, fecha_ingreso, medico) VALUES (?, ?, ?, ?)", (req.nombre_paciente.strip(), req.edad.strip(), fecha, req.medico.strip()))
    pid = cursor.lastrowid
    cursor.execute("UPDATE habitaciones SET estado='OCUPADA', paciente_id=? WHERE numero=?", (pid, req.numero_hab))
    conn.commit(); conn.close()
    return {"status": "ok"}

@app.post("/liberar-habitacion/{numero}")
def liberar(numero: str):
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("SELECT paciente_id FROM habitaciones WHERE numero=?", (numero,))
    res = cursor.fetchone()
    if res and res[0]:
        fecha_egreso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE pacientes SET fecha_egreso=? WHERE id=?", (fecha_egreso, res[0]))
    cursor.execute("UPDATE habitaciones SET estado='LIBRE', paciente_id=NULL WHERE numero=?", (numero,))
    conn.commit(); conn.close()
    return {"status": "ok"}

@app.get("/catalogo-medicamentos")
def catalogo_medicamentos():
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT nombre_medicamento FROM consumos")
    filas = cursor.fetchall(); conn.close()
    return [f[0] for f in filas]

@app.post("/agregar-medicamento")
def agregar_med(req: MedReq):
    pb_exacto = round(req.precio_base, 2)
    pf = round(pb_exacto * 1.40, 2)
    fh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    
    cursor.execute("SELECT id, cantidad, precio_base FROM consumos WHERE paciente_id=? AND nombre_medicamento=? AND presentacion=?", (req.paciente_id, req.nombre_med.strip(), req.presentacion.strip()))
    existentes = cursor.fetchall()
    id_match = None
    cant_actual = 0
    for fila in existentes:
        if round(fila[2], 2) == pb_exacto:
            id_match = fila[0]
            cant_actual = fila[1]
            break
            
    if id_match:
        nueva_cantidad = cant_actual + req.cantidad
        nuevo_total = round(pf * nueva_cantidad, 2)
        cursor.execute("UPDATE consumos SET cantidad=?, precio_final=?, total_articulo=? WHERE id=?", (nueva_cantidad, pf, nuevo_total, id_match))
    else:
        tot = round(pf * req.cantidad, 2)
        cursor.execute("INSERT INTO consumos (paciente_id, nombre_medicamento, presentacion, cantidad, precio_base, precio_final, total_articulo, fecha_registro, registrado_por) VALUES (?,?,?,?,?,?,?,?,?)", 
                       (req.paciente_id, req.nombre_med.strip(), req.presentacion.strip(), req.cantidad, pb_exacto, pf, tot, fh, req.registrado_por))
    conn.commit(); conn.close()
    return {"status": "ok"}

@app.post("/editar-medicamento")
def editar_medicamento(req: EditReq):
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracion WHERE clave='PIN_MAESTRO'")
    row = cursor.fetchone()
    pin_guardado = str(row[0]).strip() if row else "1234"
    if str(req.pin_autorizacion).strip() != pin_guardado:
        conn.close(); raise HTTPException(status_code=401, detail="PIN inválido")
    pf = round(req.nuevo_precio * 1.40, 2)
    tot = round(pf * req.nueva_cantidad, 2)
    fh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE consumos SET cantidad=?, precio_base=?, precio_final=?, total_articulo=?, autorizado_por=?, fecha_modificacion=? WHERE id=?", (req.nueva_cantidad, req.nuevo_precio, pf, tot, "Administrador / Dir.", fh, req.id_consumo))
    conn.commit(); conn.close()
    return {"status": "ok"}

@app.post("/cambiar-pin")
def cambiar_pin(req: PinReq):
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("UPDATE configuracion SET valor=? WHERE clave='PIN_MAESTRO'", (str(req.nuevo_pin).strip(),))
    conn.commit(); conn.close()
    return {"status": "ok"}

@app.get("/historial-paciente/{pid}")
def historial(pid: int):
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("SELECT nombre, edad, fecha_ingreso, medico FROM pacientes WHERE id = ?", (pid,))
    pac = cursor.fetchone()
    cursor.execute("SELECT id, cantidad, nombre_medicamento, presentacion, precio_base, precio_final, total_articulo, fecha_registro, registrado_por, autorizado_por FROM consumos WHERE paciente_id = ?", (pid,))
    filas = cursor.fetchall(); conn.close()
    lista = [{"id": r[0], "cant": r[1], "nom": r[2], "pres": r[3], "pb": r[4], "pf": r[5], "tot": r[6], "fec": r[7], "usr": r[8], "auth": r[9]} for r in filas]
    return {"paciente": {"nombre": pac[0], "edad": pac[1], "ingreso": pac[2], "medico": pac[3]}, "medicamentos": lista, "gran_total": sum(i["tot"] for i in lista)}

@app.get("/estadisticas")
def estadisticas():
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM habitaciones WHERE tipo IN ('Habitación', 'Suite')")
    total_habs = cursor.fetchone()[0]
    
    año_actual = str(datetime.now().year)
    cursor.execute("SELECT id, nombre, edad, medico, fecha_ingreso, fecha_egreso FROM pacientes WHERE fecha_ingreso LIKE ? ORDER BY id DESC", (año_actual + "%",))
    pacientes_anuales = cursor.fetchall()
    
    total_dias_estancia = 0
    lista_historial = []
    
    for p in pacientes_anuales:
        ingreso = p[4]
        egreso = p[5]
        try:
            t_ingreso = datetime.strptime(ingreso, "%Y-%m-%d %H:%M:%S")
            t_egreso = datetime.strptime(egreso, "%Y-%m-%d %H:%M:%S") if egreso else datetime.now()
            
            horas_totales = (t_egreso - t_ingreso).total_seconds() / 3600
            dias_completos = int(horas_totales // 24)
            horas_restantes = int(horas_totales % 24)
            
            dias_a_graficar = dias_completos
            if horas_restantes >= 6: 
                dias_a_graficar += 1
                
            total_dias_estancia += dias_a_graficar
            
            estado = "Alta" if egreso else "Internado"
            tiempo_str = f"{dias_completos} días, {horas_restantes} hrs"
            
            lista_historial.append({
                "nombre": p[1], "edad": p[2], "medico": p[3], "ingreso": ingreso.split(" ")[0],
                "tiempo": tiempo_str, "dias_fact": dias_a_graficar, "estado": estado
            })
        except: pass 
        
    dias_transcurridos_del_año = (datetime.now() - datetime(datetime.now().year, 1, 1)).days + 1
    capacidad_total_dias = total_habs * dias_transcurridos_del_año
    ocupacion_pct = round((total_dias_estancia / capacidad_total_dias) * 100, 1) if capacidad_total_dias > 0 else 0
    conn.close()
    
    return {
        "total_habitaciones": total_habs, 
        "dias_consumidos": total_dias_estancia, 
        "porcentaje": ocupacion_pct, 
        "ingresos_anuales": len(pacientes_anuales), 
        "historial": lista_historial
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
